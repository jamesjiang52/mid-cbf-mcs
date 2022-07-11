# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.
#
# Copyright (c) 2019 National Research Council of Canada
#
# """
# VccBandSimulator Class
#
# This class is used to simulate the behaviour of the HPS VCC band
# devices when the Talon-DX hardware is not connected.
# 
# Currently this is just provided as a single class, but there may
# be a need to add functionality for different bands at a later time.
# In that case, this may be used as a base class with an additional class
# created for each band that inherit from it.
# """

from __future__ import annotations # allow forward references in type hints

import json
import tango
from typing import List

from ska_tango_base.control_model import ObsState
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict

__all__ = ["VccBandSimulator"]

class VccBandSimulator:
    """
    VccBandSimulator class used to simulate the behaviour of the HPS VCC band
    devices when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance
    """
    def __init__(self: VccBandSimulator, device_name: str) -> None:
        self.device_name = device_name

        self._state = tango.DevState.INIT
        self._obs_state = ObsState.IDLE

        self._frequency_offset_k = 0
        self._frequency_offset_delta_f = 0
        self._vcc_gain = []

        self._config_id = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset = [0, 0]
        self._rfi_flagging_mask = ""

        self._scan_id = 0

    # Properties that match the Tango attributes in the band devices
    @property
    def obsState(self) -> List[float]:
        """Return the Obs state attribute."""
        return self._obs_state

    @property
    def frequencyOffsetK(self) -> List[float]:
        """Return the frequency offset K attribute."""
        return self._frequency_offset_k

    @property
    def frequencyOffsetDeltaF(self) -> List[float]:
        """Return the frequency offset delta_f attribute."""
        return self._frequency_offset_delta_f

    @property
    def vccGain(self) -> List[float]:
        """Return the VCC gain attribute."""
        return self._vcc_gain

    @property
    def configID(self) -> str:
        """Return the config ID attribute."""
        return self._config_id

    @property
    def frequencyBand(self) -> int:
        """Return the frequency band attribute."""
        return self._frequency_band

    @property
    def frequencyBandOffset(self) -> List[int]:
        """Return the frequency band offset attribute."""
        return self._frequency_band_offset

    @property
    def scanID(self) -> int:
        """Return the scan ID attribute."""
        return self._scan_id

    # Methods that match the Tango commands in the band devices
    def On(self: VccBandSimulator) -> None:
        """Set the device to the ON state"""
        self._state = tango.DevState.ON

    def Disable(self: VccBandSimulator) -> None:
        """Set the device to the DISABLE state"""
        self._state = tango.DevState.DISABLE

    def State(self: VccBandSimulator) -> tango.DevState:
        """Get the current state of the device"""
        return self._state

    def InitCommonParameters(self: VccBandSimulator, json_str: str) -> None:
        """
        Initialize the common/constant parameters of this VCC device. These
        parameters hold the same value across all bands for one receptor, and
        do not change during scan configuration.

        :param json_str: JSON-formatted string containing the parameters
        """
        params = json.loads(json_str)
        self._frequency_offset_k  = params["frequency_offset_k"]
        self._frequency_offset_delta_f = params["frequency_offset_delta_f"]
        self._state = tango.DevState.DISABLE

    def SetInternalParameters(self: VccBandSimulator, json_str: str) -> None:
        """
        Set the internal parameters of this VCC device. These parameters are
        unique per receptor per band. Currently the parameters just consist
        of the VCC gain values.

        :param json_str: JSON-formatted string containing the parameters
        """
        internal_params = json.loads(json_str)
        self._vcc_gain  = internal_params["vcc_gain"]

    def ConfigureScan(self: VccBandSimulator, json_str: str) -> None:
        """
        Execute a configure scan operation.

        :param json_str: JSON-formatted string containing the scan configuration
                         parameters
        """
        self._obs_state = ObsState.CONFIGURING

        configuration = json.loads(json_str)

        self._config_id = configuration["config_id"]

        self._frequency_band = freq_band_dict()[configuration["frequency_band"]]

        # If band is 5a or 5b, store band 5 turning parameter
        if self._frequency_band in [4, 5]:
            self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset = [
            int(configuration["frequency_band_offset_stream_1"]),
            int(configuration["frequency_band_offset_stream_2"])
        ]
        
        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = str(configuration["rfi_flagging_mask"])

        self._obs_state = ObsState.READY

    def Scan(self: VccBandSimulator, scan_id: int) -> None:
        """
        Execute a scan operation.

        :param scan_id: Scan identifier
        """
        self._scan_id = scan_id
        self._obs_state = ObsState.SCANNING

    def EndScan(self: VccBandSimulator) -> None:
        """End the scan."""
        self._obs_state = ObsState.READY

    def Abort(self: VccBandSimulator) -> None:
        """Abort whatever action is currently executing."""
        self._obs_state = ObsState.ABORTED

    def ObsReset(self: VccBandSimulator) -> None:
        """Reset the observing state."""
        self._obs_state = ObsState.RESETTING
        self.Unconfigure()

    def Unconfigure(self: VccBandSimulator) -> None:
        """Reset the configuration."""
        self._config_id = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset = [0, 0]
        self._rfi_flagging_mask = ""

        self._scan_id = 0

        self._obs_state = ObsState.IDLE