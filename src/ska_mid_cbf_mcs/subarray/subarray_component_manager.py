# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
CbfSubarray
Sub-element subarray device for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

import concurrent.futures
import copy
import functools
import json
from threading import Event, Lock, Thread
from typing import Callable, Optional

# Tango imports
import tango
from ska_control_model import (
    AdminMode,
    CommunicationStatus,
    ObsState,
    PowerState,
    ResultCode,
    TaskStatus,
)
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_testing import context
from ska_telmodel.schema import validate as telmodel_validate

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_mcs.commons.global_enum import (
    FspModes,
    const,
    freq_band_dict,
    mhz_to_hz,
    vcc_oversampling_factor,
)
from ska_mid_cbf_mcs.component.obs_component_manager import (
    CbfObsComponentManager,
)


class CbfSubarrayComponentManager(CbfObsComponentManager):
    """A component manager for the CbfSubarray class."""

    @property
    def vcc_ids(self: CbfSubarrayComponentManager) -> list[int]:
        """Return the list of assigned VCC IDs"""
        dish_ids = self.dish_ids.copy()
        if self._dish_utils is not None:
            return [
                self._dish_utils.dish_id_to_vcc_id[dish] for dish in dish_ids
            ]
        self.logger.error(
            "Unable to return VCC IDs as system parameters have not yet been provided."
        )
        return []

    def __init__(
        self: CbfSubarrayComponentManager,
        *args: any,
        subarray_id: int,
        controller: str,
        vcc: list[str],
        fsp: list[str],
        fsp_corr_sub: list[str],
        talon_board: list[str],
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param subarray_id: ID of subarray
        :param controller: FQDN of controller device
        :param vcc: FQDNs of subordinate VCC devices
        :param fsp: FQDNs of subordinate FSP devices
        :param fsp_corr_sub: FQDNs of subordinate FSP CORR subarray devices
        :param talon_board: FQDNs of talon board devices
        """
        super().__init__(*args, **kwargs)

        self.obs_state = ObsState.EMPTY

        self._dish_utils = None

        self.subarray_id = subarray_id
        self._fqdn_controller = controller
        self._fqdn_vcc = vcc
        self._fqdn_fsp = fsp
        self._fqdn_fsp_corr_subarray_device = fsp_corr_sub
        self._fqdn_talon_board_device = talon_board

        # initialize attribute values
        self._sys_param_str = ""
        self.dish_ids = []
        self.frequency_band = 0

        self.last_received_delay_model = ""

        self._delay_model_lock = Lock()

        # store the subscribed telstate events as event_ID:attribute_proxy key:value pairs
        self._events_telstate = {}

        # for easy device-reference
        self._rfi_flagging_mask = {}
        self._frequency_band_offset_stream1 = 0
        self._frequency_band_offset_stream2 = 0
        self._stream_tuning = [0, 0]

        # device proxy for easy reference to CBF controller
        self._proxy_cbf_controller = None
        self._controller_max_capabilities = {}
        self._count_vcc = 0
        self._count_fsp = 0

        # proxies to subelement devices
        self._all_vcc_proxies = []
        self._assigned_vcc_proxies = set()

        self._all_fsp_proxies = []
        self._all_fsp_corr_proxies = []
        self._assigned_fsp_proxies = set()
        self._assigned_fsp_corr_proxies = set()

        self._all_talon_board_proxies = []
        self._assigned_talon_board_proxies = set()

    def _init_controller_proxy(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxy to controller device, read MaxCapabilities property

        :return: False if initialization failed, otherwise True
        """
        try:
            if self._proxy_cbf_controller is None:
                self._proxy_cbf_controller = context.DeviceProxy(
                    device_name=self._fqdn_controller
                )
                self._controller_max_capabilities = dict(
                    pair.split(":")
                    for pair in self._proxy_cbf_controller.maxCapabilities
                )
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        self._count_vcc = int(self._controller_max_capabilities["VCC"])
        self._count_fsp = int(self._controller_max_capabilities["FSP"])

        self._fqdn_vcc = self._fqdn_vcc[: self._count_vcc]
        self._fqdn_fsp = self._fqdn_fsp[: self._count_fsp]
        self._fqdn_fsp_corr_subarray_device = (
            self._fqdn_fsp_corr_subarray_device[: self._count_fsp]
        )

        return True

    def _init_subelement_proxies(self: CbfSubarrayComponentManager) -> bool:
        """
        Initialize proxies to FSP and VCC subelements

        :return: False if initialization failed, otherwise True
        """
        try:
            if len(self._all_vcc_proxies) == 0:
                self._all_vcc_proxies = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._fqdn_vcc
                ]

            if len(self._all_fsp_proxies) == 0:
                self._all_fsp_proxies = [
                    context.DeviceProxy(device_name=fqdn)
                    for fqdn in self._fqdn_fsp
                ]

            if len(self._all_fsp_corr_proxies) == 0:
                for fqdn in self._fqdn_fsp_corr_subarray_device:
                    proxy = context.DeviceProxy(device_name=fqdn)
                    self._all_fsp_corr_proxies.append(proxy)

            if len(self._all_talon_board_proxies) == 0:
                for fqdn in self._fqdn_talon_board_device:
                    proxy = context.DeviceProxy(device_name=fqdn)
                    self._all_talon_board_proxies.append(proxy)

            # for proxy in self._all_fsp_corr_proxies:
            #     proxy.adminMode = AdminMode.ONLINE

        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        return True

    def start_communicating(self: CbfSubarrayComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug(
            "Entering CbfSubarrayComponentManager.start_communicating"
        )

        if self.is_communicating:
            self.logger.info("Already connected.")
            return

        controller_success = self._init_controller_proxy()
        if not controller_success:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        subelement_success = self._init_subelement_proxies()
        if not subelement_success:
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super().start_communicating()
        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self: CbfSubarrayComponentManager) -> None:
        """Stop communication with the component."""
        self.logger.debug(
            "Entering CbfSubarrayComponentManager.stop_communicating"
        )
        try:
            for proxy in self._all_fsp_corr_proxies:
                proxy.adminMode = AdminMode.OFFLINE
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return

        super().stop_communicating()

    @check_communicating
    def on(self: CbfSubarrayComponentManager) -> None:
        """
        Set state to ON
        """
        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    @check_communicating
    def off(self: CbfSubarrayComponentManager) -> None:
        """
        Set state to OFF
        """
        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

    def update_sys_param(
        self: CbfSubarrayComponentManager, sys_param_str: str
    ) -> None:
        """
        Reload sys param from input JSON

        :param sys_param_str: sys params JSON string
        """
        self.logger.debug(f"Received sys param: {sys_param_str}")
        self._sys_param_str = sys_param_str
        sys_param = json.loads(sys_param_str)
        self._dish_utils = DISHUtils(sys_param)
        self.logger.info(
            "Updated DISH ID to VCC ID and frequency offset k mapping"
        )

    def _update_delay_model(
        self: CbfSubarrayComponentManager, model: str
    ) -> None:
        """
        Update FSP and VCC delay models.
        This method is always started in a separate thread.

        :param model: delay model JSON string
        """
        self.logger.info(f"Updating delay model; {model}")

        if model == self.last_received_delay_model:
            self.logger.warning(
                "Ignoring delay model (identical to previous)."
            )
            return
        try:
            delay_model_json = json.loads(model)
        except (
            json.JSONDecodeError
        ) as je:  # delay model string not a valid JSON object
            self.logger.error(
                f"Delay model object is not a valid JSON object; {je}"
            )
            return

        # Validate delay_model_json against the telescope model
        self.logger.info(
            f"Attempting to validate the following json against the telescope model: {delay_model_json}"
        )
        try:
            telmodel_validate(
                version=delay_model_json["interface"],
                config=delay_model_json,
                strictness=1,
            )
            self.logger.info("Delay model is valid!")
        except ValueError as e:
            self.logger.error(
                f"Delay model JSON validation against the telescope model schema failed, ignoring delay model;\n {e}."
            )
            return

        # pass DISH ID as VCC ID integer to FSPs
        for delay_detail in delay_model_json["receptor_delays"]:
            dish_id = delay_detail["receptor"]
            delay_detail["receptor"] = self._dish_utils.dish_id_to_vcc_id[
                dish_id
            ]

        # we lock the mutex, forward the configuration, then unlock it
        with self._delay_model_lock:
            results_fsp = self._issue_group_command(
                command_name="UpdateDelayModel",
                proxies=list(self._assigned_fsp_corr_proxies),
                argin=model,
            )

            for result_code, _ in results_fsp:
                if result_code == ResultCode.FAILED:
                    self.logger.error(
                        "Failed to issue UpdateDelayModel command to FSP devices"
                    )

            self.last_received_delay_model = model

    @check_communicating
    def _delay_model_event_callback(
        self: CbfSubarrayComponentManager, event_data: tango.EventData
    ) -> None:
        """ "
        Callback for delayModel change event subscription.

        :param event_data: the received change event data
        """
        self.logger.debug("Entering _delay_model_event_callback()")

        value = event_data.attr_value.value

        if value is None:
            self.logger.error(
                f"Delay model callback: None value received; {event_data}"
            )
            return
        if self.obs_state != ObsState.READY:
            log_msg = f"Ignoring delay model (obsState not correct). Delay model being passed in is: {value}"
            self.logger.warning(log_msg)
            return

        Thread(target=self._update_delay_model, args=(value,)).start()

    #####################
    # Resourcing Commands
    #####################

    def _get_talon_proxy_from_dish_id(
        self: CbfSubarrayComponentManager,
        dish_id: str,
    ) -> context.DeviceProxy:
        """
        Return the TalonBoard device proxy that matches the DISH ID parameter.

        :param dish_id: the DISH ID
        :return: proxy to Talon board device, or None if failed to initialize proxy
        """
        for proxy in self._all_talon_board_proxies:
            board_dish_id = proxy.dishID
            if board_dish_id == dish_id:
                return proxy
        # Talon board proxy not essential to scan operation, so we log an error
        # but don't cause a failure
        # return None here to fail conditionals later
        self.logger.error(
            f"Couldn't find TalonBoard device with DISH ID {dish_id}; "
            + "unable to update TalonBoard device subarrayID for this DISH."
        )
        return None

    def is_assign_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if AddReceptors command is allowed in current state"""
        self.logger.debug("Checking if AddReceptors is allowed.")
        if self.obs_state not in [ObsState.EMPTY, ObsState.IDLE]:
            self.logger.warning(
                f"AddReceptors not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.EMPTY or IDLE"
            )
            return False
        return True

    def _assign_vcc_thread(
        self: CbfSubarrayComponentManager,
        vcc_proxy: context.DeviceProxy,
        talon_proxy: context.DeviceProxy,
    ) -> bool:
        """
        Thread to perform individual VCC assignment.

        :param vcc_proxy: proxy to VCC
        :param talon_proxy: proxy to Talon board device with matching DISH ID
        :return: True if successfully assigned VCC proxy, otherwise False
        """
        try:
            # Setting simulation mode of VCC proxies based on simulation mode of subarray
            vcc_fqdn = vcc_proxy.dev_name()
            self.logger.info(
                f"Writing {vcc_fqdn} simulation mode to: {self.simulation_mode}"
            )
            vcc_proxy.adminMode = AdminMode.OFFLINE
            vcc_proxy.simulationMode = self.simulation_mode
            vcc_proxy.adminMode = AdminMode.ONLINE
            vcc_proxy.On()

            # change subarray membership of vcc
            vcc_proxy.subarrayMembership = self.subarray_id
            self.logger.debug(
                f"{vcc_fqdn}.subarrayMembership: "
                + f"{vcc_proxy.subarrayMembership}"
            )

            # assign the subarray ID to the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = str(self.subarray_id)

            return True
        except tango.DevFailed as df:
            self.logger.error(f"Failed to assign VCC; {df}")
            return False

    def _assign_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Add receptors/dishes to subarray.

        :param argin: The list of DISH (receptor) IDs to be assigned
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "AddReceptors", task_callback, task_abort_event
        ):
            return

        input_dish_valid, msg = self._dish_utils.are_Valid_DISH_Ids(argin)
        if not input_dish_valid:
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, msg),
            )
            return

        # build list of VCCs to assign
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_add = []
        for dish_id in argin:
            self.logger.debug(f"Attempting to add receptor {dish_id}")

            try:
                vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            except KeyError:
                self.logger.warning(
                    f"Skipping {dish_id}, outside of Mid.CBF max capabilities."
                )
                continue

            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            vcc_subarray_id = vcc_proxy.subarrayMembership

            # only add VCC if it does not already belong to a subarray
            if vcc_subarray_id != 0:
                self.logger.warning(
                    f"Skipping {dish_id}, already assigned to subarray {vcc_subarray_id}"
                )
                continue

            vcc_proxies.append(vcc_proxy)
            talon_proxy = self._get_talon_proxy_from_dish_id(dish_id)
            talon_proxies.append(talon_proxy)
            dish_ids_to_add.append(dish_id)

        if len(dish_ids_to_add) == 0:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "No valid DISH IDs were provided",
                ),
            )
            return

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._assign_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to assign all requested VCCs.",
                ),
            )
            return

        # Update obsState callback if previously unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=True)

        self.dish_ids.extend(dish_ids_to_add)
        receptors_push_val = self.dish_ids.copy()
        receptors_push_val.sort()
        self._device_attr_change_callback("receptors", receptors_push_val)
        self._device_attr_archive_callback("receptors", receptors_push_val)

        self._assigned_vcc_proxies.update(vcc_proxies)
        self._assigned_talon_board_proxies.update(talon_proxies)

        self.logger.info(f"Receptors after adding: {self.dish_ids}")

        task_callback(
            result=(ResultCode.OK, "AddReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def assign_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit AddReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be assigned
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="assign",
                command_thread=self._assign_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_assign_vcc_allowed,
            task_callback=task_callback,
        )

    def is_release_vcc_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if RemoveReceptors command is allowed in current state"""
        self.logger.debug("Checking if RemoveReceptors is allowed.")
        if self.obs_state not in [ObsState.IDLE]:
            self.logger.warning(
                f"RemoveReceptors not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.IDLE"
            )
            return False
        return True

    def _release_vcc_thread(
        self: CbfSubarrayComponentManager,
        vcc_proxy: context.DeviceProxy,
        talon_proxy: context.DeviceProxy,
    ) -> bool:
        """
        Thread to perform individual VCC release.

        :param vcc_proxy: proxy to VCC
        :param talon_proxy: proxy to Talon board device with matching DISH ID
        :return: True if successfully assigned VCC proxy, otherwise False
        """
        try:
            vcc_fqdn = vcc_proxy.dev_name()
            # reset subarrayMembership Vcc attribute:
            vcc_proxy.subarrayMembership = 0
            self.logger.debug(
                f"{vcc_fqdn}.subarrayMembership: "
                + f"{vcc_proxy.subarrayMembership}"
            )
            vcc_proxy.Off()
            vcc_proxy.adminMode = AdminMode.OFFLINE

            # clear the subarray ID off the talon board with the matching DISH ID
            if talon_proxy is not None:
                talon_proxy.subarrayID = ""

            return True
        except tango.DevFailed as df:
            self.logger.error(f"Failed to release VCC; {df}")
            return False

    def _release_vcc_loop(
        self: CbfSubarrayComponentManager, dish_ids: list[str]
    ) -> bool:
        """
        Main loop for use in releasing VCC resources, shared between resource-releasing
        commands and Restart command

        :param dish_ids: list of DISH IDs
        :return: False if unsuccessful in releasing VCCs, otherwise True
        """
        # build list of VCCs to remove
        vcc_proxies = []
        talon_proxies = []
        dish_ids_to_remove = []
        for dish_id in dish_ids:
            self.logger.debug(f"Attempting to remove {dish_id}")

            try:
                vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            except KeyError:
                self.logger.warning(
                    f"Skipping {dish_id}, outside of Mid.CBF max capabilities."
                )
                continue

            if dish_id not in self.dish_ids:
                self.logger.warning(
                    f"Skipping receptor {dish_id} as it is not currently assigned to this subarray."
                )
                continue

            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            vcc_proxies.append(vcc_proxy)
            talon_proxy = self._get_talon_proxy_from_dish_id(dish_id)
            talon_proxies.append(talon_proxy)
            dish_ids_to_remove.append(dish_id)

        if len(dish_ids_to_remove) == 0:
            self.logger.error(
                "Subarray does not currently have any assigned receptors."
            )
            return False

        successes = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                self._release_vcc_thread, vcc_proxies, talon_proxies
            ):
                successes.append(result)

        if not all(successes):
            return False

        updated_dish_ids = [
            dish for dish in self.dish_ids if dish not in dish_ids_to_remove
        ]
        self.dish_ids = updated_dish_ids
        receptors_push_val = self.dish_ids.copy()
        receptors_push_val.sort()
        self._device_attr_change_callback("receptors", receptors_push_val)
        self._device_attr_archive_callback("receptors", receptors_push_val)

        self._assigned_vcc_proxies.difference_update(vcc_proxies)
        self._assigned_talon_board_proxies.difference_update(talon_proxies)

        self.logger.info(f"Receptors after removal: {self.dish_ids}")

        return True

    def _release_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Remove receptors/dishes from subarray.

        :param argin: The list of DISH (receptor) IDs to be removed
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "RemoveReceptors", task_callback, task_abort_event
        ):
            return

        input_dish_valid, msg = self._dish_utils.are_Valid_DISH_Ids(argin)
        if not input_dish_valid:
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, msg),
            )
            return

        # TODO: shouldn't happen
        if len(self.dish_ids) == 0:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Subarray does not currently have any assigned receptors.",
                ),
            )
            return

        release_success = self._release_vcc_loop(dish_ids=argin)
        if not release_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove receptors.",
                ),
            )
            return

        # Update obsState callback if now unresourced
        if len(self.dish_ids) == 0:
            self._update_component_state(resourced=False)

        task_callback(
            result=(ResultCode.OK, "RemoveReceptors completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def release_vcc(
        self: CbfSubarrayComponentManager,
        argin: list[str],
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveReceptors operation method to task executor queue.

        :param argin: The list of DISH (receptor) IDs to be removed
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_vcc,
            ),
            args=[argin],
            is_cmd_allowed=self.is_release_vcc_allowed,
            task_callback=task_callback,
        )

    @check_communicating
    def release_all_vcc(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit RemoveAllReceptors operation method to task executor queue.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="release",
                command_thread=self._release_vcc,
            ),
            args=[self.dish_ids.copy()],
            is_cmd_allowed=self.is_release_vcc_allowed,
            task_callback=task_callback,
        )

    #####################
    # Scan Commands
    #####################

    def _issue_command_all_assigned_resources(
        self: CbfSubarrayComponentManager,
        command_name: str,
        argin: Optional[any] = None,
    ) -> bool:
        """
        Issue command to all subarray-assigned resources

        :param command_name: name of command to issue to proxy group
        :param argin: optional command input argument
        :return: False if any command failed to be issued, otherwise True
        """
        assigned_resources = list(self._assigned_vcc_proxies) + list(
            self._assigned_fsp_corr_proxies
        )
        for result_code, _ in self._issue_group_command(
            command_name=command_name, proxies=assigned_resources, argin=argin
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(
                    f"Failed to issue {command_name} command to assigned resources"
                )
                return False
        return True

    def _validate_input(self: CbfSubarrayComponentManager, argin: str) -> bool:
        """
        Validate scan configuration.

        :param argin: The configuration as JSON formatted string.

        :return: False if validation failed, otherwise True
        """
        self.logger.info("Validating ConfigureScan input JSON...")

        # Validate full_configuration against the telescope model
        try:
            full_configuration = json.loads(argin)
            telmodel_validate(
                version=full_configuration["interface"],
                config=full_configuration,
                strictness=2,
            )
            self.logger.info("Scan configuration is valid!")
        except json.JSONDecodeError as je:  # argument not a valid JSON object
            self.logger.error(
                f"Scan configuration object is not a valid JSON object; {je}"
            )
            return False
        except ValueError as ve:
            self.logger.error(
                f"ConfigureScan JSON validation against the telescope model schema failed;\n {ve}."
            )
            return False

        # TODO: return additional validation as needed

        return True

    def _calculate_dish_sample_rate(
        self: CbfSubarrayComponentManager,
        freq_band_info: dict,
        freq_offset_k: int,
    ) -> int:
        """
        Calculate frequency slice sample rate

        :param freq_band_info: constants pertaining to a given frequency band
        :param freq_offset_k: DISH frequency offset k value
        :return: DISH sample rate
        """
        base_dish_sample_rate_MH = freq_band_info["base_dish_sample_rate_MHz"]
        sample_rate_const = freq_band_info["sample_rate_const"]

        return (base_dish_sample_rate_MH * mhz_to_hz) + (
            sample_rate_const * freq_offset_k * const.DELTA_F
        )

    def _calculate_fs_sample_rate(
        self: CbfSubarrayComponentManager, freq_band: str, dish: str
    ) -> dict:
        """
        Calculate frequency slice sample rate for a given DISH

        :param freq_band: target frequency band
        :param dish: target DISH ID
        :return: VCC output sample rate
        """
        log_msg = (
            f"Calculate fs_sample_rate for freq_band:{freq_band} and {dish}"
        )
        self.logger.info(log_msg)

        # convert the DISH ID to a VCC ID integer using DISHUtils
        vcc_id = self._dish_utils.dish_id_to_vcc_id[dish]

        # find the k value for this DISH
        freq_offset_k = self._dish_utils.dish_id_to_k[dish]
        freq_band_info = freq_band_dict()[freq_band]

        total_num_fs = freq_band_info["total_num_FSs"]

        dish_sample_rate = self._calculate_dish_sample_rate(
            freq_band_info, freq_offset_k
        )

        log_msg = f"dish_sample_rate: {dish_sample_rate}"
        self.logger.debug(log_msg)
        fs_sample_rate = int(
            dish_sample_rate * vcc_oversampling_factor / total_num_fs
        )
        fs_sample_rate_for_band = {
            "vcc_id": vcc_id,
            "fs_sample_rate": fs_sample_rate,
        }
        log_msg = f"fs_sample_rate_for_band: {fs_sample_rate_for_band}"
        self.logger.info(log_msg)

        return fs_sample_rate_for_band

    def _calculate_fs_sample_rates(
        self: CbfSubarrayComponentManager, freq_band: str
    ) -> list[dict]:
        """
        Calculate frequency slice sample rate for all assigned DISH

        :param freq_band: target frequency band
        :return: list of assigned VCC output sample rates
        """
        output_sample_rates = []
        for dish in self.dish_ids:
            output_sample_rates.append(
                self._calculate_fs_sample_rate(freq_band, dish)
            )

        return output_sample_rates

    def _vcc_configure_band(
        self: CbfSubarrayComponentManager,
        configuration: dict[any],
    ) -> bool:
        """
        Issue Vcc ConfigureBand command

        :param configuration: scan configuration dict
        :return: False if VCC ConfigureBand command failed, otherwise True
        """
        self.logger.info("Configuring VCC band...")

        # Prepare args for ConfigureBand
        vcc_success = True
        for dish_id in self.dish_ids:
            # Fetch K-value based on dish_id
            vcc_id = self._dish_utils.dish_id_to_vcc_id[dish_id]
            vcc_proxy = self._all_vcc_proxies[vcc_id - 1]
            freq_offset_k = self._dish_utils.dish_id_to_k[dish_id]
            # Calculate dish sample rate
            dish_sample_rate = self._calculate_dish_sample_rate(
                freq_band_dict()[configuration["frequency_band"]],
                freq_offset_k,
            )
            # Fetch samples per frame for this freq band
            samples_per_frame = freq_band_dict()[
                configuration["frequency_band"]
            ]["num_samples_per_frame"]

            result_code, msg = vcc_proxy.ConfigureBand(
                json.dumps(
                    {
                        "frequency_band": configuration["frequency_band"],
                        "dish_sample_rate": int(dish_sample_rate),
                        "samples_per_frame": int(samples_per_frame),
                    }
                )
            )

            if result_code == ResultCode.FAILED:
                vcc_success = False
                self.logger.error(msg)

        return vcc_success

    def _vcc_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        configuration: dict[any],
    ) -> bool:
        """
        Issue Vcc ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param configuration: Mid.CBF scan configuration dict
        :return: False if VCC ConfigureScan command failed, otherwise True
        """
        self.logger.info("Configuring VCC for scan...")
        # Configure band5Tuning, if frequencyBand is 5a or 5b.
        self.frequency_band = freq_band_dict()[
            common_configuration["frequency_band"]
        ]["band_index"]
        if self.frequency_band in [4, 5]:
            self._stream_tuning = [
                *map(float, common_configuration["band_5_tuning"])
            ]
        else:
            self._stream_tuning = [0, 0]
            self.logger.warning(
                "'band_5_tuning' not specified. Defaulting to [0, 0]."
            )

        # Configure frequency_band_offset_stream1 and 2
        # If not given, use a default value.
        if "frequency_band_offset_stream1" in configuration:
            self._frequency_band_offset_stream1 = int(
                configuration["frequency_band_offset_stream1"]
            )
        else:
            self._frequency_band_offset_stream1 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream1' not specified. Defaulting to 0."
            )
        if "frequency_band_offset_stream2" in configuration:
            self._frequency_band_offset_stream2 = int(
                configuration["frequency_band_offset_stream2"]
            )
        else:
            self._frequency_band_offset_stream2 = 0
            self.logger.warning(
                "'frequencyBandOffsetStream2' not specified. Defaulting to 0."
            )

        # Configure rfi_flagging_mask
        # If not given, use a default value.
        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = configuration["rfi_flagging_mask"]
        else:
            self._rfi_flagging_mask = {}
            self.logger.warning(
                "'rfi_flagging_mask' not specified. Defaulting to none."
            )

        config_dict = {
            "config_id": self.config_id,
            "frequency_band": common_configuration["frequency_band"],
            "band_5_tuning": self._stream_tuning,
            "frequency_band_offset_stream1": self._frequency_band_offset_stream1,
            "frequency_band_offset_stream2": self._frequency_band_offset_stream2,
            "rfi_flagging_mask": self._rfi_flagging_mask,
        }

        # Add subset of FSP configuration to the VCC configure scan argument
        reduced_fsp = []
        for fsp in configuration["fsp"]:
            function_mode = fsp["function_mode"]
            fsp_cfg = {"fsp_id": fsp["fsp_id"], "function_mode": function_mode}
            if function_mode == "CORR":
                fsp_cfg["frequency_slice_id"] = fsp["frequency_slice_id"]
            reduced_fsp.append(fsp_cfg)
        config_dict["fsp"] = reduced_fsp

        vcc_success = True
        for result_code, _ in self._issue_group_command(
            command_name="ConfigureScan",
            proxies=list(self._assigned_vcc_proxies),
            argin=json.dumps(config_dict),
        ):
            if result_code == ResultCode.FAILED:
                self.logger.error(
                    "Failed to issue ConfigureScan command to VCC devices"
                )
                vcc_success = False

        return vcc_success

    def _assign_fsp_corr(
        self: CbfSubarrayComponentManager, fsp_id: int, function_mode: str
    ) -> bool:
        """
        Set FSP function mode and add subarray membership

        :param fsp_id: ID of FSP to assign
        :param function_mode: target FSP function mode
        :return: False if failed to configure FSP device, True otherwise
        """
        self.logger.info(f"Assigning FSP {fsp_id} to subarray...")

        fsp_proxy = self._all_fsp_proxies[fsp_id - 1]
        fsp_corr_proxy = self._all_fsp_corr_proxies[fsp_id - 1]
        try:
            # TODO handle LRCs

            # set FSP devices simulationMode attributes
            fsp_corr_proxy.adminMode = AdminMode.OFFLINE
            fsp_corr_proxy.simulationMode = self.simulation_mode
            fsp_corr_proxy.adminMode = AdminMode.ONLINE
            fsp_proxy.adminMode = AdminMode.OFFLINE
            fsp_proxy.simulationMode = self.simulation_mode
            fsp_proxy.adminMode = AdminMode.ONLINE

            # only set function mode if FSP is both IDLE and not configured for
            # another mode
            current_function_mode = fsp_proxy.functionMode
            if current_function_mode != FspModes[function_mode].value:
                if current_function_mode != FspModes.IDLE.value:
                    self.logger.error(
                        f"Unable to configure FSP {fsp_id} for function mode {function_mode}, as it is currently configured for function mode {current_function_mode}"
                    )
                    return False

                # if FSP function mode is IDLE, turn on FSP and set function mode
                result = fsp_proxy.On()
                if result[0] == ResultCode.FAILED:
                    self.logger.error(result[1])
                    return False

                result = fsp_proxy.SetFunctionMode(function_mode)
                if result[0] == ResultCode.FAILED:
                    self.logger.error(result[1])
                    return False

            # finally, add subarray membership, which powers on this subarray's
            # FSP function mode devices
            result = fsp_proxy.AddSubarrayMembership(self.subarray_id)
            if result[0] == ResultCode.FAILED:
                self.logger.error(result[1])
                return False
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        self._assigned_fsp_proxies.add(fsp_proxy)
        self._assigned_fsp_corr_proxies.add(fsp_corr_proxy)
        return True

    def _release_all_fsp(self: CbfSubarrayComponentManager) -> bool:
        """
        Remove subarray membership and return FSP to IDLE state if possible

        :return: False if failed to release FSP device, True otherwise
        """
        self.logger.info("Releasing all FSP from subarray...")

        try:
            # remove subarray membership from assigned FSP
            for fsp_proxy in self._assigned_fsp_proxies:
                result = fsp_proxy.RemoveSubarrayMembership(self.subarray_id)
                if result[0] == ResultCode.FAILED:
                    self.logger.error(result[1])
                    return False
        except tango.DevFailed as df:
            self.logger.error(f"{df}")
            return False

        self._assigned_fsp_proxies = set()
        self._assigned_fsp_corr_proxies = set()
        return True

    def _fsp_configure_scan(
        self: CbfSubarrayComponentManager,
        common_configuration: dict[any],
        configuration: dict[any],
    ) -> bool:
        """
        Issue FSP function mode subarray ConfigureScan command

        :param common_configuration: common Mid.CSP scan configuration dict
        :param configuration: Mid.CBF scan configuration dict
        :return: False if FSP ConfigureScan command failed, otherwise True
        """
        self.logger.info("Configuring FSP for scan...")

        # build FSP configuration JSONs, add FSP
        fsp_success = True
        corr_config = []
        for config in configuration["fsp"]:
            fsp_config = copy.deepcopy(config)

            # Add configID, frequency_band, band_5_tuning, and sub_id to fsp.
            # They are not included in the "fsp" portion of the JSON
            fsp_config["config_id"] = common_configuration["config_id"]
            fsp_config["sub_id"] = common_configuration["subarray_id"]
            fsp_config["frequency_band"] = common_configuration[
                "frequency_band"
            ]
            fsp_config["band_5_tuning"] = self._stream_tuning
            fsp_config[
                "frequency_band_offset_stream1"
            ] = self._frequency_band_offset_stream1
            fsp_config[
                "frequency_band_offset_stream2"
            ] = self._frequency_band_offset_stream2

            # Add channel_offset if it was omitted from the configuration (it is optional).
            if "channel_offset" not in fsp_config:
                self.logger.warning(
                    "channel_offset not defined in configuration. Assigning default of 1."
                )
                fsp_config["channel_offset"] = 1

            # Add the fs_sample_rate for all dishes
            fsp_config["fs_sample_rates"] = self._calculate_fs_sample_rates(
                common_configuration["frequency_band"]
            )

            # Add all DISH IDs for subarray and for correlation to fsp
            # Parameter named "subarray_vcc_ids" used by HPS contains all the
            # VCCs assigned to the subarray
            # Parameter named "corr_vcc_ids" used by HPS contains the
            # subset of the subarray VCCs for which the correlation results
            # are requested to be used in Mid.CBF output products (visibilities)
            fsp_config["subarray_vcc_ids"] = []
            for dish in self.dish_ids:
                fsp_config["subarray_vcc_ids"].append(
                    self._dish_utils.dish_id_to_vcc_id[dish]
                )

            match fsp_config["function_mode"]:
                case "CORR":
                    # dishes may not be specified in the
                    # configuration at all, or the list may be empty
                    fsp_config["corr_vcc_ids"] = []
                    if (
                        "receptors" not in fsp_config
                        or len(fsp_config["receptors"]) == 0
                    ):
                        # In this case by the ICD, all subarray allocated resources should be used.
                        fsp_config["corr_vcc_ids"] = fsp_config[
                            "subarray_vcc_ids"
                        ].copy()
                    else:
                        for dish in fsp_config["receptors"]:
                            fsp_config["corr_vcc_ids"].append(
                                self._dish_utils.dish_id_to_vcc_id[dish]
                            )

                    corr_config.append(fsp_config)

                    # set function mode and add subarray membership
                    fsp_success = self._assign_fsp_corr(
                        fsp_id=int(fsp_config["fsp_id"]), function_mode="CORR"
                    )
                case _:
                    self.logger.error(
                        f"Function mode {fsp_config['function_mode']} currently unsupported."
                    )
                    fsp_success = False

        if not fsp_success or len(corr_config) == 0:
            return False

        # Call ConfigureScan for all FSP function mode subarray devices
        # NOTE: corr_config is a list of fsp config JSON objects, each
        #      augmented by a number of vcc-fsp common parameters
        for fsp_config in corr_config:
            try:
                # TODO handle fsp corr LRC
                self.logger.debug(f"fsp_config: {json.dumps(fsp_config)}")
                fsp_corr_proxy = self._all_fsp_corr_proxies[
                    int(fsp_config["fsp_id"]) - 1
                ]
                fsp_corr_proxy.set_timeout_millis(12000)
                fsp_corr_proxy.ConfigureScan(json.dumps(fsp_config))

            except tango.DevFailed as df:
                self.logger.error(
                    "Failed to issue ConfigureScan to FSP CORR subarray device "
                    + f"{fsp_corr_proxy.dev_name()}; {df}"
                )
                fsp_success = False

        return fsp_success

    def _subscribe_tm_event(
        self: CbfSubarrayComponentManager,
        subscription_point: str,
        callback: Callable,
    ) -> bool:
        """
        Subscribe to change events on TM-published data subscription point

        :param subscription_point: FQDN of TM data subscription point
        :param callback: callback for event subscription
        :return: False if VCC ConfigureScan command failed, otherwise True
        """
        self.logger.info(f"Attempting subscription to {subscription_point}")

        # split delay_model_subscription_point between device FQDN and attribute name
        subscription_point_split = subscription_point.split("/")
        fqdn = "/".join(subscription_point_split[:-1])
        attr_name = subscription_point_split[-1]

        try:
            proxy = context.DeviceProxy(device_name=fqdn)
            event_id = proxy.subscribe_event(
                attr_name,
                tango.EventType.CHANGE_EVENT,
                callback,
            )
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to subscribe to change events for {subscription_point}; {df}"
            )
            return False

        self.logger.info(
            f"Subscribed to {subscription_point}; event ID: {event_id}"
        )
        self._events_telstate[event_id] = proxy
        return True

    def _deconfigure(
        self: CbfSubarrayComponentManager,
    ) -> bool:
        """
        Completely deconfigure the subarray; all initialization performed by the
        ConfigureScan command must be 'undone' here.

        :return: False if failed to deconfigure, otherwise True
        """
        self.logger.info("Deconfiguring subarray...")

        # component_manager._deconfigure is invoked by GoToIdle, ConfigureScan,
        # ObsReset and Restart here in the CbfSubarray
        if len(self._assigned_fsp_proxies) > 0:
            fsp_success = self._release_all_fsp()
            if not fsp_success:
                return False

        try:
            # unsubscribe from TMC events
            for event_id in list(self._events_telstate.keys()):
                self._events_telstate[event_id].remove_event(event_id)
                del self._events_telstate[event_id]
        except tango.DevFailed as df:
            self.logger.error(f"Error in unsubscribing from TM events; {df}")
            return False

        self.scan_id = 0
        self.config_id = ""
        self.frequency_band = 0
        self._last_received_delay_model = ""

        return True

    def _configure_scan(
        self: CbfSubarrayComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute configure scan operation.

        :param argin: JSON string with the configure scan parameters
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ConfigureScan", task_callback, task_abort_event
        ):
            return

        validation_success = self._validate_input(argin)
        if not validation_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate ConfigureScan input JSON",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        full_configuration = json.loads(argin)
        common_configuration = copy.deepcopy(full_configuration["common"])
        configuration = copy.deepcopy(full_configuration["cbf"])

        # store configID
        self.config_id = str(common_configuration["config_id"])

        vcc_configure_band_success = self._vcc_configure_band(
            configuration=common_configuration
        )
        if not vcc_configure_band_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureBand command to VCC",
                ),
            )
            return

        vcc_configure_scan_success = self._vcc_configure_scan(
            common_configuration=common_configuration,
            configuration=configuration,
        )
        if not vcc_configure_scan_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to VCC",
                ),
            )
            return

        # Configure delayModel subscription point
        delay_model_success = self._subscribe_tm_event(
            subscription_point=configuration["delay_model_subscription_point"],
            callback=self._delay_model_event_callback,
        )
        if not delay_model_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to subscribe to delayModel attribute",
                ),
            )
            return

        fsp_configure_scan_success = self._fsp_configure_scan(
            common_configuration=common_configuration,
            configuration=configuration,
        )
        if not fsp_configure_scan_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ConfigureScan command to FSP",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(configured=True)

        task_callback(
            result=(ResultCode.OK, "ConfigureScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _scan(
        self: CbfSubarrayComponentManager,
        argin: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Start subarray Scan operation.

        :param argin: The scan ID as JSON formatted string.
        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Scan", task_callback, task_abort_event
        ):
            return

        scan = json.loads(argin)

        # Validate scan_json against the telescope model
        try:
            telmodel_validate(
                version=scan["interface"], config=scan, strictness=1
            )
            self.logger.info("Scan is valid!")
        except ValueError as ve:
            self.logger.error(
                f"Scan validation against ska-telmodel schema failed with exception:\n {ve}"
            )
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to validate Scan input JSON",
                ),
            )
            return

        # issue Scan to assigned resources
        scan_id = scan["scan_id"]
        scan_success = self._issue_command_all_assigned_resources(
            command_name="Scan", argin=scan_id
        )
        if not scan_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Scan command to VCC/FSP",
                ),
            )
            return

        self.scan_id = scan_id

        # Update obsState callback
        self._update_component_state(scanning=True)

        task_callback(
            result=(ResultCode.OK, "Scan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _end_scan(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        End scan operation.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "EndScan", task_callback, task_abort_event
        ):
            return

        # issue EndScan to assigned resources
        end_scan_success = self._issue_command_all_assigned_resources(
            command_name="EndScan"
        )
        if not end_scan_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue EndScan command to VCC/FSP",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(scanning=False)

        task_callback(
            result=(ResultCode.OK, "EndScan completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _go_to_idle(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Execute observing state transition from READY to IDLE.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "GoToIdle", task_callback, task_abort_event
        ):
            return

        # issue GoToIdle to assigned resources
        idle_success = self._issue_command_all_assigned_resources(
            command_name="GoToIdle"
        )
        if not idle_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue GoToIdle command to VCC/FSP",
                ),
            )
            return

        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # Update obsState callback
        self._update_component_state(configured=False)

        task_callback(
            result=(ResultCode.OK, "GoToIdle completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _abort(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Abort the current scan operation.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Abort", task_callback, task_abort_event
        ):
            return

        # issue Abort to assigned resources
        abort_success = self._issue_command_all_assigned_resources(
            command_name="Abort"
        )
        if not abort_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue Abort command to VCC/FSP",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "Abort completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def _obs_reset(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation to IDLE from ABORTED or FAULT.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "ObsReset", task_callback, task_abort_event
        ):
            return

        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self._component_state["obsfault"]:
            abort_success = self._issue_command_all_assigned_resources(
                command_name="Abort"
            )
            if not abort_success:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return

        obsreset_success = self._issue_command_all_assigned_resources(
            command_name="ObsReset"
        )
        if not obsreset_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "ObsReset completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    def is_restart_allowed(self: CbfSubarrayComponentManager) -> bool:
        """Check if Restart command is allowed in current state"""
        self.logger.debug("Checking if Restart is allowed.")
        if self.obs_state not in [ObsState.ABORTED, ObsState.FAULT]:
            self.logger.warning(
                f"Restart not allowed in ObsState {self.obs_state}; "
                + "must be in ObsState.ABORTED or FAULT"
            )
            return False
        return True

    def _restart(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """
        Reset the scan operation to EMPTY from ABORTED or FAULT.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :param task_abort_event: event indicating AbortCommands has been issued
        """
        # set task status in progress, check for abort event
        task_callback(status=TaskStatus.IN_PROGRESS)
        if self.task_abort_event_is_set(
            "Restart", task_callback, task_abort_event
        ):
            return

        # if subarray is in FAULT, we must first abort VCC and FSP operation
        # this will allow us to call ObsReset on them even if they are not in FAULT
        if self._component_state["obsfault"]:
            abort_success = self._issue_command_all_assigned_resources(
                command_name="Abort"
            )
            if not abort_success:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to issue Abort command to VCC/FSP",
                    ),
                )
                return

        obsreset_success = self._issue_command_all_assigned_resources(
            command_name="ObsReset"
        )
        if not obsreset_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to issue ObsReset command to VCC/FSP",
                ),
            )
            return

        # We might have interrupted a long-running command such as a Configure
        # or a Scan, so we need to clean up from that.
        # deconfigure to reset assigned FSPs and unsubscribe from events.
        deconfigure_success = self._deconfigure()
        if not deconfigure_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to deconfigure subarray",
                ),
            )
            return

        # remove all assigned VCCs to return to EMPTY
        release_success = self._release_vcc_loop(dish_ids=self.dish_ids.copy())
        if not release_success:
            task_callback(
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "Failed to remove receptors.",
                ),
            )
            return

        task_callback(
            result=(ResultCode.OK, "Restart completed OK"),
            status=TaskStatus.COMPLETED,
        )
        return

    @check_communicating
    def restart(
        self: CbfSubarrayComponentManager,
        task_callback: Optional[Callable] = None,
    ) -> tuple[TaskStatus, str]:
        """
        Submit Restart operation method to task executor queue.

        :param task_callback: callback for driving status of task executor's
            current LRC task
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (TaskStatus, str)
        """
        self.logger.debug(f"Component state: {self._component_state}")
        return self.submit_task(
            func=functools.partial(
                self._obs_command_with_callback,
                hook="restart",
                command_thread=self._restart,
            ),
            is_cmd_allowed=self.is_restart_allowed,
            task_callback=task_callback,
        )
