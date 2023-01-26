# -*- coding: utf-8 -*-
#
# This file is part of the Fsp project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""
from __future__ import annotations  # allow forward references in type hints

import tango

__all__ = ["FspCorr"]


class FspCorr:
    """
    FspCorr class used to simulate the behaviour of
    the HPS FSP Corr Controller devices
    when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance
    """

    def __init__(
        self: FspCorr,
        device_name: str,
    ) -> None:
        self.device_name = device_name

        self._state = tango.DevState.INIT

        self._fsp_id = ""
        self._fspUnitID = 0
        self._fqdn = ""
        self._scan_id = "0"

    @property
    def fspID(self) -> str:
        """Return the Fsp ID attribute."""
        return self._fsp_id

    @property
    def fspUnitID(self) -> int:
        """Return the Fsp Unit ID attribute."""
        return self._fsp_unit_id

    @property
    def fqdn(self) -> str:
        """Return the fqdn attribute."""
        return self._fqdn

    # --------
    # Commands
    # --------

    def init_device(self: FspCorr, json_str: str) -> None:
        """
        Initialize the common/constant parameters of this FSP device.

        :param json_str: JSON-formatted string containing the parameters
        """
        pass

    def ConfigureScan(self: FspCorr, json_str: str) -> None:
        """
        Execute a configure scan operation.

        :param json_str: JSON-formatted string containing the scan configuration
                         parameters
        """
        pass

    def Scan(self: FspCorr, scan_id: str) -> None:
        """
        Execute a scan operation.

        :param scan_id: Scan identifier
        """
        self._scan_id = scan_id

    def EndScan(self: FspCorr) -> None:
        """End the scan."""
        self._scan_id = "0"

    def Abort(self: FspCorr) -> None:
        """Abort whatever action is currently executing."""
        pass

    def GoToIdle(self: FspCorr) -> None:
        """Set the device state to IDLE"""
        pass

    def UpdateDelayModels(self: FspCorr, delay_model: str) -> None:
        """
        Execute an update delay model operation.

        :param delay_model: Delay Model
        """
        pass

    def SetState(self, argin):
        """Set state to argin(DevState)."""
        self.set_state(argin)
