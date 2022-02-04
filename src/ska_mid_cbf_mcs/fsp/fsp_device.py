# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# Fsp Tango device prototype
# Fsp TANGO device class for the prototype
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple, Optional

# tango imports
import tango
from tango.server import run
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrWriteType
# Additional import
# PROTECTED REGION ID(Fsp.additionnal_import) ENABLED START #
import os
import sys
import json
from enum import Enum

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_tango_base import SKACapability, SKABaseDevice
from ska_tango_base.commands import ResultCode, BaseCommand
from ska_tango_base.control_model import PowerMode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy
from ska_mid_cbf_mcs.fsp.fsp_component_manager import FspComponentManager
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
# PROTECTED REGION END #    //  Fsp.additionnal_import

__all__ = ["Fsp", "main"]


class Fsp(SKACapability):
    """
    Fsp TANGO device class for the prototype
    """
    # PROTECTED REGION ID(Fsp.class_variable) ENABLED START #

    # PROTECTED REGION END #    //  Fsp.class_variable

    # -----------------
    # Device Properties
    # -----------------

    FspID = device_property(
        dtype='uint16'
    )

    CorrelationAddress = device_property(
        dtype='str'
    )

    PSSAddress = device_property(
        dtype='str'
    )

    PSTAddress = device_property(
        dtype='str'
    )

    VLBIAddress = device_property(
        dtype='str'
    )

    FspCorrSubarray = device_property(
        dtype=('str',)
    )

    FspPssSubarray = device_property(
        dtype=('str',)
    )

    FspPstSubarray = device_property(
        dtype=('str',)
    )

    # ----------
    # Attributes
    # ----------

    functionMode = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Function mode",
        doc="Function mode; an int in the range [0, 4]",
        enum_labels=["IDLE", "CORRELATION", "PSS", "PST", "VLBI", ],
    )

    subarrayMembership = attribute(
        dtype=('uint16',),
        max_dim_x=16,
        access=AttrWriteType.READ,
        label="Subarray membership",
        doc="Subarray membership"
    )

    scanID = attribute(
        dtype='DevLong64',
        label="scanID",
        doc="scan ID, set when transition to SCANNING is performed",
    )

    configID = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Config ID",
        doc="set when transition to READY is performed",
    )

    jonesMatrix = attribute(
        dtype=(('double',),),
        max_dim_x=16,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label='Jones Matrix',
        doc='Jones Matrix, given per frequency slice'
    )

    delayModel = attribute(
        dtype = (('double',),),
        max_dim_x=6,
        max_dim_y=16,
        access=AttrWriteType.READ,
        label='Delay Model',
        doc='Differential off-boresight beam delay model'
    )

    timingBeamWeights = attribute(
        dtype = (('double',),),
        max_dim_x=6,
        max_dim_y=16,
        access=AttrWriteType.READ,
        label='Timing Beam Weights',
        doc='Amplitude weights used in the tied-array beamforming'
    )
   
    # ---------------
    # General methods
    # ---------------

    def init_command_objects(self: Fsp) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object(
            "On", self.OnCommand(*device_args)
        )

        self.register_command_object(
            "Off", self.OffCommand(*device_args)
        )

        self.register_command_object(
            "Standby", self.StandbyCommand(*device_args)
        )

        self.register_command_object(
            "SetFunctionMode", self.SetFunctionModeCommand(*device_args)
        )

        self.register_command_object(
            "AddSubarrayMembership", self.AddSubarrayMembershipCommand(*device_args)
        )

        self.register_command_object(
            "RemoveSubarrayMembership", self.RemoveSubarrayMembershipCommand(*device_args)
        )

        self.register_command_object(
            "UpdateJonesMatrix", self.UpdateJonesMatrixCommand(*device_args)
        )

    def always_executed_hook(self: Fsp) -> None:
        # PROTECTED REGION ID(Fsp.always_executed_hook) ENABLED START #
        """Hook to be executed before any commands."""

        # PROTECTED REGION END #    //  Fsp.always_executed_hook
    
    def create_component_manager(self: Fsp) -> FspComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return FspComponentManager( 
            self.logger,
            self.FspID,
            self.FspCorrSubarray,
            self.FspPssSubarray,
            self.FspPstSubarray,
            self.CorrelationAddress,
            self.PSSAddress,
            self.PSTAddress,
            self.VLBIAddress,
            self.push_change_event,
            self._communication_status_changed,
            self._component_power_mode_changed,
        )

    def delete_device(self: Fsp) -> None:
        # PROTECTED REGION ID(Fsp.delete_device) ENABLED START #
        """Hook to delete device."""
        pass
        # PROTECTED REGION END #    //  Fsp.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_functionMode(self: Fsp) -> tango.DevEnum:
        # PROTECTED REGION ID(Fsp.functionMode_read) ENABLED START #
        """
            Read the functionMode attribute.

            :return: a DevEnum representing the mode.
            :rtype: tango.DevEnum
        """
        return self.component_manager.function_mode
        # PROTECTED REGION END #    //  Fsp.functionMode_read

    def read_subarrayMembership(self: Fsp) -> List[int]:
        # PROTECTED REGION ID(Fsp.subarrayMembership_read) ENABLED START #
        """
            Read the subarrayMembership attribute.

            :return: an array of affiliations of the FSP.
            :rtype: List[int]
        """
        return self.component_manager.subarray_membership
        # PROTECTED REGION END #    //  Fsp.subarrayMembership_read

    def read_scanID(self: Fsp) -> int:
        # PROTECTED REGION ID(FspCorrSubarray.scanID_read) ENABLED START #
        """
            Read the scanID attribute.

            :return: the scanID attribute.
            :rtype: int
        """
        return self._scan_id
        # PROTECTED REGION END #    //  FspCorrSubarray.scanID_read

    def read_configID(self: Fsp) -> str:
        # PROTECTED REGION ID(Fsp.configID_read) ENABLED START #
        """
            Read the configID attribute.

            :return: the configID attribute.
            :rtype: str
        """
        return self._config_id
        # PROTECTED REGION END #    //  Fsp.configID_read

    def write_configID(self: Fsp, value: str) -> None:
        # PROTECTED REGION ID(Fsp.configID_write) ENABLED START #
        """
            Write the configID attribute.

            :param value: the configID value.
        """
        self._config_id=value
        # PROTECTED REGION END #    //  Fsp.configID_write

    def read_jonesMatrix(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.jonesMatrix_read) ENABLED START #
        """
            Read the jonesMatrix attribute.

            :return: the jonesMatrix attribute.
            :rtype: list of list of float
        """
        return self.component_manager.jones_matrix
        # PROTECTED REGION END #    //  Fsp.jonesMatrix_read

    def read_delayModel(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.delayModel_read) ENABLED START #
        """
            Read the delayModel attribute.

            :return: the delayModel attribute.
            :rtype: list of list of float
        """
        return self._delay_model
        # PROTECTED REGION END #    //  Fsp.delayModel_read
    
    def read_timingBeamWeights(self: Fsp) -> List[List[float]]:
        # PROTECTED REGION ID(Fsp.timingBeamWeights_read) ENABLED START #
        """
            Read the timingBeamWeights attribute.

            :return: the timingBeamWeights attribute.
            :rtype: list of list of float
        """
        return self._timing_beam_weights
        # PROTECTED REGION END #    //  Fsp.timingBeamWeights_read

    # --------
    # Commands
    # --------

    class InitCommand(SKACapability.InitCommand):
        """
        A class for the Fsp's init_device() "command".
        """

        def do(
            self: Fsp.InitCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message)=super().do()

            device = self.target

            # initialize FSP proxies
            device._group_fsp_corr_subarray = None
            device._group_fsp_pss_subarray = None
            device._group_fsp_pst_subarray = None
            device._proxy_correlation = None
            device._proxy_pss = None
            device._proxy_pst = None
            device._proxy_vlbi = None
            device._proxy_fsp_corr_subarray = None
            device._proxy_fsp_pss_subarray = None
            device._proxy_fsp_pst_subarray = None

            device._fsp_id = device.FspID

            # initialize attribute values
            device._function_mode = 0  # IDLE
            device._subarray_membership = []
            device._scan_id = 0
            device._config_id = ""
            device._jones_matrix = [[0.0] * 16 for _ in range(4)]
            device._delay_model = [[0.0] * 6 for _ in range(4)]
            device._timing_beam_weights = [[0.0] * 6 for _ in range(4)]

            return (result_code,message)
    
    class OnCommand(SKABaseDevice.OnCommand):
        """
        A class for the Fsp's On() command.
        """

        def do(            
            self: Fsp.OnCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for On() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.on()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.ON)

            return (result_code, message)

    class OffCommand(SKABaseDevice.OffCommand):
        """
        A class for the Fsp's Off() command.
        """
        def do(
            self: Fsp.OffCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Off() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.off()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.OFF)

            return (result_code, message)

    
    class StandbyCommand(SKABaseDevice.StandbyCommand):
        """
        A class for the Fsp's Standby() command.
        """
        def do(            
            self: Fsp.StandbyCommand,
        ) -> Tuple[ResultCode, str]:
            """
            Stateless hook for Standby() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            
            (result_code,message) = self.target.component_manager.standby()

            if result_code == ResultCode.OK:
                self.target._component_power_mode_changed(PowerMode.STANDBY)

            return (result_code, message)
    
    class SetFunctionModeCommand(BaseCommand):
        """
        A class for the Fsp's SetFunctionMode() command.
        """

        def do(
            self: Fsp.SetFunctionModeCommand, 
            argin: str
        ) -> Tuple[ResultCode, str]:  
            """
            Stateless hook for SetFunctionMode() command functionality.

            :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.set_function_mode(argin)
            return (result_code, message)

    @command(
        dtype_in='str',
        doc_in='Function mode'
    )
    def SetFunctionMode(self: Fsp, argin: str) -> None:  
        """
        Set the Fsp Function Mode, either IDLE, CORR, PSS-BF, PST-BF, or VLBI
        If IDLE set the pss, pst, corr and vlbi devicess to DISABLE. OTherwise, 
        turn one of them ON according to argin, and all others DISABLE.

        :param argin: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'
        """
        handler = self.get_command_object("SetFunctionMode")
        return handler(argin)
    
    def is_SetFunctionMode_allowed(
        self: Fsp
        ) -> bool:
        """
        Determine if SetFunctionMode is allowed 
        (allowed if FSP state is ON).

        :return: if SetFunctionMode is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False
    
    class AddSubarrayMembershipCommand(BaseCommand):
        """
        A class for the Fsp's AddSubarrayMembership() command.
        """

        def do(
            self: Fsp.AddSubarrayMembershipCommand, 
            argin: int
        ) -> Tuple[ResultCode, str]:  
            """
            Stateless hook for AddSubarrayMembership() command functionality.

            :param argin: an integer representing the subarray affiliation
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.add_subarray_membership(argin)
            return (result_code, message)
    
    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def AddSubarrayMembership(self: Fsp, argin: str) -> None:  
        """
        Add a subarray to the subarrayMembership list.

        :param argin: an integer representing the subarray affiliation
        """
        handler = self.get_command_object("AddSubarrayMembership")
        return handler(argin)

    def is_AddSubarrayMembership_allowed(self: Fsp) -> bool:
        """
            Determine if AddSubarrayMembership is allowed
            (allowed if FSP state is ON).

            :return: if AddSubarrayMembership is allowed
            :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False
    
    class RemoveSubarrayMembershipCommand(BaseCommand):
        """
        A class for the Fsp's RemoveSubarrayMembership() command.
        """

        def do(
            self: Fsp.RemoveSubarrayMembershipCommand, 
            argin: int
        ) -> Tuple[ResultCode, str]:  
            """
            Stateless hook for RemoveSubarrayMembership() command functionality.

            :param argin: an integer representing the subarray affiliation
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.remove_subarray_membership(argin)
            return (result_code, message)

    @command(
        dtype_in='uint16',
        doc_in='Subarray ID'
    )
    def RemoveSubarrayMembership(self: Fsp, argin: str) -> None:  
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing 
        (no subarray is using this FSP), set function mode to empty.

        :param argin: an integer representing the subarray affiliation
        """
        handler = self.get_command_object("RemoveSubarrayMembership")
        return handler(argin)

    def is_RemoveSubarrayMembership_allowed(self: Fsp) -> bool:
        """
        Determine if RemoveSubarrayMembership is allowed 
        (allowed if FSP state is ON).

        :return: if RemoveSubarrayMembership is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_out='DevString',
        doc_out="returns configID for all the fspCorrSubarray",
    )
    def getConfigID(self: Fsp) -> str:
        # PROTECTED REGION ID(Fsp.getConfigID) ENABLED START #
        """
            Get the configID for all the fspCorrSubarray

            :return: the configID
            :rtype: str
        """
        result ={}
        for proxy in self._proxy_fsp_corr_subarray:
            result[str(proxy)]=proxy.configID
        return str(result)
        # PROTECTED REGION END #    //  Fsp.getConfigID
    
    class UpdateJonesMatrixCommand(BaseCommand):
        """
        A class for the Fsp's UpdateJonesMatrix() command.
        """

        def do(
            self: Fsp.UpdateJonesMatrixCommand, 
            argin: str
        ) -> Tuple[ResultCode, str]:  
            """
            Stateless hook for UpdateJonesMatrix() command functionality.

            :param argin: the jones matrix data
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code,message) = self.target.component_manager.update_jones_matrix(argin)
            return (result_code, message)
    
    @command(
        dtype_in='str',
        doc_in="Jones Matrix, given per frequency slice"
    )
    def UpdateJonesMatrix(self: Fsp, argin: str) -> None:  
        """
        Update the FSP's jones matrix (serialized JSON object)

        :param argin: the jones matrix data
        """
        handler = self.get_command_object("UpdateJonesMatrix")
        return handler(argin)

    def is_UpdateJonesMatrix_allowed(self: Fsp) -> bool:
        """
        Determine if UpdateJonesMatrix is allowed 
        (allowed if FSP state is ON and ObsState is 
        READY OR SCANNINNG).

        :return: if UpdateJonesMatrix is allowed
        :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    # @command(
    #     dtype_in='str',
    #     doc_in="Jones Matrix, given per frequency slice"
    # )
    # def UpdateJonesMatrix(
    #     self: Fsp, 
    #     argin: str,
    #     ) -> None:
    #     # PROTECTED REGION ID(Fsp.UpdateJonesMatrix) ENABLED START #
    #     """
    #         Update the FSP's jones matrix (serialized JSON object)

    #         :param argin: the jones matrix data
    #     """
    #     self.logger.debug("Fsp.UpdateJonesMatrix")

    #     #TODO: this enum should be defined once and referred to throughout the project
    #     FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
    #     if self._function_mode in [FspModes.PSS_BF.value, FspModes.PST_BF.value, FspModes.VLBI.value]:
    #         argin = json.loads(argin)

    #         for i in self._subarray_membership:
    #             if self._function_mode == FspModes.PSS_BF.value:
    #                 proxy = self._proxy_fsp_pss_subarray[i - 1]
    #                 fs_length = 16
    #             elif self._function_mode == FspModes.PST_BF.value:
    #                 proxy = self._proxy_fsp_pst_subarray[i - 1]
    #                 fs_length = 4
    #             else:
    #                 fs_length = 4
    #                 # TODO: support for function mode VLBI
    #                 log_msg = "function mode {} currently not supported".format(self._function_mode)
    #                 self.logger.error(log_msg)
    #                 return

    #             for receptor in argin:
    #                 rec_id = int(receptor["receptor"])
    #                 if rec_id in proxy.receptors:
    #                     for frequency_slice in receptor["receptorMatrix"]:
    #                         fs_id = frequency_slice["fsid"]
    #                         matrix = frequency_slice["matrix"]
    #                         if fs_id == self._fsp_id:
    #                             if len(matrix) == fs_length:
    #                                 self._jones_matrix[rec_id - 1] = matrix.copy()
    #                             else:
    #                                 log_msg = "'matrix' not valid length for frequency slice {} of " \
    #                                         "receptor {}".format(fs_id, rec_id)
    #                                 self.logger.error(log_msg)
    #                         else:
    #                             log_msg = "'fsid' {} not valid for receptor {}".format(
    #                                 fs_id, rec_id
    #                             )
    #                             self.logger.error(log_msg)
    #     else:
    #         log_msg = "matrix not used in function mode {}".format(self._function_mode)
    #         self.logger.error(log_msg)
    #     # PROTECTED REGION END #    // Fsp.UpdateJonesMatrix

    def is_UpdateDelayModel_allowed(self: Fsp) -> bool:
        """
            Determine if UpdateDelayModelis allowed 
            (allowed if FSP state is ON and ObsState is 
            READY OR SCANNINNG).

            :return: if UpdateDelayModel is allowed
            :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay Model, per receptor per polarization per timing beam"
    )
    def UpdateDelayModel(
        self: Fsp, 
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.UpdateDelayModel) ENABLED START #
        """
            Update the FSP's delay model (serialized JSON object)

            :param argin: the delay model data
        """
        self.logger.debug("Fsp.UpdateDelayModel")

        # update if current function mode is either PSS-BF or PST-BF
        if self._function_mode in [2, 3]:
            argin = json.loads(argin)
            for i in self._subarray_membership:
                if self._function_mode == 2:
                    proxy = self._proxy_fsp_pss_subarray[i - 1]
                else:
                    proxy = self._proxy_fsp_pst_subarray[i - 1]
                for receptor in argin:
                    rec_id = int(receptor["receptor"])
                    if rec_id in proxy.receptors:
                        for frequency_slice in receptor["receptorDelayDetails"]:
                            fs_id = frequency_slice["fsid"]
                            model = frequency_slice["delayCoeff"]
                            if fs_id == self._fsp_id:
                                if len(model) == 6:
                                    self._delay_model[rec_id - 1] = model.copy()
                                else:
                                    log_msg = "'model' not valid length for frequency slice {} of " \
                                            "receptor {}".format(fs_id, rec_id)
                                    self.logger.error(log_msg)
                            else:
                                log_msg = "'fsid' {} not valid for receptor {}".format(
                                    fs_id, rec_id
                                )
                                self.logger.error(log_msg)
        else:
            log_msg = "model not used in function mode {}".format(self._function_mode)
            self.logger.error(log_msg)
        # PROTECTED REGION END #    // Fsp.UpdateDelayModel

    def is_UpdateTimingBeamWeights_allowed(self: Fsp) -> bool:
        """
            Determine if UpdateTimingBeamWeights is allowed 
            (allowed if FSP state is ON and ObsState is 
            READY OR SCANNINNG).

            :return: if UpdateTimingBeamWeights is allowed
            :rtype: bool
        """
        #TODO implement obsstate in FSP
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Timing Beam Weights, per beam per receptor per group of 8 channels"
    )
    def UpdateBeamWeights(
        self: Fsp, 
        argin: str,
        ) -> None:
        # PROTECTED REGION ID(Fsp.UpdateTimingBeamWeights) ENABLED START #
        """
            Update the FSP's timing beam weights (serialized JSON object)

            :param argin: the timing beam weight data
        """
        self.logger.debug("Fsp.UpdateBeamWeights")

        # update if current function mode is PST-BF
        if self._function_mode == 3:
            argin = json.loads(argin)
            for i in self._subarray_membership:
                proxy = self._proxy_fsp_pst_subarray[i - 1]
                for receptor in argin:
                    rec_id = int(receptor["receptor"])
                    if rec_id in proxy.receptors:
                        for frequency_slice in receptor["receptorWeightsDetails"]:
                            fs_id = frequency_slice["fsid"]
                            weights = frequency_slice["weights"]
                            if fs_id == self._fsp_id:
                                if len(weights) == 6:
                                    self._timing_beam_weights[rec_id - 1] = weights.copy()
                                else:
                                    log_msg = "'weights' not valid length for frequency slice {} of " \
                                            "receptor {}".format(fs_id, rec_id)
                                    self.logger.error(log_msg)
                            else:
                                log_msg = "'fsid' {} not valid for receptor {}".format(
                                    fs_id, rec_id
                                )
                                self.logger.error(log_msg)
        else:
            log_msg = "weights not used in function mode {}".format(self._function_mode)
            self.logger.error(log_msg)
        # PROTECTED REGION END #    // Fsp.UpdateTimingBeamWeights
    
    # ----------
    # Callbacks
    # ----------
    def _communication_status_changed(
        self: Fsp,
        communication_status: CommunicationStatus,
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
        elif communication_status == CommunicationStatus.ESTABLISHED \
            and self._component_power_mode is not None:
            self._component_power_mode_changed(self._component_power_mode)
        else:  # self._component_power_mode is None
            pass  # wait for a power mode update
    
    def _component_power_mode_changed(
        self: Fsp,
        power_mode: PowerMode,
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

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(Fsp.main) ENABLED START #
    return run((Fsp,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Fsp.main

if __name__ == '__main__':
    main()