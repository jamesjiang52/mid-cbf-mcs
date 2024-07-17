# -*- coding: utf-8 -*-
#
# This file is part of the FspCorrSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

# """

# """ FspCorrSubarray Tango device prototype

# FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
# """
from __future__ import annotations

import os

import tango
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import FastCommand
from tango.server import attribute, command, device_property, run

from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["FspCorrSubarray", "main"]


class FspCorrSubarray(CbfObsDevice):
    """
    FspCorrSubarray TANGO device class for the FspCorrSubarray prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    HpsFspCorrControllerAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="str",
        doc="Differential off-boresight beam delay model",
    )
    def delayModel(self: FspCorrSubarrayComponentManager) -> str:
        """
        Read the delayModel attribute.

        :return: the delayModel attribute.
        :rtype: string
        """
        return self.component_manager.delay_model

    @attribute(
        dtype=("uint16",),
        max_dim_x=197,
        doc="Assigned VCC IDs",
    )
    def vccIDs(self: FspCorrSubarray) -> list[int]:
        """
        Read the vccIDs attribute; FSP deals with VCC, not DISH (receptor) IDs.

        :return: the list of assigned VCC IDs
        :rtype: list[int]
        """
        return self.component_manager.vcc_ids

    @attribute(
        dtype=tango.DevEnum,
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
        doc="Frequency band; an int in the range [0, 5]",
    )
    def frequencyBand(self: FspCorrSubarray) -> tango.DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band

    @attribute(
        dtype="int",
        doc="Frequency slice ID",
    )
    def frequencySliceID(self: FspCorrSubarray) -> int:
        """
        Read the frequencySliceID attribute.

        :return: the frequencySliceID attribute.
        :rtype: int
        """
        return self.component_manager.frequency_slice_id

    # --------------
    # Initialization
    # --------------

    def init_command_objects(self: FspCorrSubarrayComponentManager) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        self.register_command_object(
            "UpdateDelayModel",
            self.UpdateDelayModelCommand(
                component_manager=self.component_manager, logger=self.logger
            ),
        )

    def create_component_manager(
        self: FspCorrSubarray,
    ) -> FspCorrSubarrayComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        return FspCorrSubarrayComponentManager(
            hps_fsp_corr_controller_fqdn=self.HpsFspCorrControllerAddress,
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
        )

    # -------------
    # Fast Commands
    # -------------

    def is_UpdateDelayModel_allowed(
        self: FspCorrSubarrayComponentManager,
    ) -> bool:
        """
        Determine if UpdateDelayModelis allowed
        (allowed if FSP state is ON and ObsState is
        READY OR SCANNINNG).

        :return: if UpdateDelayModel is allowed
        :rtype: bool
        """
        if self.dev_state() == tango.DevState.ON:
            return True
        return False

    class UpdateDelayModelCommand(FastCommand):
        """
        A class for the Fsp's UpdateDelayModel() command.
        """

        def __init__(
            self: FspCorrSubarrayComponentManager.UpdateDelayModelCommand,
            *args,
            component_manager: FspCorrSubarrayComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.component_manager = component_manager

        def do(
            self: FspCorrSubarrayComponentManager.UpdateDelayModelCommand,
            argin: str,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for UpdateDelayModel() command functionality.

            :param argin: the delay model data
            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            return self.component_manager.update_delay_model(argin)

    @command(
        dtype_in="str",
        dtype_out="DevVarLongStringArray",
        doc_in="Delay Model, per receptor per polarization per timing beam",
    )
    def UpdateDelayModel(
        self: FspCorrSubarrayComponentManager, argin: str
    ) -> DevVarLongStringArrayType:
        """
        Update the FSP's delay model (serialized JSON object)

        :param argin: the delay model data
        """
        command_handler = self.get_command_object("UpdateDelayModel")
        result_code, message = command_handler(argin)
        return [[result_code], [message]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return run((FspCorrSubarray,), args=args, **kwargs)


if __name__ == "__main__":
    main()
