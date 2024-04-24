# @pytest.fixture() - indicates helper for testing
# fixture for mock component manager
# fixture to patch fixture
# fixture to mock external proxies

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

from __future__ import annotations

import unittest

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.harness import TangoTestHarnessContext
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

# Tango imports
from ska_mid_cbf_mcs.testing import context
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

from ... import test_utils

# Local imports


@pytest.fixture(name="device_under_test")
def device_under_test_fixture(
    test_context: TangoTestHarnessContext,
) -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return test_context.get_device("mid_csp_cbf/fs_links/001")


@pytest.fixture(name="change_event_callbacks")
def slim_link_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture()
def mock_slim_tx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 123456)
    builder.add_attribute("read_counters", [6, 7, 8])

    builder.add_command("ping", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_rx() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 0)
    builder.add_attribute("read_counters", [0, 1, 2, 3, 0, 0])
    builder.add_attribute("bit_error_rate", 8e-12)

    builder.add_command("ping", None)
    builder.add_command("initialize_connection", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_tx_regenerate() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", None)
    builder.add_attribute("read_counters", [6, 7, 8])

    builder.add_command("ping", None)
    builder.add_command("clear_read_counters", None)
    return builder()


@pytest.fixture()
def mock_slim_rx_unhealthy() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.INIT)
    builder.add_attribute("idle_ctrl_word", 0)
    builder.add_attribute("read_counters", [0, 1, 2, 3, 4, 5])
    builder.add_attribute("bit_error_rate", 8e-8)

    builder.add_command("ping", None)
    builder.add_command("initialize_connection", None)
    builder.add_command("clear_read_counters", None)
    return builder()
