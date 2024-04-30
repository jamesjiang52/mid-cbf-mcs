# -*- coding: utf-8 -*-
#
# This file is part of the PowerSwitch project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
TANGO device class for controlling and monitoring the web power switch that distributes power to the Talon LRUs.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

# tango imports
from ska_tango_base.commands import (
    FastCommand,
    ResultCode,
    SubmittedSlowCommand,
)

# Additional import
from ska_tango_base.control_model import PowerState, SimulationMode
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.device.base_device import CbfDevice
from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import (
    PowerSwitchComponentManager,
)

__all__ = ["PowerSwitch", "main"]


class PowerSwitch(CbfDevice):
    """
    TANGO device class for controlling and monitoring the web power switch that
    distributes power to the Talon LRUs.
    """

    # -----------------
    # Device Properties
    # -----------------

    PowerSwitchModel = device_property(dtype="str")
    PowerSwitchIp = device_property(dtype="str")
    PowerSwitchLogin = device_property(dtype="str")
    PowerSwitchPassword = device_property(dtype="str")

    # ---------------
    # General methods
    # ---------------

    def always_executed_hook(self: PowerSwitch) -> None:
        """
        Hook to be executed before any attribute access or command.
        """

    def delete_device(self: PowerSwitch) -> None:
        """
        Uninitialize the device.
        """

    def create_component_manager(
        self: PowerSwitch,
    ) -> PowerSwitchComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device
        """
        # Simulation mode default true (using the simulator)
        return PowerSwitchComponentManager(
            model=self.PowerSwitchModel,
            ip=self.PowerSwitchIp,
            login=self.PowerSwitchLogin,
            password=self.PowerSwitchPassword,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self: PowerSwitch) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()
        self.register_command_object(
            "TurnOnOutlet",
            SubmittedSlowCommand(
                command_name="TurnOnOutlet",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="turn_on_outlet",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "TurnOffOutlet",
            SubmittedSlowCommand(
                command_name="TurnOffOutlet",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="turn_off_outlet",
                logger=self.logger,
            ),
        )
        self.register_command_object(
            "GetOutletPowerState",
            self.GetOutletPowerStateCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    # ---------
    # Callbacks
    # ---------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.

    # ------------------
    # Attributes methods
    # ------------------

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: PowerSwitch) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: PowerSwitch, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    @attribute(dtype=int)
    def numOutlets(self: PowerSwitch) -> int:
        """
        Get the number of outlets.

        :return: number of outlets
        """
        return self.component_manager.num_outlets

    @attribute(dtype=int)
    def isCommunicating(self: PowerSwitch) -> bool:
        """
        Get whether or not the power switch is communicating.

        :return: True if power switch can be contacted, False if not
        """
        return self.component_manager.is_communicating

    # --------
    # Commands
    # --------

    class InitCommand(CbfDevice.InitCommand):
        """
        A class for the PowerSwitch's init_device() "command".
        """

        def do(self: PowerSwitch.InitCommand) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """

            (result_code, message) = super().do()
            self._device._simulation_mode = SimulationMode.TRUE

            return (result_code, message)

    class GetOutletPowerStateCommand(FastCommand):
        """
        The command class for the GetOutletPowerState command.

        Get the power mode of an individual outlet, specified by the outlet ID.
        """

        def __init__(
            self: PowerSwitch.GetOutletPowerStateCommand,
            *args: Any,
            component_manager: PowerSwitchComponentManager,
            **kwargs: Any,
        ) -> None:
            self.component_manager = component_manager
            super().__init__(*args, **kwargs)

        def do(
            self: PowerSwitch.GetOutletPowerStateCommand, argin: str
        ) -> PowerState:
            """
            Implement GetOutletPowerState command functionality.

            :param argin: the outlet ID to get the state of

            :return: power mode of the outlet
            """
            try:
                return self.component_manager.get_outlet_power_mode(argin)
            except AssertionError as e:
                self.logger.error(e)
                return PowerState.UNKNOWN

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to get the power mode of.",
        dtype_out="DevULong",
        doc_out="Power mode of the outlet.",
    )
    @DebugIt()
    def GetOutletPowerState(self: PowerSwitch, argin: str) -> int:
        handler = self.get_command_object("GetOutletPowerState")
        return int(handler(argin))

    # ---------------------
    # Long Running Commands
    # ---------------------

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn on.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOnOutlet(self: PowerSwitch, argin: str) -> None:
        command_handler = self.get_command_object(command_name="TurnOnOutlet")
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]

    @command(
        dtype_in="DevString",
        doc_in="Outlet ID to turn off.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def TurnOffOutlet(self: PowerSwitch, argin: str) -> None:
        command_handler = self.get_command_object(command_name="TurnOffOutlet")
        result_code_message, command_id = command_handler(argin)
        return [[result_code_message], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(PowerSwitch.main) ENABLED START #
    return run((PowerSwitch,), args=args, **kwargs)
    # PROTECTED REGION END #    //  PowerSwitch.main


if __name__ == "__main__":
    main()
