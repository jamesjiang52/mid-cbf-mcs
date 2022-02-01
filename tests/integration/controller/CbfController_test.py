#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

# Standard imports
import sys
import os
import time

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports

from ska_tango_base.base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode, ControlMode, HealthState, LoggingLevel, SimulationMode, TestMode
)
from ska_tango_base.base.base_device import (
    _DEBUGGER_PORT,
    _Log4TangoLoggingLevel,
    _PYTHON_TO_TANGO_LOGGING_LEVEL,
    LoggingUtils,
    LoggingTargetError,
    # DeviceStateModel, removed in v0.11.3
    TangoLoggingServiceHandler,
)
from ska_tango_base.faults import CommandError
import socket
from tango.test_context import DeviceTestContext


@pytest.mark.usefixtures("test_proxies")

class TestCbfController:
    """
    Test class for CbfController device class integration testing.
    """

    @pytest.mark.skip(reason="enable to test DebugDevice")
    def test_DebugDevice(self, test_proxies):
        port = test_proxies.controller.DebugDevice()
        assert port == _DEBUGGER_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", _DEBUGGER_PORT))
        test_proxies.controller.On()
    
    def test_Connect(self, test_proxies):
        """
        Test the initial states and verify the component manager 
        can start communicating
        """
        
        # after init devices should be in DISABLE state
        assert test_proxies.controller.State() == DevState.DISABLE
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.DISABLE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.DISABLE

        # trigger start_communicating by setting the AdminMode to ONLINE
        test_proxies.controller.adminMode = AdminMode.ONLINE

        # controller device should be in OFF state after start_communicating 
        test_proxies.wait_timeout_dev([test_proxies.controller], DevState.OFF, 3, 0.1)
        assert test_proxies.controller.State() == DevState.OFF

    @pytest.mark.skip(reason="controller subordinate devices need to be \
        updated to v0.11.3")
    def test_On(self, test_proxies):
        """
        Test the "On" command
        """
        
        # send the On command
        test_proxies.controller.On()

        test_proxies.wait_timeout_dev([test_proxies.controller], DevState.ON, 3, 0.1)
        assert test_proxies.controller.State() == DevState.ON

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev([test_proxies.subarray[i]], DevState.ON, 3, 0.1)
            assert test_proxies.subarray[i].State() == DevState.ON

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.ON

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.ON
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.ON
    
    @pytest.mark.skip(reason="controller subordinate devices need to be \
        updated to v0.11.3")    
    def test_Off(self, test_proxies):
        """
        Test the "Off" command
        """

        # send the Off command
        test_proxies.controller.Off()

        test_proxies.wait_timeout_dev([test_proxies.controller], DevState.OFF, 3, 0.1)
        assert test_proxies.controller.State() == DevState.OFF

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev([test_proxies.subarray[i]], DevState.OFF, 3, 0.1)
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.OFF
    
    @pytest.mark.skip(reason="controller subordinate devices need to be \
        updated to v0.11.3")  
    def test_Standby(self, test_proxies):
        """
        Test the "Standby" command
        """
        # send the Standby command
        test_proxies.controller.Standby()

        test_proxies.wait_timeout_dev([test_proxies.controller], DevState.STANDBY, 3, 0.1)
        assert test_proxies.controller.State() == DevState.STANDBY

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev([test_proxies.subarray[i]], DevState.OFF, 3, 0.1)
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert test_proxies.fspSubarray[i][j][k].State() == DevState.OFF

    def test_Disconnect(self, test_proxies):
        """
        Verify the component manager can stop communicating
        """

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.controller.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating  
        test_proxies.wait_timeout_dev([test_proxies.controller], DevState.DISABLE, 3, 0.1)
        assert test_proxies.controller.State() == DevState.DISABLE

    #TODO implement these tests properly?
    # def test_reportVCCSubarrayMembership(
    #         self,
    #         cbf_master_proxy,
    #         subarray_1_proxy,
    #         subarray_2_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC subarray membership subscriptions
    # """

    # def test_reportVCCState(
    #         self,
    #         cbf_master_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC state subscriptions
    # """
       
    # def test_reportVCCHealthState(
    #         self,
    #         cbf_master_proxy,
    #         vcc_test_proxies
    # ):
    # """
    #     Test the VCC state subscriptions
    # """
