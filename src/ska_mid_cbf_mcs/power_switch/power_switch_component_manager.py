# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import logging
import threading
from time import sleep
from typing import Callable, Optional

import tango
from ska_control_model import (
    CommunicationStatus,
    PowerState,
    SimulationMode,
    TaskStatus,
)
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CbfComponentManager
from ska_mid_cbf_mcs.power_switch.apc_pdu_driver import ApcPduDriver
from ska_mid_cbf_mcs.power_switch.apc_snmp_driver import ApcSnmpDriver
from ska_mid_cbf_mcs.power_switch.dli_pro_switch_driver import (
    DLIProSwitchDriver,
)
from ska_mid_cbf_mcs.power_switch.power_switch_simulator import (
    PowerSwitchSimulator,
)
from ska_mid_cbf_mcs.power_switch.st_switched_pro2_driver import (
    STSwitchedPRO2Driver,
)

__all__ = ["PowerSwitchComponentManager"]


class PowerSwitchComponentManager(CbfComponentManager):
    """
    A component manager for the power switch. Calls either the power
    switch driver or the power switch simulator based on the value of simulation
    mode.

    :param model: Name of the power switch model
    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param simulation_mode: simulation mode identifies if the real power switch
                          driver or the simulator should be used
    """

    def __init__(
        self: PowerSwitchComponentManager,
        *args: any,
        model: str,
        ip: str,
        login: str,
        password: str,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: any,
    ) -> None:
        """
        Initialize a new instance.

        :param model: Name of the power switch model
        :param ip: IP address of the power switch
        :param login: Login username of the power switch
        :param password: Login password for the power switch
        :param simulation_mode: simulation mode identifies if the real power switch
                driver or the simulator should be used

        """
        super().__init__(*args, **kwargs)
        self.simulation_mode = simulation_mode

        self.power_switch_driver = self.get_power_switch_driver(
            model=model,
            ip=ip,
            login=login,
            password=password,
            logger=self.logger,
        )

        self.power_switch_simulator = PowerSwitchSimulator(
            model=model, logger=self.logger
        )

    @property
    def num_outlets(self: PowerSwitchComponentManager) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        if self.simulation_mode:
            return self.power_switch_simulator.num_outlets
        else:
            return self.power_switch_driver.num_outlets

    @property
    def is_communicating(self: PowerSwitchComponentManager) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        if super().is_communicating:
            if self.simulation_mode:
                return self.power_switch_simulator.is_communicating
            else:
                return self.power_switch_driver.is_communicating
        return False

    # -------------
    # Communication
    # -------------

    def start_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Perform any setup needed for communicating with the power switch.
        """
        self.logger.debug("Entering PowerSwitch.start_communicating")

        if self.is_communicating:
            self.logger.info("Already communicating.")
            return

        if self.simulation_mode:
            outlets = self.power_switch_simulator.outlets
        else:
            self.power_switch_driver.initialize()
            outlets = self.power_switch_driver.outlets

        # We only want CommunicationStatus.Established if
        # the PDU responded with a valid list of outlets.
        if outlets:
            super().start_communicating()
            # This moves the op state model.
            self._update_component_state(power=PowerState.ON)
        else:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )

    def stop_communicating(self: PowerSwitchComponentManager) -> None:
        """
        Stop communication with the component.
        """
        if not self.simulation_mode:
            self.power_switch_driver.stop()

        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model.
        super().stop_communicating()

    # ----------------
    # Helper Functions
    # ----------------

    def get_power_switch_driver(
        self: PowerSwitchComponentManager,
        model: str,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ):
        # The text must match the powerswitch.yaml
        if model == "DLI LPC9":
            return DLIProSwitchDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "Server Technology Switched PRO2":
            return STSwitchedPRO2Driver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "APC AP8681 SSH":
            return ApcPduDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        elif model == "APC AP8681 SNMP":
            return ApcSnmpDriver(
                ip=ip, login=login, password=password, logger=logger
            )
        else:
            err = f"Model name {model} is not supported."
            logger.error(err)
            tango.Except.throw_exception(
                "PowerSwitch_CreateDriverFailed",
                err,
                "get_power_switch_driver()",
            )

    def check_power_state(
        self: PowerSwitchComponentManager,
        mode: str,
        outlet: str,
        result_code: ResultCode,
        message: str,
    ) -> bool:
        if result_code != ResultCode.OK:
            return False, message

        power_state = self.get_outlet_power_state(outlet)
        self.logger.debug(f"Outlet {outlet} = {power_state}")
        if mode == "on":
            if power_state == PowerState.ON:
                return True, "TurnOnOutlet completed OK"
            else:
                # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async events
                self.logger.warn(
                    "The outlet's power state is not 'on' as expected. Waiting for 5 seconds before rechecking the power state..."
                )
                sleep(5)
                power_state = self.get_outlet_power_state(outlet)
                if power_state != PowerState.ON:
                    return (
                        False,
                        f"Outlet {outlet} failed to power on after sleep.",
                    )
        elif mode == "off":
            if power_state == PowerState.OFF:
                return True, "TurnOffOutlet completed OK"
            else:
                # TODO: This is a temporary workaround for CIP-2050 until the power switch deals with async
                self.logger.warn(
                    "The outlet's power state is not 'off' as expected. Waiting for 5 seconds before rechecking the power state..."
                )
                sleep(5)
                power_state = self.get_outlet_power_state(outlet)
                if power_state != PowerState.OFF:
                    return (
                        False,
                        f"Outlet {outlet} failed to power off after sleep.",
                    )

    # -------------
    # Fast Commands
    # -------------

    def get_outlet_power_state(
        self: PowerSwitchComponentManager, outlet: str
    ) -> PowerState:
        """
        Get the power state of a specific outlet.

        :param outlet: outlet ID
        :return: power state of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        """

        if self.simulation_mode:
            return self.power_switch_simulator.get_outlet_power_state(outlet)
        else:
            return self.power_switch_driver.get_outlet_power_state(outlet)

    # ---------------------
    # Long Running Commands
    # ---------------------

    def _turn_on_outlet(
        self: PowerSwitchComponentManager,
        outlet: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Tell the power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        self.logger.debug(
            f"Entering PowerSwitch.TurnOnOutlet()  -  Outlet={outlet}"
        )

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "TurnOnOutlet", task_callback, task_abort_event
        ):
            return

        if self.simulation_mode:
            self.power_switch_simulator.turn_on_outlet(outlet)
        else:
            try:
                result_code, message = self.power_switch_driver.turn_on_outlet(
                    outlet
                )
                powered_on, message = self.check_power_state(
                    "on", outlet, result_code, message
                )
                if not powered_on:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(ResultCode.FAILED, message),
                    )
                    return
            except AssertionError as e:
                self.logger.error(e)
                task_callback(
                    exception=e,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "TurnOnOutlet FAILED",
                    ),
                )
                return
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(result_code, "TurnOnOutlet completed OK"),
        )

    @check_communicating
    def turn_on_outlet(
        self: PowerSwitchComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[TaskStatus, str]:
        """
        Turn on the PDU outlet specified by argin.

        :param argin: the target outlet ID, as a string
        :param task_callback: callback to be called when the status of
            the command changes

        :return: a result code and message
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._turn_on_outlet,
            args=[argin],
            task_callback=task_callback,
        )

    def _turn_off_outlet(
        self: PowerSwitchComponentManager,
        outlet: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> tuple[ResultCode, str]:
        """
        Tell the power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        :return: a tuple containing a return code and a string
                message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        self.logger.debug(
            f"Entering PowerSwitch.TurnOffOutlet()  -  Outlet={outlet}"
        )

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "TurnOffOutlet", task_callback, task_abort_event
        ):
            return
        if self.simulation_mode:
            self.power_switch_simulator.turn_off_outlet(outlet)
        else:
            try:
                (
                    result_code,
                    message,
                ) = self.power_switch_driver.turn_off_outlet(outlet)
                powered_off, message = self.check_power_state(
                    "off", outlet, result_code, message
                )
                if not powered_off:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(ResultCode.FAILED, message),
                    )
                    return
            except AssertionError as e:
                self.logger.error(f"Assertion error: {e}")
                task_callback(
                    exception=e,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "TurnOffOutlet FAILED",
                    ),
                )
                return
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(result_code, "TurnOffOutlet completed OK"),
        )

    @check_communicating
    def turn_off_outlet(
        self: PowerSwitchComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        **kwargs: any,
    ) -> tuple[TaskStatus, str]:
        """
        Turn off the PDU outlet specified by argin.

        :param argin: the target outlet ID, as a string
        :param task_callback: callback to be called when the status of
            the command changes

        :return: a result code and message
        """
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._turn_off_outlet,
            args=[argin],
            task_callback=task_callback,
        )
