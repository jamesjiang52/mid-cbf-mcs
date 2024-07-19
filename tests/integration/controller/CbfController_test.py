#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

import json
import os
import socket
from typing import Iterator

import pytest

# Tango imports
from ska_control_model import (
    AdminMode,
    LoggingLevel,
    ObsState,
    ResultCode,
    SimulationMode,
)
from ska_tango_base.base.base_device import (
    _DEBUGGER_PORT,  # DeviceStateModel, removed in v0.11.3
)

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_telmodel.data import TMData
from tango import DevState

data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestCbfController:
    """
    Test class for CbfController device class integration testing.
    """

    def test_Connect(
        self,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        subdevices_under_test: pytest.fixture,
        lru_change_event_callbacks: MockTangoEventCallbackGroup,
        ps_change_event_callbacks: MockTangoEventCallbackGroup,
    ):
        """
        Test the initial states and verify the component manager
        can start communicating
        """
        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        change_event_callbacks["state"].assert_change_event(DevState.OFF)
        ps_change_event_callbacks["state"].assert_change_event(DevState.OFF)
        lru_change_event_callbacks["state"].assert_change_event(DevState.OFF)

        ps_change_event_callbacks.assert_not_called()
        lru_change_event_callbacks.assert_not_called()
        change_event_callbacks.assert_not_called()

    # def test_InitSysParam(self, device_under_test, change_event_callbacks):
    #     """
    #     Test the "InitSysParam" command
    #     """
    #     # Get the system parameters
    #     data_file_path = (
    #         os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
    #     )
    #     with open(data_file_path + "sys_param_4_boards.json") as f:
    #         sp = f.read()

    #     # Initialize the system parameters
    #     result_code, command_id = device_under_test.InitSysParam(sp)
    #     assert result_code == [ResultCode.QUEUED]

    #     change_event_callbacks["longRunningCommandResult"].assert_change_event(
    #         (f"{command_id[0]}", '[0, "InitSysParam completed OK"]')
    #     )
    #     change_event_callbacks.assert_not_called()

    # def test_On(self, device_under_test, subdevices_under_test, change_event_callbacks):
    #     """
    #     Test the "On" command
    #     """
    #     # Send the On command
    #     result_code, command_id = device_under_test.On()
    #     assert result_code == [ResultCode.QUEUED]

    #     change_event_callbacks["longRunningCommandResult"].assert_change_event(
    #         (f"{command_id[0]}", '[0, "On completed OK"]')
    #     )
    #     change_event_callbacks["state"].assert_change_event(DevState.ON)

    #     # Validate subelements are in the correct state
    #     # for i in range(1, subdevices_under_test.num_sub + 1):
    #     #     assert subdevices_under_test.subarray[i].adminMode == AdminMode.ONLINE
    #     # for i in range(1, subdevices_under_test.num_vcc + 1):
    #     #     assert subdevices_under_test.vcc[i].adminMode == AdminMode.ONLINE
    #     # for i in range(1, subdevices_under_test.num_fsp + 1):
    #     #     assert subdevices_under_test.fsp[i].adminMode == AdminMode.ONLINE
    #     # for mesh in subdevices_under_test.slim:
    #     #     assert mesh.adminMode == AdminMode.ONLINE
    #     # for i in ["CORR", "PSS-BF", "PST-BF"]:
    #     #     for j in range(1, subdevices_under_test.num_sub + 1):
    #     #         for k in range(1, subdevices_under_test.num_fsp + 1):
    #     #             assert (
    #     #                 subdevices_under_test.fspSubarray[i][j][k].adminMode
    #     #                 == AdminMode.ONLINE
    #     #             )

    # def test_InitSysParam_Condition(self, subdevices_under_test):
    #     """
    #     Test that InitSysParam can only be used when
    #     the controller op state is OFF
    #     """
    #     if subdevices_under_test.controller.State() == DevState.OFF:
    #         subdevices_under_test.controller.On()
    #     with open(data_file_path + "sys_param_4_boards.json") as f:
    #         sp = f.read()
    #     result = subdevices_under_test.controller.InitSysParam(sp)
    #     assert result[0] == ResultCode.FAILED

    # @pytest.mark.parametrize(
    #     "config_file_name",
    #     [
    #         "source_init_sys_param.json",
    #         "source_init_sys_param_retrieve_from_car.json",
    #     ],
    # )
    # def test_SourceInitSysParam(self, subdevices_under_test, config_file_name: str):
    #     """
    #     Test that InitSysParam file can be retrieved from CAR
    #     """
    #     if subdevices_under_test.controller.State() == DevState.ON:
    #         subdevices_under_test.controller.Off()
    #     with open(data_file_path + config_file_name) as f:
    #         sp = f.read()
    #     result = subdevices_under_test.controller.InitSysParam(sp)

    #     assert subdevices_under_test.controller.State() == DevState.OFF
    #     assert result[0] == ResultCode.OK
    #     assert subdevices_under_test.controller.sourceSysParam == sp
    #     sp_json = json.loads(sp)
    #     tm_data_sources = sp_json["tm_data_sources"][0]
    #     tm_data_filepath = sp_json["tm_data_filepath"]
    #     retrieved_init_sys_param_file = TMData([tm_data_sources])[
    #         tm_data_filepath
    #     ].get_dict()
    #     assert subdevices_under_test.controller.sysParam == json.dumps(
    #         retrieved_init_sys_param_file
    #     )

    # def test_Off(
    #     self, device_under_test, subdevices_under_test, change_event_callbacks
    # ):
    #     """
    #     Test the "Off" command
    #     """

    #     # if controller is already off, we must turn it On before turning off.
    #     if device_under_test.State() == DevState.OFF:
    #         self.test_On(
    #             device_under_test, subdevices_under_test, change_event_callbacks
    #         )

    #     # Send the Off command
    #     result_code, command_id = device_under_test.Off()
    #     assert result_code == [ResultCode.QUEUED]

    #     change_event_callbacks["longRunningCommandResult"].assert_change_event(
    #         (f"{command_id[0]}", '[0, "Off completed OK"]')
    #     )
    #     change_event_callbacks["state"].assert_change_event(DevState.OFF)

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_controller.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Off_GoToIdle_RemoveAllReceptors(
    #     self, subdevices_under_test, config_file_name, receptors, vcc_receptors
    # ):
    #     """
    #     Test the "Off" command resetting the subelement observing state machines.
    #     """

    #     wait_time_s = 5
    #     sleep_time_s = 0.1

    #     # turn system on
    #     self.test_On(subdevices_under_test)

    #     # load scan config
    #     f = open(data_file_path + config_file_name)
    #     json_string = f.read().replace("\n", "")
    #     f.close()
    #     configuration = json.loads(json_string)

    #     sub_id = int(configuration["common"]["subarray_id"])

    #     # Off from IDLE to test RemoveAllReceptors path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    #     # turn system on
    #     self.test_On(subdevices_under_test)

    #     # Off from READY to test GoToIdle path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # configure scan
    #     subdevices_under_test.subarray[sub_id].ConfigureScan(json_string)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.READY,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_controller.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Off_Abort(
    #     self,
    #     subdevices_under_test,
    #     config_file_name,
    #     scan_file_name,
    #     receptors,
    #     vcc_receptors,
    # ):
    #     """
    #     Test the "Off" command resetting the subelement observing state machines.
    #     """
    #     wait_time_s = 5
    #     sleep_time_s = 1

    #     self.test_On(subdevices_under_test)

    #     # load scan config
    #     f = open(data_file_path + config_file_name)
    #     json_string = f.read().replace("\n", "")
    #     f.close()
    #     configuration = json.loads(json_string)
    #     sub_id = int(configuration["common"]["subarray_id"])

    #     # Off from SCANNING to test Abort path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # configure scan
    #     subdevices_under_test.subarray[sub_id].ConfigureScan(json_string)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.READY,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Scan command
    #     f2 = open(data_file_path + scan_file_name)
    #     json_string_scan = f2.read().replace("\n", "")
    #     f2.close()
    #     subdevices_under_test.subarray[sub_id].Scan(json_string_scan)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.SCANNING,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    def test_Disconnect(
        self, device_under_test, change_event_callbacks, subdevices_under_test
    ):
        """
        Verify the component manager can stop communicating
        """
        # Trigger stop_communicating by setting the AdminMode to OFFLINE
        device_under_test.adminMode = AdminMode.OFFLINE
        change_event_callbacks["state"].assert_change_event(DevState.DISABLE)
