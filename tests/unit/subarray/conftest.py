# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

# Standard imports
from typing import Callable, Type, Dict
import pytest
import unittest

# Tango imports
import tango
from tango import DevState
from tango.server import command

#Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_attribute import MockAttributeBuilder
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.subarray.subarray_device import CbfSubarray
from ska_tango_base.control_model import HealthState, AdminMode, ObsState
from ska_tango_base.commands import ResultCode


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/sub_elt/subarray_01")

@pytest.fixture()
def device_to_load() -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :param patched_vcc_device_class: a class for a patched Vcc
        device with extra methods for testing purposes.

    :return: specification of the device to be loaded
    """
    return {
        "path": "charts/ska-mid-cbf/data/midcbfconfig.json",
        "package": "ska_mid_cbf_mcs",
        "device": "cbfsubarray-01",
        "proxy": CbfDeviceProxy,
        "patch": CbfSubarray,
    }

@pytest.fixture()
def mock_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.add_attribute("receptorToVcc", ["1:1", "2:2", "3:3, 4:4"])
    builder.add_property("MaxCapabilities", {'MaxCapabilities': ['VCC:4', 'FSP:4', 'Subarray:1']})
    return builder()

@pytest.fixture()
def mock_vcc() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_vcc_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def mock_fsp_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("adminMode", AdminMode.ONLINE)
    builder.add_attribute("healthState", HealthState.OK)
    builder.add_attribute("subarrayMembership", 0)
    builder.add_attribute("obsState", ObsState.IDLE)
    builder.add_result_command("On", ResultCode.OK)
    builder.add_result_command("Off", ResultCode.OK)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_controller: unittest.mock.Mock,
    mock_vcc: unittest.mock.Mock,
    mock_vcc_group: unittest.mock.Mock,
    mock_fsp: unittest.mock.Mock,
    mock_fsp_group: unittest.mock.Mock,
    mock_fsp_subarray: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_vcc: a mock Vcc that is powered off.
    :param mock_fsp: a mock VccBand3 that is powered off.
    :param mock_subarray: a mock VccBand4 that is powered off.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/sub_elt/controller": mock_controller,
        "mid_csp_cbf/vcc/001": mock_vcc,
        "mid_csp_cbf/vcc/002": mock_vcc,
        "mid_csp_cbf/vcc/003": mock_vcc,
        "mid_csp_cbf/vcc/004": mock_vcc,
        "mid_csp_cbf/fsp/01": mock_fsp,
        "mid_csp_cbf/fsp/02": mock_fsp,
        "mid_csp_cbf/fsp/03": mock_fsp,
        "mid_csp_cbf/fsp/04": mock_fsp,
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_subarray,
        "VCC": mock_vcc_group,
        "FSP": mock_fsp_group,
    }
