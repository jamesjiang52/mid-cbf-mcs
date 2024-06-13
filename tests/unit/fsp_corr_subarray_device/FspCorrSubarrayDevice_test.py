#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspCorrSubarray."""

from __future__ import annotations

# Standard imports
import os
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DevState

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 4


class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray tests.
    """

    def test_State(
        self: TestFspCorrSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestFspCorrSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestFspCorrSubarray, device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        command: str,
    ) -> None:
        """
        Test Power commands.

        :param device_under_test: fixture that provides a
            :py:class:`CbfDeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param command: the name of the Power command to be tested
        """

        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        if command == "On":
            expected_state = DevState.ON
            result = device_under_test.On()
        elif command == "Off":
            expected_state = DevState.OFF
            result = device_under_test.Off()
        elif command == "Standby":
            expected_state = DevState.STANDBY
            result = device_under_test.Standby()

        time.sleep(CONST_WAIT_TIME)
        assert result[0][0] == ResultCode.OK
        assert device_under_test.State() == expected_state

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
        ],
    )
    def test_ConfigureScan(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test the ConfigureScan() command and the triggered ObState transition

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        """
        device_under_test.write_attribute("adminMode", AdminMode.ONLINE)
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.adminMode == AdminMode.ONLINE

        assert device_under_test.State() == DevState.OFF

        device_under_test.On()
        time.sleep(CONST_WAIT_TIME)
        assert device_under_test.State() == DevState.ON

        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        device_under_test.ConfigureScan(json_string)
        time.sleep(0.1)

        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
        ],
    )
    def test_GoToIdle(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test the test_GoToIdle() command and the triggered ObState transition


        First calls the ConfigureScan() command to get it in the ready state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        """

        self.test_ConfigureScan(device_under_test, config_file_name)

        device_under_test.GoToIdle()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 1),
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 2),
        ],
    )
    def test_Scan(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test the Scan() command and the triggered ObState transition

        First calls the ConfigureScan() command to get it in the ready state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        :param scan_id: the scan id
        """

        self.test_ConfigureScan(device_under_test, config_file_name)

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevShort, scan_id)

        device_under_test.Scan(scan_id_device_data)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 1),
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 2),
        ],
    )
    def test_EndScan(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test the EndScan() command and the triggered ObState transition

        First calls the Scan() command to get it in the scanning state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        :param scan_id: the scan id
        """

        self.test_Scan(device_under_test, config_file_name, scan_id)

        device_under_test.EndScan()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.READY

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
        ],
    )
    def test_Abort_FromReady(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test the Abort() command and the triggered ObState transition

        First calls the ConfigureScan() command to get it in the ready state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        """

        self.test_ConfigureScan(device_under_test, config_file_name)

        device_under_test.Abort()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.ABORTED

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id",
        [
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 1),
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 2),
        ],
    )
    def test_Abort_FromScanning(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test the Abort() command and the triggered ObState transition

        First calls the Scan() command to get it in the scanning state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        :param scan_id: the scan id
        """

        self.test_Scan(device_under_test, config_file_name, scan_id)

        device_under_test.Abort()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.ABORTED

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
            "/../../data/FspCorrSubarray_ConfigureScan_basic.json",
        ],
    )
    def test_ObsReset(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
    ) -> None:
        """
        Test the ObsReset() command and the triggered ObState transition

        First calls the Abort() command to get it in the aborted state
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param config_file_name: name of the JSON file that contains the
            configuration
        """

        self.test_Abort_FromReady(device_under_test, config_file_name)

        device_under_test.ObsReset()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE