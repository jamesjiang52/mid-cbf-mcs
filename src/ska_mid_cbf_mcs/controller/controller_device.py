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
CbfController
Sub-element controller device for Mid.CBf
"""

from __future__ import annotations  # allow forward references in type hints

from re import T
from typing import List, Optional, Tuple

import tango
from ska_tango_base import SKABaseDevice, SKAController
from ska_tango_base.commands import ResponseCommand, ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode
from tango import AttrWriteType, DebugIt, DevState
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.controller.talondx_component_manager import (
    TalonDxComponentManager,
)

__all__ = ["CbfController", "main"]


class CbfController(SKAController):

    """
    CbfController TANGO device class.
    Primary point of contact for monitoring and control of Mid.CBF. Implements state and mode indicators, and a set of state transition commmands.
    """

    # PROTECTED REGION ID(CbfController.class_variable) ENABLED START #

    # PROTECTED REGION END #    //  CbfController.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CbfSubarray = device_property(dtype=("str",))

    VCC = device_property(dtype=("str",))

    FSP = device_property(dtype=("str",))

    TalonLRU = device_property(dtype=("str",))

    TalonBoard = device_property(dtype=("str",))

    PowerSwitch = device_property(dtype=("str",))

    FsSLIM = device_property(dtype=("str"))

    VisSLIM = device_property(dtype=("str"))

    TalonDxConfigPath = device_property(dtype=("str"))

    HWConfigPath = device_property(dtype=("str"))

    FsSLIMConfigPath = device_property(dtype=("str"))

    VisSLIMConfigPath = device_property(dtype=("str"))

    LruTimeout = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    commandProgress = attribute(
        dtype="uint16",
        label="Command progress percentage",
        max_value=100,
        min_value=0,
        polling_period=3000,
        abs_change=5,
        rel_change=2,
        doc="Percentage progress implemented for commands that result in state/mode transitions for a large \nnumber of components and/or are executed in stages (e.g power up, power down)",
    )

    sysParam = attribute(
        dtype="str",
        access=AttrWriteType.READ,
        label="Dish ID to VCC and frequency offset k mapping",
        doc="Maps Dish ID to VCC and frequency offset k. The string is in JSON format.",
    )

    sourceSysParam = attribute(
        dtype="str",
        access=AttrWriteType.READ,
        label="The location of the file containing Dish ID to VCC and frequency offset k mapping.",
        doc="Source and file path to the file to be retrieved through the Telescope Model. The string is in JSON format.",
    )

    simulationMode = attribute(
        dtype=SimulationMode,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
    )

    @attribute(
        dtype="DevBoolean",
        access=AttrWriteType.READ_WRITE,
        label="Restrictive Validation of Supported Configurations",
        doc="Flag to indicate if a restrictive validation is requested for "
        "supported configurations, such as with Scan Configurations. "
        "Defaults to True",
    )
    def validateSupportedConfiguration(self: CbfController) -> bool:
        """
        Reads and return the value in the validateSupportedConfiguration

        :return: the value in validateSupportedConfiguration
        :rtype: bool
        """
        res = self.component_manager.validateSupportedConfiguration
        return res

    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: CbfController) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object("On", self.OnCommand(*device_args))

        self.register_command_object("Off", self.OffCommand(*device_args))

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

        self.register_command_object(
            "InitSysParam", self.InitSysParamCommand(*device_args)
        )

    def get_num_capabilities(
        self: CbfController,
    ) -> None:
        # self._max_capabilities inherited from SKAController
        # check first if property exists in DB
        """Get number of capabilities for _init_Device.
        If property not found in db, then assign a default amount(197,27,16)"""

        if self._max_capabilities:
            return self._max_capabilities
        else:
            self.logger.warning("MaxCapabilities device property not defined")

    class InitCommand(SKAController.InitCommand):
        def _get_num_capabilities(
            self: CbfController.InitCommand,
        ) -> None:
            # self._max_capabilities inherited from SKAController
            # check first if property exists in DB
            """Get number of capabilities for _init_Device.
            If property not found in db, then assign a default amount(197,27,16)
            """

            device = self.target

            device.write_simulationMode(True)
            device.write_validateSupportedConfiguration(True)

            if device._max_capabilities:
                try:
                    device._count_vcc = device._max_capabilities["VCC"]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "VCC capabilities not defined; defaulting to 197."
                    )
                    device._count_vcc = 197

                try:
                    device._count_fsp = device._max_capabilities["FSP"]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "FSP capabilities not defined; defaulting to 27."
                    )
                    device._count_fsp = 27

                try:
                    device._count_subarray = device._max_capabilities[
                        "Subarray"
                    ]
                except KeyError:  # not found in DB
                    self.logger.warning(
                        "Subarray capabilities not defined; defaulting to 16."
                    )
                    device._count_subarray = 16
            else:
                self.logger.warning(
                    "MaxCapabilities device property not defined - \
                    using default value"
                )

        def do(
            self: CbfController.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.
            :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
            :return: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")
            message = "Entering InitCommand()"
            self.logger.info(message)

            super().do()

            device = self.target

            # initialize attribute values
            device._command_progress = 0

            # defines self._count_vcc, self._count_fsp, and self._count_subarray
            self._get_num_capabilities()

            # # initialize attribute values
            device._command_progress = 0

            # TODO remove when upgrading base class from 0.11.3
            device.set_change_event("healthState", True, True)

            message = "CbfController Init command completed OK"
            self.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self: CbfController) -> None:
        # PROTECTED REGION ID(CbfController.always_executed_hook) ENABLED START #
        """
        Hook to be executed before any command.
        """
        # PROTECTED REGION END #    //  CbfController.always_executed_hook

    def create_component_manager(
        self: CbfController,
    ) -> ControllerComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        # Create the Talon-DX component manager and initialize simulation
        # mode to on
        self._simulation_mode = SimulationMode.TRUE
        self._talondx_component_manager = TalonDxComponentManager(
            talondx_config_path=self.TalonDxConfigPath,
            hw_config_path=self.HWConfigPath,
            simulation_mode=self._simulation_mode,
            logger=self.logger,
        )

        return ControllerComponentManager(
            get_num_capabilities=self.get_num_capabilities,
            vcc_fqdns_all=self.VCC,
            fsp_fqdns_all=self.FSP,
            subarray_fqdns_all=self.CbfSubarray,
            talon_lru_fqdns_all=self.TalonLRU,
            talon_board_fqdns_all=self.TalonBoard,
            power_switch_fqdns_all=self.PowerSwitch,
            fs_slim_fqdn=self.FsSLIM,
            vis_slim_fqdn=self.VisSLIM,
            lru_timeout=int(self.LruTimeout),
            talondx_component_manager=self._talondx_component_manager,
            talondx_config_path=self.TalonDxConfigPath,
            hw_config_path=self.HWConfigPath,
            fs_slim_config_path=self.FsSLIMConfigPath,
            vis_slim_config_path=self.VisSLIMConfigPath,
            logger=self.logger,
            push_change_event=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    def delete_device(self: CbfController) -> None:
        """Unsubscribe to events, turn all the subarrays, VCCs and FSPs off"""
        # PROTECTED REGION ID(CbfController.delete_device) ENABLED START #
        # PROTECTED REGION END #    //  CbfController.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_commandProgress(self: CbfController) -> int:
        # PROTECTED REGION ID(CbfController.commandProgress_read) ENABLED START #
        """Return commandProgress attribute: percentage progress implemented for
        commands that result in state/mode transitions for a large number of
        components and/or are executed in stages (e.g power up, power down)"""
        return self._command_progress
        # PROTECTED REGION END #    //  CbfController.commandProgress_read

    def read_sysParam(self: CbfController) -> str:
        # PROTECTED REGION ID(CbfController.read_sysParam) ENABLED START #
        """Return the mapping from Dish ID to VCC and frequency offset k. The string is in JSON format."""
        return self.component_manager._init_sys_param
        # PROTECTED REGION END #    //  CbfController.sysParam_read

    def read_sourceSysParam(self: CbfController) -> str:
        # PROTECTED REGION ID(CbfController.read_sourceSysParam) ENABLED START #
        """Return the location of the json file that contains the mapping from
        Dish ID to VCC and frequency offset k, to be retrieved using the Telescope Model.
        """
        return self.component_manager._source_init_sys_param
        # PROTECTED REGION END #    //  CbfController.read_sourceSysParam

    def read_dishToVcc(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.dishToVcc_read) ENABLED START #
        """Return 'dishID:vccID'"""
        if self.component_manager.dish_utils is None:
            return []
        out_str = [
            f"{r}:{v}"
            for r, v in self.component_manager.dish_utils.dish_id_to_vcc_id.items()
        ]

        return out_str
        # PROTECTED REGION END #    //  CbfController.dishToVcc_read

    def read_vccToDish(self: CbfController) -> List[str]:
        # PROTECTED REGION ID(CbfController.vccToDish_read) ENABLED START #
        """Return dishToVcc attribute: 'vccID:dishID'"""
        if self.component_manager.dish_utils is None:
            return []
        out_str = [
            f"{v}:{r}"
            for r, v in self.component_manager.dish_utils.dish_id_to_vcc_id.items()
        ]
        return out_str
        # PROTECTED REGION END #    //  CbfController.vccToDish_read

    def write_simulationMode(
        self: CbfController, value: SimulationMode
    ) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: SimulationMode
        """
        super().write_simulationMode(value)
        self._talondx_component_manager.simulation_mode = value

    def write_validateSupportedConfiguration(
        self: CbfController, value: bool
    ) -> None:
        """
        Sets the validateSupportedConfiguration flag of the device and the
        component manager.

        A warning level log is created when the flag is set to False.

        :param value: Set the flag to True/False
        """
        if value is False:
            msg = (
                "Setting validateSupportedConfiguration to False. "
                "This prevent restrictive checking with Configurations in "
                "MCS"
            )
            self.logger.warning(msg)

        self.component_manager.validateSupportedConfiguration = value

    # --------
    # Commands
    # --------

    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the CbfController's On() command.
        """

        def is_allowed(
            self: CbfController.OnCommand, raise_if_disallowed=False
        ) -> bool:
            """
            Determine if OnCommand is allowed.

            :return: if OnCommand is allowed
            :rtype: bool
            """
            result = super().is_allowed(raise_if_disallowed)
            if self.target.get_state() == tango.DevState.ON:
                result = False
            return result

        def do(
            self: CbfController.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.info("Trying ON Command")

            (result_code, message) = self.target.component_manager.on()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.ON)
                self.logger.info(message)
            elif result_code == ResultCode.FAILED:
                self.logger.error(message)

            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the CbfController's Off() command.
        """

        def is_allowed(
            self: CbfController.OffCommand, raise_if_disallowed=False
        ) -> bool:
            """
            Determine if OffCommand is allowed.

            :return: if OffCommand is allowed
            :rtype: bool
            """
            result = super().is_allowed(raise_if_disallowed)
            if self.target.get_state() == tango.DevState.OFF:
                result = False
            return result

        def do(
            self: CbfController.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                (result_code, message) = self.target.component_manager.off()
            else:
                result_code = ResultCode.FAILED
                message = f"Off command is not allowed when op state is {self.target.op_state_model.op_state}"

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.OFF)
                self.logger.info(message)
            elif result_code == ResultCode.FAILED:
                self.logger.error(message)

            return (result_code, message)

    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the CbfController's Standby() command.
        """

        def do(
            self: CbfController.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.
            Turn off subarray, vcc, fsp, turn CbfController to standby

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = self.target.component_manager.standby()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.STANDBY)

            self.logger.info(message)
            return (result_code, message)

    class InitSysParamCommand(ResponseCommand):
        """
        A class for the CbfController's InitSysParam() command.
        """

        def is_allowed(self: CbfController.InitSysParamCommand) -> bool:
            """
            Determine if InitSysParamCommand is allowed
            (allowed when state is OFF).

            :return: if InitSysParamCommand is allowed
            :rtype: bool
            """
            return self.target.op_state_model.op_state == DevState.OFF

        def do(
            self: CbfController.InitSysParamCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            This command sets the Dish ID - VCC ID mapping and k values

            :param argin: the Dish ID - VCC ID mapping and frequency offset (k)
                in a json string.
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            if not self.is_allowed():
                return (
                    ResultCode.FAILED,
                    "InitSysParam command may be called only when state is OFF",
                )

            (
                result_code,
                message,
            ) = self.target.component_manager.init_sys_param(argin)

            if result_code == ResultCode.OK:
                self.logger.info(message)
            elif result_code == ResultCode.FAILED:
                self.logger.error(message)

            return (result_code, message)

    @command(
        dtype_in="DevString",
        doc_in="the Dish ID - VCC ID mapping and frequency offset (k) in a json string",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def InitSysParam(
        self: CbfController, argin: str
    ) -> tango.DevVarLongStringArray:
        # PROTECTED REGION ID(CbfController.InitSysParam) ENABLED START #
        handler = self.get_command_object("InitSysParam")
        return_code, message = handler(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  CbfController.InitSysParam

    # ----------
    # Callbacks
    # ----------
    def _communication_status_changed(
        self: CbfController, communication_status: CommunicationStatus
    ) -> None:
        """
        Handle change in communications status between component manager and component.

        This is a callback hook, called by the component manager when
        the communications status changes. It is implemented here to
        drive the op_state.

        :param communication_status: the status of communications
            between the component manager and its component.
        """

        self._communication_status = communication_status

        if communication_status == CommunicationStatus.DISABLED:
            self.op_state_model.perform_action("component_disconnected")
        elif communication_status == CommunicationStatus.NOT_ESTABLISHED:
            self.op_state_model.perform_action("component_unknown")

    def _component_power_mode_changed(
        self: CbfController, power_mode: PowerMode
    ) -> None:
        """
        Handle change in the power mode of the component.

        This is a callback hook, called by the component manager when
        the power mode of the component changes. It is implemented here
        to drive the op_state.

        :param power_mode: the power mode of the component.
        """
        self._component_power_mode = power_mode

        if self._communication_status == CommunicationStatus.ESTABLISHED:
            action_map = {
                PowerMode.OFF: "component_off",
                PowerMode.STANDBY: "component_standby",
                PowerMode.ON: "component_on",
                PowerMode.UNKNOWN: "component_unknown",
            }

            self.op_state_model.perform_action(action_map[power_mode])

    def _component_fault(self: CbfController, faulty: bool) -> None:
        """
        Handle component fault

        :param faulty: whether the component has faulted.
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")
        else:
            self.set_status("The device has recovered from FAULT state.")


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CbfController.main) ENABLED START #
    return run((CbfController,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CbfController.main


if __name__ == "__main__":
    main()
