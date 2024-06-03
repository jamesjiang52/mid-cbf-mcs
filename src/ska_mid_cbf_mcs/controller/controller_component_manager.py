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

import json
import logging
import os
import threading
from typing import Any, Callable, Optional

import tango
import yaml
from polling2 import TimeoutException, poll
from ska_control_model import TaskStatus
from ska_tango_base.base.component_manager import check_communicating
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    ObsState,
    PowerState,
    SimulationMode,
)
from ska_tango_testing import context
from ska_telmodel.data import TMData
from ska_telmodel.schema import validate as telmodel_validate

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)


class ControllerComponentManager(CbfComponentManager):
    """A component manager for the CbfController device."""

    def __init__(
        self: ControllerComponentManager,
        *args: Any,
        fqdn_dict: dict[str, list[str]],
        config_path_dict: dict[str, str],
        max_capabilities: dict[str, int],
        lru_timeout: int,
        talondx_component_manager: TalonDxComponentManager,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param fqdn_dict: dictionary containing FQDNs for the controller's sub-elements
        :param config_path_dict: dictionary containing paths to configuration files
        :param max_capabilities: dictionary containing maximum number of sub-elements
        :param lru_timeout: timeout in seconds for LRU commands
        :param talondx_component_manager: instance of TalonDxComponentManager
        """

        super().__init__(*args, **kwargs)
        self.simulation_mode = SimulationMode.TRUE

        (
            self._fqdn_vcc,
            self._fqdn_fsp,
            self._fqdn_subarray,
            self._fqdn_talon_lru,
            self._fqdn_talon_board,
            self._fqdn_power_switch,
        ) = ([] for i in range(6))

        # init sub-element count
        self._count_vcc = max_capabilities["VCC"]
        self._count_fsp = max_capabilities["FSP"]
        self._count_subarray = max_capabilities["Subarray"]

        # init sub-element FQDNs to all
        self._subarray_fqdns_all = fqdn_dict["CbfSubarray"]
        self._vcc_fqdns_all = fqdn_dict["VCC"]
        self._fsp_fqdns_all = fqdn_dict["FSP"]
        self._talon_lru_fqdns_all = fqdn_dict["TalonLRU"]
        self._talon_board_fqdns_all = fqdn_dict["TalonBoard"]
        self._power_switch_fqdns_all = fqdn_dict["PowerSwitch"]
        self._fs_slim_fqdn = fqdn_dict["FsSLIM"][0]
        self._vis_slim_fqdn = fqdn_dict["VisSLIM"][0]

        # init config paths
        self._talondx_config_path = config_path_dict["TalonDxConfigPath"]
        self._hw_config_path = config_path_dict["HWConfigPath"]
        self._fs_slim_config_path = config_path_dict["FsSLIMConfigPath"]
        self._vis_slim_config_path = config_path_dict["VisSLIMConfigPath"]

        self._lru_timeout = lru_timeout

        self._last_init_sys_param = ""
        self._source_init_sys_param = ""
        self.dish_utils = None

        # TODO: component manager should not be passed into component manager ?
        self._talondx_component_manager = talondx_component_manager
        self._proxies = {}

    # -------------
    # Communication
    # -------------

    def _set_fqdns(self: ControllerComponentManager) -> None:
        """
        Set the list of sub-element FQDNs to be used, limited by max capabilities count
        """

        def _filter_fqdn(all_domains: list[str], config_key: str) -> list[str]:
            return [
                domain
                for domain in all_domains
                if domain.split("/")[-1]
                in list(self._hw_config[config_key].keys())
            ]

        self._fqdn_vcc = list(self._vcc_fqdns_all)[: self._count_vcc]
        self._fqdn_fsp = list(self._fsp_fqdns_all)[: self._count_fsp]
        self._fqdn_subarray = list(self._subarray_fqdns_all)[
            : self._count_subarray
        ]
        self._fqdn_talon_lru = _filter_fqdn(
            self._talon_lru_fqdns_all, "talon_lru"
        )
        self._fqdn_talon_board = _filter_fqdn(
            self._talon_board_fqdns_all, "talon_board"
        )
        self._fqdn_power_switch = _filter_fqdn(
            self._power_switch_fqdns_all, "power_switch"
        )

        fqdn_variables = {
            "VCC": self._fqdn_vcc,
            "FSP": self._fqdn_fsp,
            "Subarray": self._fqdn_subarray,
            "Talon board": self._fqdn_talon_board,
            "Talon LRU": self._fqdn_talon_lru,
            "Power switch": self._fqdn_power_switch,
            "FS SLIM mesh": self._fs_slim_fqdn,
            "VIS SLIM mesh": self._vis_slim_fqdn,
        }

        for name, value in fqdn_variables.items():
            self.logger.debug(f"fqdn {name}: {value}")

    def _create_group_proxies(self: ControllerComponentManager) -> bool:
        """
        Create group proxies (list of DeviceProxy) for VCC, FSP, and Subarray

        :return: True if the group proxies are successfully created, False otherwise.
        """
        try:
            self._group_vcc = list(map(lambda fqdn: context.DeviceProxy(device_name=fqdn), self._fqdn_vcc))
        except tango.DevFailed:
            self.logger.error(f"Failure in connection to {self._fqdn_vcc}")
            return False
        
        try:
            self._group_fsp = list(map(lambda fqdn: context.DeviceProxy(device_name=fqdn), self._fqdn_fsp))
        except tango.DevFailed:
            self.logger.error(f"Failure in connection to {self._fqdn_fsp}")
            return False

        try:
            self._group_subarray = list(map(lambda fqdn: context.DeviceProxy(device_name=fqdn), self._fqdn_subarray))
        except tango.DevFailed:
            self.logger.error(
                f"Failure in connection to {self._fqdn_subarray}"
            )
            return False
        return True

    def _write_hw_config(
        self: ControllerComponentManager,
        fqdn: str,
        proxy: context.DeviceProxy,
        device_type: str,
    ) -> bool:
        """
        Write hardware configuration properties to the device

        :param fqdn: FQDN of the device
        :param proxy: Proxy of the device
        :param device_type: Type of the device. Can be one of "power_switch", "talon_lru", or "talon_board".
        :return: True if the hardware configuration properties are successfully written to the device, False otherwise.
        """
        try:
            self.logger.debug(
                f"Writing hardware configuration properties to {fqdn}"
            )

            device_id = fqdn.split("/")[-1]
            if device_type == "talon_board":
                device_config = {
                    "TalonDxBoardAddress": self._hw_config[device_type][
                        device_id
                    ]
                }
            else:
                device_config = self._hw_config[device_type][device_id]

            device_config = tango.utils.obj_2_property(device_config)
            proxy.put_property(device_config)
            proxy.Init()

            if device_type == "talon_lru":
                proxy.set_timeout_millis(self._lru_timeout * 1000)

        except tango.DevFailed as df:
            for item in df.args:
                self.logger.error(
                    f"Failed to write {fqdn} HW config properties: {item.reason}"
                )
            return False
        return True

    def _set_proxy_online(
        self: ControllerComponentManager,
        fqdn: str,
    ) -> bool:
        """
        Set the AdminMode of the device to ONLINE, given the FQDN of the device

        :param fqdn: FQDN of the device
        :return: True if the AdminMode of the device is successfully set to ONLINE, False otherwise.
        """
        try:
            self.logger.info(f"Setting {fqdn} to AdminMode.ONLINE")
            self._proxies[fqdn].adminMode = AdminMode.ONLINE
        except tango.DevFailed as df:
            for item in df.args:
                self.logger.error(
                    f"Failed to set AdminMode of {fqdn} to ONLINE: {item.reason}"
                )
            return False
        return True

    def _init_device_proxy(
        self: ControllerComponentManager,
        fqdn: str,
    ) -> bool:
        """
        Initialize the device proxy, given the FQDN of the device
        """
        if fqdn not in self._proxies:
            try:
                self.logger.debug(f"Trying connection to {fqdn}")
                proxy = context.DeviceProxy(device_name=fqdn)
            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(
                        f"Failure in connection to {fqdn}: {item.reason}"
                    )
                return False
            self._proxies[fqdn] = proxy
        else:
            proxy = self._proxies[fqdn]

        # If the fqdn is of a power switch, talon LRU, or talon board, write hw config
        device_types = {
            "power_switch": self._fqdn_power_switch,
            "talon_lru": self._fqdn_talon_lru,
            "talon_board": self._fqdn_talon_board,
        }
        for device_type, device_fqdns in device_types.items():
            if fqdn in device_fqdns:
                if not self._write_hw_config(fqdn, proxy, device_type):
                    return False
                break

        if not self._set_proxy_online(fqdn):
            return False

        return True

    def _init_proxies(self: ControllerComponentManager) -> bool:
        """
        Init all proxies, return True if all proxies are connected.
        """

        # NOTE: order matters here
        # - must set PDU online before LRU to establish outlet power states
        # - must set VCC online after LRU to establish LRU power state
        # TODO: evaluate ordering and add further comments

        for fqdn in (
            self._fqdn_power_switch
            + self._fqdn_talon_lru
            + self._fqdn_talon_board
            + self._fqdn_subarray
            + self._fqdn_fsp
            + self._fqdn_vcc
            + [self._fs_slim_fqdn, self._vis_slim_fqdn]
        ):
            if not self._init_device_proxy(fqdn):
                return False
        return True

    def start_communicating(
        self: ControllerComponentManager,
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        self.logger.debug(
            "Entering ControllerComponentManager.start_communicating"
        )

        if self._communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Communication already established")
            return

        with open(self._hw_config_path) as yaml_fd:
            self._hw_config = yaml.safe_load(yaml_fd)

        self._set_fqdns()

        if not self._create_group_proxies():
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        if not self._init_proxies():
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super().start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self: ControllerComponentManager) -> None:
        """
        Stop communication with the component
        """
        self.logger.debug(
            "Entering ControllerComponentManager.stop_communicating"
        )
        for proxy in self._proxies.values():
            proxy.adminMode = AdminMode.OFFLINE
        self._update_component_state(power=PowerState.UNKNOWN)
        super().stop_communicating()

    # ---------------------
    # Long Running Commands
    # ---------------------

    def _get_talon_lru_fqdns(self: ControllerComponentManager) -> list[str]:
        """
        Get the FQDNs of the Talon LRUs that are connected to the controller from the configuration JSON

        :return: List of FQDNs of the Talon LRUs
        """
        # read in list of LRUs from configuration JSON
        with open(
            os.path.join(
                os.getcwd(),
                self._talondx_config_path,
                "talondx-config.json",
            )
        ) as f:
            talondx_config_json = json.load(f)

        fqdn_talon_lru = []
        for config_command in talondx_config_json["config_commands"]:
            target = config_command["target"]
            for lru_id, lru_config in self._hw_config["talon_lru"].items():
                lru_fqdn = f"mid_csp_cbf/talon_lru/{lru_id}"
                talon1 = lru_config["TalonDxBoard1"]
                talon2 = lru_config["TalonDxBoard2"]
                if (
                    target in [talon1, talon2]
                    and lru_fqdn not in fqdn_talon_lru
                ):
                    fqdn_talon_lru.append(lru_fqdn)
        return fqdn_talon_lru

    def _lru_on(
        self: ControllerComponentManager,
        proxy: context.DeviceProxy,
        sim_mode: SimulationMode,
        lru_fqdn: str,
    ) -> tuple[bool, str]:
        """
        Turn on the LRU with the given FQDN

        :param proxy: Device proxy of the LRU
        :param sim_mode: Simulation Mode of the controller
        :param lru_fqdn: FQDN of the LRU to turn on
        :return: A tuple containing a boolean indicating success and a string with the FQDN of the LRU that failed to turn on
        """
        try:
            self.logger.info(f"Turning on LRU {lru_fqdn}")
            proxy.adminMode = AdminMode.OFFLINE
            proxy.simulationMode = sim_mode
            proxy.adminMode = AdminMode.ONLINE

            proxy.On()
        except tango.DevFailed as e:
            self.logger.error(e)
            return (False, lru_fqdn)

        self.logger.info(f"LRU successfully turned on: {lru_fqdn}")
        return (True, None)

    def _turn_on_lrus(
        self: ControllerComponentManager,
    ) -> tuple[bool, str]:
        """
        Turn on all of the Talon LRUs

        :return: A tuple containing a boolean indicating success and a string with the FQDN of the LRUs that failed to turn on
        """
        results = [
            self._lru_on(
                self._proxies[fqdn],
                self._talondx_component_manager.simulation_mode,
                fqdn,
            )
            for fqdn in self._fqdn_talon_lru
        ]

        failed_lrus = []
        out_status = True
        for status, fqdn in results:
            if not status:
                failed_lrus.append(fqdn)
                out_status = False
        return (out_status, f"Failed to power on Talon LRUs: {failed_lrus}")

    def _send_configure_slim_device(
        self: ControllerComponentManager, fqdn: str, config_path: str
    ) -> None:
        """
        Send the configuration file to the SLIM device

        :param fqdn: FQDN of the SLIM device
        :param config_path: File path to the configuration file
        """
        with open(config_path) as f:
            slim_config = f.read()
        self._proxies[fqdn].set_timeout_millis(10000)
        self._proxies[fqdn].command_inout("Configure", slim_config)

    def _configure_slim_devices(
        self: ControllerComponentManager,
    ) -> None | tuple[ResultCode, str]:
        """
        Configure the SLIM devices

        :return: Either None if the configuration is successful, or a tuple containing a return code
                 and a string message indicating status if the configuration fails
        """
        try:
            self.logger.info(
                f"Setting SLIM simulation mode to {self._talondx_component_manager.simulation_mode}"
            )
            for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
                self._proxies[fqdn].write_attribute(
                    "simulationMode",
                    self._talondx_component_manager.simulation_mode,
                )
                self._proxies[fqdn].command_inout("On")

            # Longer timeout may be needed because the links need to wait
            # for Tx/Rx to be ready. From experience this can be as late
            # as around 5s after HPS master completes configure.
            self._send_configure_slim_device(
                self._fs_slim_fqdn, self._fs_slim_config_path
            )
            self._send_configure_slim_device(
                self._vis_slim_fqdn, self._vis_slim_config_path
            )

            # restore default timeout
            self._proxies[self._fs_slim_fqdn].set_timeout_millis(3000)
            self._proxies[self._vis_slim_fqdn].set_timeout_millis(3000)
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = f"Failed to configure SLIM: {item.reason}"
                self.logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
        except OSError as e:
            log_msg = f"Failed to read SLIM configuration file: {e}"
            return (ResultCode.FAILED, log_msg)

    def is_on_allowed(self: ControllerComponentManager) -> bool:
        self.logger.debug("Checking if on is allowed")

        if self.dish_utils is None:
            self.logger.warning("Dish-VCC mapping has not been provided.")
            return False

        if self._component_state["power"] == PowerState.OFF:
            return True
        self.logger.warning("Already on, do not need to turn on.")
        return False

    def _on(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Turn on the controller and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        self.logger.debug("Entering ControllerComponentManager.on")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        # Power on all the Talon boards if not in SimulationMode
        # TODO: There are two VCCs per LRU. Need to check the number of
        #       VCCs turned on against the number of LRUs powered on
        if (
            self._talondx_component_manager.simulation_mode
            == SimulationMode.FALSE
        ):
            self._fqdn_talon_lru = self._get_talon_lru_fqdns()
            # TODO: handle subscribed events for missing LRUs
        else:
            # Use a hard-coded example fqdn talon lru for simulationMode
            self._fqdn_talon_lru = ["mid_csp_cbf/talon_lru/001"]

        # Turn on all the LRUs with the boards we need
        lru_on_status, msg = self._turn_on_lrus()
        if not lru_on_status:
            task_callback(
                result=(ResultCode.FAILED, msg),
                status=TaskStatus.FAILED,
            )
            return

        # Configure all the Talon boards
        if (
            self._talondx_component_manager.configure_talons()
            == ResultCode.FAILED
        ):
            msg = "Failed to configure Talon boards"
            self.logger.error(msg)
            task_callback(
                result=(ResultCode.FAILED, msg),
                status=TaskStatus.FAILED,
            )
            return

        # Set the Simulation mode of the Subarray and turn it on
        # try:
        #     self._group_subarray.write_attribute(
        #         "simulationMode",
        #         self._talondx_component_manager.simulation_mode,
        #     )
        #     self._group_subarray.command_inout("On")
        # except tango.DevFailed as df:
        #     for item in df.args:
        #         msg = f"Failed to turn on group proxies; {item.reason}"
        #         self.logger.error(msg)
        #     task_callback(
        #         result=(ResultCode.FAILED, msg),
        #         status=TaskStatus.FAILED,
        #     )
        #     return
        

        group_subarray_on_failed = False
        for result_code, msg in self._issue_group_command(command_name="On", proxies=self._group_subarray):
            if result_code == ResultCode.FAILED:
                self.logger.error(msg)
                group_subarray_on_failed = True

        if group_subarray_on_failed:
            task_callback(
                result=(ResultCode.FAILED, "Failed to turn on subarrays"),
                status=TaskStatus.FAILED,
            )
            return

        # Configure SLIM Mesh devices
        configure_slim_result = self._configure_slim_devices()
        if configure_slim_result:
            task_callback(
                result=configure_slim_result,
                status=TaskStatus.FAILED,
            )
            return

        self._update_component_state(power=PowerState.ON)
        task_callback(
            result=(ResultCode.OK, "On completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def on(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit on operation method to task executor queue.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )

    def _subarray_to_empty(
        self: ControllerComponentManager, subarray: context.DeviceProxy
    ) -> tuple[bool, str]:
        """
        Restart subarray observing state model to ObsState.EMPTY
        """
        # if subarray is READY go to IDLE
        if subarray.obsState == ObsState.READY:
            subarray.GoToIdle()
            if subarray.obsState != ObsState.IDLE:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.IDLE,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to send subarray {subarray} to idle, currently in {subarray.obsState}"
                    self.logger.error(log_msg)
                    return (False, log_msg)

        # if subarray is IDLE go to EMPTY by removing all receptors
        if subarray.obsState == ObsState.IDLE:
            subarray.RemoveAllReceptors()
            if subarray.obsState != ObsState.EMPTY:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.EMPTY,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to remove all receptors from subarray {subarray}, currently in {subarray.obsState}"
                    self.logger.error(log_msg)
                    return (False, log_msg)

        # wait if subarray is in the middle of RESOURCING/RESTARTING, as it may return to EMPTY
        if subarray.obsState in [
            ObsState.RESOURCING,
            ObsState.RESTARTING,
        ]:
            try:
                poll(
                    lambda: subarray.obsState
                    not in [
                        ObsState.RESOURCING,
                        ObsState.RESTARTING,
                    ],
                    timeout=const.DEFAULT_TIMEOUT,
                    step=0.5,
                )
            except TimeoutException:
                # raise exception if timed out waiting to exit RESOURCING/RESTARTING
                log_msg = f"Timed out waiting for {subarray} to exit {subarray.obsState}"
                self.logger.error(log_msg)
                return (False, log_msg)

        # if subarray not in EMPTY then we need to ABORT and RESTART
        if subarray.obsState != ObsState.EMPTY:
            # if subarray is in the middle of ABORTING/RESETTING, wait before issuing RESTART/ABORT
            if subarray.obsState in [
                ObsState.ABORTING,
                ObsState.RESETTING,
            ]:
                try:
                    poll(
                        lambda: subarray.obsState
                        not in [
                            ObsState.ABORTING,
                            ObsState.RESETTING,
                        ],
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit ABORTING/RESETTING
                    log_msg = f"Timed out waiting for {subarray} to exit {subarray.obsState}"
                    self.logger.error(log_msg)
                    return (False, log_msg)

            # if subarray not yet in FAULT/ABORTED, issue Abort command to enable Restart
            if subarray.obsState not in [
                ObsState.FAULT,
                ObsState.ABORTED,
            ]:
                subarray.Abort()
                if subarray.obsState != ObsState.ABORTED:
                    try:
                        # TODO: poll causes problem in unit test
                        poll(
                            lambda: subarray.obsState == ObsState.ABORTED,
                            timeout=const.DEFAULT_TIMEOUT,
                            step=0.5,
                        )
                        pass
                    except TimeoutException:
                        # raise exception if timed out waiting to exit ABORTING
                        log_msg = f"Failed to send {subarray} to ObsState.ABORTED, currently in {subarray.obsState}"
                        self.logger.error(log_msg)
                        return (False, log_msg)

            # finally, subarray may be restarted to EMPTY
            subarray.Restart()
            if subarray.obsState != ObsState.EMPTY:
                try:
                    poll(
                        lambda: subarray.obsState == ObsState.EMPTY,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                except TimeoutException:
                    # raise exception if timed out waiting to exit RESTARTING
                    log_msg = f"Failed to restart {subarray}, currently in {subarray.obsState}"
                    self.logger.error(log_msg)
                    return (False, log_msg)

        return (
            True,
            f"Subarray {subarray} succesfully set to ObsState.EMPTY; subarray.obsState = {subarray.obsState}",
        )

    def _turn_off_subelements(
        self: ControllerComponentManager,
    ) -> tuple[bool, list[str]]:
        result = True
        message = []
        
        for result_code, msg in self._issue_group_command("Off", self._group_subarray):
            if result_code == ResultCode.FAILED:
                message.append(msg)
                result = False

        for result_code, msg in self._issue_group_command("Off", self._group_vcc):
            if result_code == ResultCode.FAILED:
                message.append(msg)
                result = False

        for result_code, msg in self._issue_group_command("Off", self._group_fsp):
            if result_code == ResultCode.FAILED:
                message.append(msg)
                result = False

        try:
            for fqdn in [self._fs_slim_fqdn, self._vis_slim_fqdn]:
                self._proxies[fqdn].command_inout("Off")
        except tango.DevFailed as df:
            for item in df.args:
                log_msg = f"Failed to turn off SLIM proxy; {item.reason}"
                self.logger.error(log_msg)
                message.append(log_msg)
            result = False

        if result:
            message.append(
                "Successfully issued off command to all subelements."
            )
        return (result, message)

    def _check_subelements_off(
        self: ControllerComponentManager,
    ) -> tuple[list[str], list[str]]:
        """
        Verify that the subelements are in DevState.OFF, ObsState.EMPTY/IDLE
        """
        op_state_error_list = []
        obs_state_error_list = []
        for fqdn, proxy in self._proxies.items():
            self.logger.debug(f"Checking final state of device {fqdn}")
            # power switch device state is always ON as long as it is
            # communicating and monitoring the PDU; does not implement
            # On/Off commands, rather TurnOn/OffOutlet commands to
            # target specific outlets
            if fqdn not in self._fqdn_power_switch:
                try:
                    # TODO CIP-1899 The cbfcontroller is sometimes
                    # unable to read the State() of the talon_lru
                    # device server due to an error trying to
                    # acquire the serialization monitor. As a temporary
                    # workaround, the cbfcontroller will log these
                    # errors if they occur but continue polling.
                    poll(
                        lambda: proxy.State() == tango.DevState.OFF,
                        ignore_exceptions=(tango.DevFailed),
                        log_error=logging.WARNING,
                        timeout=const.DEFAULT_TIMEOUT,
                        step=0.5,
                    )
                # If the poll timed out while waiting
                # for proxy.State() == tango.DevState.OFF,
                # it throws a TimeoutException
                except TimeoutException:
                    op_state_error_list.append([fqdn, proxy.State()])

            if fqdn in self._fqdn_subarray:
                obs_state = proxy.obsState
                if obs_state != ObsState.EMPTY:
                    obs_state_error_list.append((fqdn, obs_state))

            if fqdn in self._fqdn_vcc:
                obs_state = proxy.obsState
                if obs_state != ObsState.IDLE:
                    obs_state_error_list.append((fqdn, obs_state))

        return (op_state_error_list, obs_state_error_list)

    def _lru_off(self, proxy, lru_fqdn) -> tuple[bool, str]:
        try:
            self.logger.info(f"Turning off LRU {lru_fqdn}")
            proxy.Off()
        except tango.DevFailed as e:
            self.logger.error(e)
            return (False, lru_fqdn)

        self.logger.info(f"LRU successfully turned off: {lru_fqdn}")
        return (True, None)

    def _turn_off_lrus(
        self: ControllerComponentManager,
    ) -> tuple[bool, str]:
        if (
            self._talondx_component_manager.simulation_mode
            == SimulationMode.FALSE
        ):
            if len(self._fqdn_talon_lru) == 0:
                self._fqdn_talon_lru = self._get_talon_lru_fqdns()
                # TODO: handle subscribed events for missing LRUs
        else:
            # use a hard-coded example fqdn talon lru for simulation mode
            self._fqdn_talon_lru = ["mid_csp_cbf/talon_lru/001"]

        # turn off LRUs
        results = [
            self._lru_off(
                self._proxies[fqdn],
                fqdn,
            )
            for fqdn in self._fqdn_talon_lru
        ]

        failed_lrus = []
        out_status = True
        for status, fqdn in results:
            if not status:
                failed_lrus.append(fqdn)
                out_status = False
        return (out_status, f"Failed to power off Talon LRUs: {failed_lrus}")

    def is_off_allowed(self: ControllerComponentManager) -> bool:
        self.logger.debug("Checking if off is allowed")
        if self._component_state["power"] == PowerState.ON:
            return True
        self.logger.info("Already off, do not need to turn off.")
        return False

    def _off(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Turn off the controller and its subordinate devices

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering ControllerComponentManager.off")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        (result_code, message) = (ResultCode.OK, [])

        # reset subarray observing state to EMPTY
        for subarray in [self._proxies[fqdn] for fqdn in self._fqdn_subarray]:
            (subarray_empty, log_msg) = self._subarray_to_empty(subarray)
            if not subarray_empty:
                self.logger.error(log_msg)
                message.append(log_msg)
                result_code = ResultCode.FAILED

        # turn off subelements
        (subelement_off, log_msg) = self._turn_off_subelements()
        message.extend(log_msg)
        if not subelement_off:
            result_code = ResultCode.FAILED

        # HPS master shutdown
        result = self._talondx_component_manager.shutdown()
        if result == ResultCode.FAILED:
            # if HPS master shutdown failed, continue with attempting to
            # shut off power outlets via LRU device
            log_msg = "HPS Master shutdown failed."
            self.logger.warning(log_msg)
            message.append(log_msg)

        # Turn off all the LRUs currently in use
        (lru_off, log_msg) = self._turn_off_lrus()
        if not lru_off:
            message.append(log_msg)
            result_code = ResultCode.FAILED

        # check final device states, log any errors
        (
            op_state_error_list,
            obs_state_error_list,
        ) = self._check_subelements_off()

        if len(op_state_error_list) > 0:
            for fqdn, state in op_state_error_list:
                log_msg = f"{fqdn} failed to turn OFF, current state: {state}"
                self.logger.error(log_msg)
                message.append(log_msg)
            result_code = ResultCode.FAILED

        if len(obs_state_error_list) > 0:
            for fqdn, obs_state in obs_state_error_list:
                log_msg = (
                    f"{fqdn} failed to restart, current obsState: {obs_state}"
                )
                self.logger.error(log_msg)
                message.append(log_msg)
            result_code = ResultCode.FAILED

        if result_code == ResultCode.OK:
            self._update_component_state(power=PowerState.OFF)
            task_callback(
                result=(ResultCode.OK, "Off completed OK"),
                status=TaskStatus.COMPLETED,
            )
        else:
            task_callback(
                result=(ResultCode.FAILED, "; ".join(message)),
                status=TaskStatus.COMPLETED,
            )
        return

    @check_communicating
    def off(
        self: ControllerComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit off operation method to task executor queue.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )

    def _validate_init_sys_param(
        self: ControllerComponentManager,
        params: dict,
    ) -> bool:
        """
        Validate the InitSysParam against the ska-telmodel schema

        :param params: The InitSysParam parameters
        :return: True if the InitSysParam parameters are valid, False otherwise
        """
        try:
            telmodel_validate(
                version=params["interface"], config=params, strictness=2
            )
            self.logger.info(
                "InitSysParam validation against ska-telmodel schema was successful!"
            )
        except ValueError as e:
            self.logger.error(
                f"InitSysParam validation against ska-telmodel schema failed with exception:\n {str(e)}"
            )
            return False
        return True

    def _retrieve_sys_param_file(
        self: ControllerComponentManager,
        init_sys_param_json: dict,
    ) -> tuple[bool, dict]:
        """
        Retrieve the sys_param file from the Telescope Model

        :param init_sys_param_json: The InitSysParam parameters
        """
        # The uri was provided in the input string, therefore the mapping from Dish ID to
        # VCC and frequency offset k needs to be retrieved using the Telescope Model
        tm_data_sources = init_sys_param_json["tm_data_sources"][0]
        tm_data_filepath = init_sys_param_json["tm_data_filepath"]
        try:
            mid_cbf_param_dict = TMData([tm_data_sources])[
                tm_data_filepath
            ].get_dict()
            self.logger.info(
                "Successfully retrieved json data from {tm_data_filepath} in {tm_data_sources}"
            )
        except (ValueError, KeyError) as e:
            self.logger.error(
                f"Retrieving the init_sys_param file failed with exception: \n {str(e)}"
            )
            return (False, None)
        return (True, mid_cbf_param_dict)

    def _update_init_sys_param(
        self: ControllerComponentManager,
        params: str,
    ) -> None:
        """
        Update the InitSysParam parameters in the subarrays and VCCs as well as the talon boards

        :param params: The InitSysParam parameters
        """
        # write the init_sys_param to each of the subarrays
        for fqdn in self._fqdn_subarray:
            self._proxies[fqdn].sysParam = params

        # set VCC values
        for fqdn in self._fqdn_vcc:
            try:
                proxy = self._proxies[fqdn]
                vcc_id = int(proxy.get_property("DeviceID")["DeviceID"][0])
                if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                    dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                    proxy.dishID = dish_id
                    self.logger.info(
                        f"Assigned DISH ID {dish_id} to VCC {vcc_id}"
                    )
                else:
                    log_msg = (
                        f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                        f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                    )
                    self.logger.error(log_msg)
                    return (ResultCode.FAILED, log_msg)
            except tango.DevFailed as df:
                for item in df.args:
                    log_msg = f"Failure in connection to {fqdn}; {item.reason}"
                    self.logger.error(log_msg)
                    return (ResultCode.FAILED, log_msg)

        # update talon boards. The VCC ID to IP address mapping comes
        # from hw_config. Then map VCC ID to DISH ID.
        for vcc_id_str, ip in self._hw_config["talon_board"].items():
            for fqdn in self._fqdn_talon_board:
                try:
                    proxy = self._proxies[fqdn]
                    board_ip = proxy.get_property("TalonDxBoardAddress")[
                        "TalonDxBoardAddress"
                    ][0]
                    if board_ip == ip:
                        vcc_id = int(vcc_id_str)
                        proxy.write_attribute("vccID", str(vcc_id))
                        if vcc_id in self.dish_utils.vcc_id_to_dish_id:
                            dish_id = self.dish_utils.vcc_id_to_dish_id[vcc_id]
                            proxy.write_attribute("dishID", dish_id)
                            self.logger.info(
                                f"Assigned DISH ID {dish_id} to VCC {vcc_id}"
                            )
                        else:
                            log_msg = (
                                f"DISH ID for VCC {vcc_id} not found in DISH-VCC mapping; "
                                f"current mapping: {self.dish_utils.vcc_id_to_dish_id}"
                            )
                            self.logger.warning(log_msg)
                except tango.DevFailed as df:
                    for item in df.args:
                        log_msg = f"Failed to update {fqdn} with VCC ID and DISH ID; {item.reason}"
                        self.logger.error(log_msg)
                        return (ResultCode.FAILED, log_msg)

    def is_init_sys_param_allowed(self: ControllerComponentManager) -> bool:
        self.logger.debug("Checking if init_sys_param is allowed")
        if self._component_state["power"] == PowerState.OFF:
            return True
        self.logger.warning(
            "InitSysParam command cannot be issued because the curremt PowerState is not 'off'."
        )
        return False

    def _init_sys_param(
        self: ControllerComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Validate and save the Dish ID - VCC ID mapping and k values.

        :param argin: the Dish ID - VCC ID mapping and k values in a
                        json string.
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(f"Received sys params {argin}")

        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "InitSysParam", task_callback, task_abort_event
        ):
            return

        def raise_on_duplicate_keys(pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    raise ValueError(f"duplicated key: {k}")
                else:
                    d[k] = v
            return d

        try:
            init_sys_param_json = json.loads(
                argin, object_pairs_hook=raise_on_duplicate_keys
            )
        except ValueError as e:
            self.logger.error(e)
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Duplicated Dish ID in the init_sys_param json",
                ),
                status=TaskStatus.FAILED,
            )
            return

        if not self._validate_init_sys_param(init_sys_param_json):
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Validating init_sys_param file against ska-telmodel schema failed",
                ),
                status=TaskStatus.FAILED,
            )
            return

        # If tm_data_filepath is provided, then we need to retrieve the
        # init sys param file from CAR via the telescope model
        if "tm_data_filepath" in init_sys_param_json:
            passed, init_sys_param_json = self._retrieve_sys_param_file(
                init_sys_param_json
            )
            if not passed:
                task_callback(
                    result=(
                        ResultCode.FAILED,
                        "Retrieving the init_sys_param file failed",
                    ),
                    status=TaskStatus.FAILED,
                )
                return
            if not self._validate_init_sys_param(init_sys_param_json):
                task_callback(
                    result=(
                        ResultCode.FAILED,
                        "Validating init_sys_param file against ska-telmodel schema failed",
                    ),
                    status=TaskStatus.FAILED,
                )
                return
            self._source_init_sys_param = argin
            self._last_init_sys_param = json.dumps(init_sys_param_json)
        else:
            self._source_init_sys_param = ""
            self._last_init_sys_param = argin

        # store the attribute
        self.dish_utils = DISHUtils(init_sys_param_json)

        # send init_sys_param to the subarrays
        try:
            self._update_init_sys_param(self._last_init_sys_param)
        except tango.DevFailed as e:
            self.logger.error(e)
            task_callback(
                result=(
                    ResultCode.FAILED,
                    "Failed to update subarrays with init_sys_param",
                ),
                status=TaskStatus.FAILED,
            )
            return

        task_callback(
            result=(
                ResultCode.OK,
                "InitSysParam completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def init_sys_param(
        self: ControllerComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit init_sys_param operation method to task executor queue.

        :param argin: the Dish ID - VCC ID mapping and k values in a
                        json string.
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._init_sys_param,
            args=[argin],
            is_cmd_allowed=self.is_init_sys_param_allowed,
            task_callback=task_callback,
        )
