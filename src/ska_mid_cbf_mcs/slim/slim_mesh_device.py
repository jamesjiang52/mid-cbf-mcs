# -*- coding: utf-8 -*-
#
#
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
TANGO device class for controlling and monitoring the
Serial Lightweight Interconnect Mesh (SLIM)
"""

from __future__ import annotations

from typing import List, Optional, Tuple

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResponseCommand, ResultCode
from ska_tango_base.control_model import PowerMode, SimulationMode
from tango import AttrWriteType
from tango.server import attribute, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.mesh_component_manager import MeshComponentManager
from ska_mid_cbf_mcs.slim.slim_common import SLIMConst

__all__ = ["SLIMMesh", "main"]


class SLIMMesh(SKABaseDevice):
    """
    TANGO device class for controlling and monitoring the SLIM mesh
    """

    # PROTECTED REGION ID(SLIMMesh.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  SLIMMesh.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=str,
        label="Mesh configuration",
        doc="Mesh configuration in a YAML string. This is the string provided in Configure. Returns empty string if not already configured",
    )
    def MeshConfiguration(self: SLIMMesh) -> str:
        """
        Read the FPGA bitstream version of the Talon-DX board.

        :return: the FPGA bitstream version
        """
        res = self.component_manager.get_configuration_string()
        return res

    @attribute(
        dtype=(bool,),
        max_dim_x=SLIMConst.MAX_NUM_LINKS,
        label="Mesh status summary",
        doc="Returns a list of status of each link. True if OK. False if the link is in a bad state.",
    )
    def MeshStatusSummary(self: SLIMMesh) -> List[bool]:
        """
        Returns a list of status of each link. True if OK. False if the link is in a bad state.

        :return: a list of link status
        """
        res = self.component_manager.get_status_summary()
        return res

    @attribute(
        dtype=(float,),
        max_dim_x=SLIMConst.MAX_NUM_LINKS,
        label="Bit error rate",
        doc="Returns the bit error rate of each link in a list",
    )
    def BitErrorRate(self: SLIMMesh) -> List[float]:
        """
        Returns the bit error rate of each link in a list

        :return: the bit error rate as a list of float
        """
        res = self.component_manager.get_bit_error_rate()
        return res

    simulationMode = attribute(
        dtype=SimulationMode,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc="Reports the simulation mode of the device. \nSome devices may implement "
        "both modes, while others will have simulators that set simulationMode "
        "to True while the real devices always set simulationMode to False.",
    )

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: SLIMMesh) -> None:
        # PROTECTED REGION ID(SLIMMesh.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SLIMMesh.always_executed_hook

    def delete_device(self: SLIMMesh) -> None:
        # PROTECTED REGION ID(SLIMMesh.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  SLIMMesh.delete_device

    def init_command_objects(self: SLIMMesh) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self.component_manager, self.logger)

        self.register_command_object(
            "Configure", self.ConfigureCommand(*device_args)
        )

    # --------
    # Commands
    # --------

    def create_component_manager(self: SLIMMesh) -> MeshComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        # Simulation mode default true
        return MeshComponentManager(
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
        )

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the init_device() "command".
        """

        def do(self: SLIMMesh.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            (result_code, message) = super().do()

            device = self.target
            device.write_simulationMode(True)

            return (result_code, message)

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.
        """

        def do(self: SLIMMesh.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.on()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.
        """

        def do(self: SLIMMesh.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.off()

    class ConfigureCommand(ResponseCommand):
        """
        The command class for the Configure command.
        """

        def do(
            self: SLIMMesh.ConfigureCommand, argin: str
        ) -> Tuple[ResultCode, str]:
            """
            Configure command. Configures the SLIM mesh as provided in the input string.

            :param argin: mesh configuration as a string in YAML format
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            self.logger.info("Entering SLIMMesh.ConfigureCommand")
            (result_code, message) = self.target.component_manager.configure(
                argin
            )
            if result_code == ResultCode.OK:
                self.logger.info("Mesh Configure completed successfully")
            elif result_code == ResultCode.FAILED:
                self.logger.error(message)

            return (result_code, message)


    # ---------
    # Callbacks
    # ---------

    def _communication_status_changed(
        self: SLIMMesh, communication_status: CommunicationStatus
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
        elif (
            communication_status == CommunicationStatus.ESTABLISHED
            and self._component_power_mode is not None
        ):
            self._component_power_mode_changed(self._component_power_mode)
        else:  # self._component_power_mode is None
            pass  # wait for a power mode update

    def _component_power_mode_changed(
        self: SLIMMesh, power_mode: PowerMode
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

    def _component_fault(self: SLIMMesh, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")

    # ------------------
    # Attributes methods
    # ------------------

    def write_simulationMode(self: SLIMMesh, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device. When simulation mode is set to
        True, the power switch software simulator is used in place of the hardware.
        When simulation mode is set to False, the real power switch driver is used.

        :param value: SimulationMode
        """
        self.logger.info(f"Writing simulationMode to {value}")
        super().write_simulationMode(value)
        self.component_manager.simulation_mode = value


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(SLIMMesh.main) ENABLED START #
    return run((SLIMMesh,), args=args, **kwargs)
    # PROTECTED REGION END #    //  SLIMMesh.main


if __name__ == "__main__":
    main()
