# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

# Standard imports
from typing import Callable, Type, Dict, Optional
import pytest
import unittest
import pytest_mock

# Tango imports
import tango
from tango import DevState
from tango.server import command

#Local imports
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockChangeEventCallback
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder
from ska_mid_cbf_mcs.testing.mock.mock_group import MockGroupBuilder
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType, TangoHarness

from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_tango_base.control_model import HealthState, AdminMode, ObsState, PowerMode
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus


@pytest.fixture()
def device_under_test(tango_harness: TangoHarness) -> CbfDeviceProxy:
    """
    Fixture that returns the device under test.

    :param tango_harness: a test harness for Tango devices

    :return: the device under test
    """
    return tango_harness.get_device("mid_csp_cbf/fsp/01")

@pytest.fixture()
def device_to_load(
    patched_fsp_device_class: Type[Fsp]
) -> DeviceToLoadType:
    """
    Fixture that specifies the device to be loaded for testing.

    :return: specification of the device to be loaded
    """
    return {
        "path": "tests/unit/fsp/devicetoload.json",
        "package": "ska_mid_cbf_mcs.fsp.fsp_device",
        "device": "fsp-01",
        "device_class": "Fsp",
        "proxy": CbfDeviceProxy,
        "patch": patched_fsp_device_class,
    }

@pytest.fixture
def unique_id() -> str:
    """
    Return a unique ID used to test Tango layer infrastructure.

    :return: a unique ID
    """
    return "a unique id"


@pytest.fixture()
def mock_component_manager(
    mocker: pytest_mock.mocker,
    unique_id: str,
) -> unittest.mock.Mock:
    """
    Return a mock component manager.

    The mock component manager is a simple mock except for one bit of
    extra functionality: when we call start_communicating() on it, it
    makes calls to callbacks signaling that communication is established
    and the component is off.

    :param mocker: pytest wrapper for unittest.mock
    :param unique_id: a unique id used to check Tango layer functionality

    :return: a mock component manager
    """
    mock = mocker.Mock()
    mock.is_communicating = False

    def _start_communicating(mock: unittest.mock.Mock) -> None:
        mock.is_communicating = True
        mock._communication_status_changed_callback(CommunicationStatus.NOT_ESTABLISHED)
        mock._communication_status_changed_callback(CommunicationStatus.ESTABLISHED)
        mock._component_power_mode_changed_callback(PowerMode.OFF)
    
    def _on(mock: unittest.mock.Mock) -> None:
        mock.message = "Fsp On command completed OK"
        return (ResultCode.OK, mock.message)
    
    def _off(mock: unittest.mock.Mock) -> None:
        mock.message = "Fsp Off command completed OK"
        return (ResultCode.OK, mock.message)
    
    def _standby(mock: unittest.mock.Mock) -> None:
        mock.message = "Fsp Standby command completed OK"
        return (ResultCode.OK, mock.message)
    
    mock.start_communicating.side_effect = lambda: _start_communicating(mock)
    mock.on.side_effect = lambda: _on(mock)
    mock.off.side_effect = lambda: _off(mock)
    mock.standby.side_effect = lambda: _standby(mock)

    mock.enqueue.return_value = unique_id, ResultCode.QUEUED

    return mock

@pytest.fixture()
def patched_fsp_device_class(
    mock_component_manager: unittest.mock.Mock,
) -> Type[Fsp]:
    """
    Return a device that is patched with a mock component manager.

    :param mock_component_manager: the mock component manager with
        which to patch the device

    :return: a device that is patched with a mock component
        manager.
    """

    class PatchedFsp(Fsp):
        """A device patched with a mock component manager."""

        def create_component_manager(
            self: PatchedFsp,
        ) -> unittest.mock.Mock:
            """
            Return a mock component manager instead of the usual one.

            :return: a mock component manager
            """
            self._communication_status: Optional[CommunicationStatus] = None
            self._component_power_mode: Optional[PowerMode] = None

            mock_component_manager._communication_status_changed_callback = (
                self._communication_status_changed
            )
            mock_component_manager._component_power_mode_changed_callback = (
                self._component_power_mode_changed
            )

            return mock_component_manager

    return PatchedFsp

@pytest.fixture()
def mock_fsp_corr_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    return builder()

@pytest.fixture()
def mock_fsp_corr_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    # add receptors to the mock pss subarray 
    # (this is required for test_UpdateJonesMatrix)
    builder.add_attribute("receptors", [1, 2, 3, 4])
    return builder()

@pytest.fixture()
def mock_fsp_pss_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def mock_fsp_pst_subarray() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.OFF)
    # add receptors to the mock pst subarray 
    # (this is required for test_UpdateBeamWeights)
    builder.add_attribute("receptors", [1, 2, 3, 4])
    return builder()

@pytest.fixture()
def mock_fsp_pst_subarray_group() -> unittest.mock.Mock:
    builder = MockGroupBuilder()
    builder.add_command("On", None)
    builder.add_command("Off", None)
    return builder()

@pytest.fixture()
def initial_mocks(
    mock_fsp_corr_subarray: unittest.mock.Mock,
    mock_fsp_corr_subarray_group: unittest.mock.Mock,
    mock_fsp_pss_subarray: unittest.mock.Mock,
    mock_fsp_pss_subarray_group: unittest.mock.Mock,
    mock_fsp_pst_subarray: unittest.mock.Mock,
    mock_fsp_pst_subarray_group: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_fsp_corr_subarray: a mock FspCorrSubarray.
    :param mock_fsp_corr_subarray_group: a mock FspCorrSubarray group.
    :param mock_fsp_pss_subarray: a mock FspPssSubarray.
    :param mock_fsp_pss_subarray_group: a mock FspPssSubarray group.
    :param mock_fsp_pst_subarray: a mock FspPstSubarray.
    :param mock_fsp_pst_subarray_group: a mock FspPstSubarray group.

    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "mid_csp_cbf/fspCorrSubarray/01_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/02_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/03_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspCorrSubarray/04_01": mock_fsp_corr_subarray,
        "mid_csp_cbf/fspPssSubarray/01_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/02_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/03_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPssSubarray/04_01": mock_fsp_pss_subarray,
        "mid_csp_cbf/fspPstSubarray/01_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/02_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/03_01": mock_fsp_pst_subarray,
        "mid_csp_cbf/fspPstSubarray/04_01": mock_fsp_pst_subarray,
        "FSP Subarray Corr": mock_fsp_corr_subarray_group,
        "FSP Subarray Pss": mock_fsp_pss_subarray_group,
        "FSP Subarray Pst": mock_fsp_pst_subarray_group,
    }
