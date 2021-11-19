#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Vcc."""

from __future__ import annotations

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestVcc:
    """
    Test class for Vcc tests.
    """

    @pytest.mark.parametrize(
        "config_file_name",
        [
            (
                "/../../data/Vcc_ConfigureScan_basic.json"
            )
        ]
    )    
    def test_Vcc_ConfigureScan_basic(
        self,
        device_under_test: CbfDeviceProxy,
        config_file_name: str
    ) -> None:
        """
            Test a minimal successful scan configuration.

            :param device_under_test: fixture that provides a
                :py:class:`tango.DeviceProxy` to the device under test, in a
                :py:class:`tango.test_context.DeviceTestContext`.
            :param config_file_name: JSON file for the configuration 
        """

        # to get the mock devices, use tango_harness.get_device("fqdn")

        device_under_test.On()
        time.sleep(1)
        assert device_under_test.State() == DevState.ON
        
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        frequency_band = configuration["frequency_band"]
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        freq_band_name =  frequency_bands[frequency_band]
        device_under_test.TurnOnBandDevice(freq_band_name)

        device_under_test.ConfigureScan(json_str)
        time.sleep(3)

        assert device_under_test.obsState == ObsState.READY
        assert device_under_test.configID == configuration["config_id"]
        assert device_under_test.frequencyBand == configuration["frequency_band"]
        assert device_under_test.rfiFlaggingMask == str(configuration["rfi_flagging_mask"])
        if "band_5_tuning" in configuration:
                if device_under_test.frequencyBand in [4, 5]:
                    band5Tuning_config = configuration["band_5_tuning"]
                    for i in range(0, len(band5Tuning_config)):
                        assert device_under_test.band5Tuning[i] == band5Tuning_config[i]
        if "frequency_band_offset_stream_1" in configuration:
            assert  device_under_test.frequencyBandOffsetStream1 == configuration["frequency_band_offset_stream_1"]
        if "frequency_band_offset_stream_2" in configuration:
            assert  device_under_test.frequencyBandOffsetStream2 == configuration["frequency_band_offset_stream_2"] 
        assert device_under_test.scfoBand1 == configuration["scfo_band_1"]
        assert device_under_test.scfoBand2 == configuration["scfo_band_2"]
        assert device_under_test.scfoBand3 == configuration["scfo_band_3"]
        assert device_under_test.scfoBand4 == configuration["scfo_band_4"]
        assert device_under_test.scfoBand5a == configuration["scfo_band_5a"]
        assert device_under_test.scfoBand5b == configuration["scfo_band_5b"]

        device_under_test.TurnOffBandDevice(freq_band_name)

    

    def test_On_Off(
        self: TestVcc,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
            Test for Vcc's On and Off commands

            :param device_under_test: fixture that provides a
                :py:class:`tango.DeviceProxy` to the device under test, in a
                :py:class:`tango.test_context.DeviceTestContext`.
        """
        
        device_under_test.On()
        time.sleep(1)
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()
        time.sleep(1)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "config_file_name, \
        scan_id", 
        [
            (
                "/../../data/Vcc_ConfigureScan_basic.json",
                1,
            ),
                        (
                "/../../data/Vcc_ConfigureScan_basic.json",
                2,
            )
        ]
    )
    def test_Scan_EndScan_GoToIdle(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        scan_id: int
    ) -> None:
        """
            Test Vcc's Scan command state changes.

            :param device_under_test: fixture that provides a
                :py:class:`tango.DeviceProxy` to the device under test, in a
                :py:class:`tango.test_context.DeviceTestContext`.
            :param config_file_name: JSON file for the configuration
            :param scan_id: the scan id
        """

        # turn on device and configure scan
        device_under_test.On()
        f = open(file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        device_under_test.ConfigureScan(json_string)
        time.sleep(3)

        scan_id_device_data = tango.DeviceData()
        scan_id_device_data.insert(tango.DevString, str(scan_id))

        # Use callable 'Scan'  API
        device_under_test.Scan(scan_id_device_data)
        time.sleep(0.1)
        assert device_under_test.scanID == scan_id
        assert device_under_test.obsState == ObsState.SCANNING


        device_under_test.EndScan()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.READY

        device_under_test.GoToIdle()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.IDLE


    #TODO refactor and enable this test, move to search window test module
    @pytest.mark.skip
    def test_ConfigureSearchWindow_basic(
        self,
        tango_context
    ):
        """
            Test a minimal successful search window configuration.
        """
        if tango_context is None:
            dev_factory = DevFactory()
            logging.info("%s", dev_factory._test_context)
            vcc_proxy = dev_factory.get_device("mid_csp_cbf/vcc/001")
            sw_1_proxy = dev_factory.get_device("mid_csp_cbf/vcc_sw1/001")
            sw_1_proxy.Init()

            # check initial values of attributes
            assert sw_1_proxy.searchWindowTuning == 0
            assert sw_1_proxy.tdcEnable == False
            assert sw_1_proxy.tdcNumBits == 0
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 0
            assert sw_1_proxy.tdcPeriodAfterEpoch == 0
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check initial state
            assert sw_1_proxy.State() == DevState.DISABLE

            # set receptorID to 1 to correctly test tdcDestinationAddress
            vcc_proxy.receptorID = 1

        
            # configure search window
            f = open(file_path + "/../data/test_ConfigureSearchWindow_basic.json")
            vcc_proxy.ConfigureSearchWindow(f.read().replace("\n", ""))
            f.close()

            # check configured values
            assert sw_1_proxy.searchWindowTuning == 1000000000
            assert sw_1_proxy.tdcEnable == True
            assert sw_1_proxy.tdcNumBits == 8
            assert sw_1_proxy.tdcPeriodBeforeEpoch == 5
            assert sw_1_proxy.tdcPeriodAfterEpoch == 25
            assert sw_1_proxy.tdcDestinationAddress == ("", "", "")

            # check state
            assert sw_1_proxy.State() == DevState.ON
    
    @pytest.mark.parametrize(
        "config_file_name, \
        delay_model_file_name", 
        [
            (
                "/../../data/Vcc_ConfigureScan_basic.json",
                "/../../data/delaymodel_vcc_unit_test.json"
            )
        ]
    )
    def test_UpdateDelayModel(
        self: TestVcc,
        device_under_test: CbfDeviceProxy,
        config_file_name: str,
        delay_model_file_name: str
    ) -> None:
        """
            Test Vcc's UpdateDelayModel Command.

            :param device_under_test: fixture that provides a
                :py:class:`tango.DeviceProxy` to the device under test, in a
                :py:class:`tango.test_context.DeviceTestContext`.
            :param config_file_name: JSON file for the configuration
            :param delay_model_file_name: JSON file for the delay model
        """

        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(5)
        assert device_under_test.State() == DevState.ON

        # delay model values should be set to 0.0 after init
        num_cols = 6
        num_rows = 26
        assert device_under_test.read_attribute("delayModel", \
             extract_as=tango.ExtractAs.List).value == [[0] * num_cols for i in range(num_rows)]
        
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        configuration = json.loads(json_str)
        f.close()

        frequency_band = configuration["frequency_band"]
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        freq_band_name =  frequency_bands[frequency_band]
        device_under_test.TurnOnBandDevice(freq_band_name)

        device_under_test.ConfigureScan(json_str)

        assert device_under_test.obsState == ObsState.READY
        
        # read the json file
        f = open(file_path + delay_model_file_name)
        json_str_model = f.read().replace("\n", "")
        f.close()
        delay_model = json.loads(json_str_model)

        # update the delay model
        for m in delay_model["delayModel"]:
            device_under_test.write_attribute("receptorID", m["delayDetails"][0]["receptor"])
            assert device_under_test.receptorID == m["delayDetails"][0]["receptor"]
            device_under_test.UpdateDelayModel(json.dumps(m["delayDetails"]))
        
        for m in delay_model["delayModel"]:
            for delayDetails in m["delayDetails"]:
                for frequency_slice in delayDetails["receptorDelayDetails"]:
                    if 1 <= frequency_slice["fsid"] <= num_rows:
                        if len(frequency_slice["delayCoeff"]) == num_cols:
                            assert device_under_test.read_attribute("delayModel", \
                            extract_as=tango.ExtractAs.List).value[frequency_slice["fsid"] -1] \
                                 == frequency_slice["delayCoeff"] 
                        else:
                            log_msg = "'delayCoeff' not valid for frequency slice {} of " \
                                        "receptor {}".format(frequency_slice["fsid"], self._receptor_ID)
                            logging.error(log_msg)
                    else:
                        log_msg = "'fsid' {} not valid for receptor {}".format(
                            frequency_slice["fsid"], self._receptor_ID
                        )
                        logging.error(log_msg)