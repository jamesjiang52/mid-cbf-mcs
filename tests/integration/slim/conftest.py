# @pytest.fixture() - indicates helper for testing

# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for MCS Slim integration tests."""

from __future__ import annotations

import pytest

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ... import test_utils


@pytest.fixture(name="device_under_test")
def device_under_test_fixture() -> context.DeviceProxy:
    """
    Fixture that returns the device under test.

    :param test_context: the context in which the tests run
    :return: the device under test
    """
    return context.DeviceProxy(device_name="mid_csp_cbf/slim/slim-fs")


@pytest.fixture(name="test_proxies")
def test_proxies_fixture() -> pytest.fixture:
    """
    Fixture that returns the proxies needed in this test.

    :return: a TestProxies object containing device proxies to all devices required
             in the scope of integration testing the device under test
    """

    class TestProxies:
        def __init__(self: TestProxies) -> None:
            """
            Initialize all device proxies needed for integration testing the DUT.

            Includes:
            - 4 TalonLru
            - 4 PowerSwitch
            - 4 SlimLink
            """

            # Talon LRU
            self.talon_lru = []
            for i in range(1, 5):  # 4 Talon LRUs for now
                self.talon_lru.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/talon_lru/{i:03}",
                    )
                )

            # Power switch
            self.power_switch = []
            for i in range(1, 4):  # 3 Power Switches
                self.power_switch.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/power_switch/{i:03}",
                    )
                )

            # SlimLink
            self.slim_link = []
            for i in range(0, 3):  # 4 SlimLinks
                self.slim_link.append(
                    context.DeviceProxy(
                        device_name=f"mid_csp_cbf/fs_links/{i:03}",
                    )
                )

    return TestProxies()


@pytest.fixture(name="change_event_callbacks")
def slim_change_event_callbacks(
    device_under_test: context.DeviceProxy,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = [
        "longRunningCommandResult",
        "state",
        "healthState",
    ]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    test_utils.change_event_subscriber(
        device_under_test, change_event_attr_list, change_event_callbacks
    )
    return change_event_callbacks


@pytest.fixture(name="lru_change_event_callbacks")
def lru_change_event_callbacks(
    test_proxies: pytest.fixture,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = ["longRunningCommandResult", "state"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for lru in test_proxies.talon_lru:
        test_utils.change_event_subscriber(
            lru, change_event_attr_list, change_event_callbacks
        )
    return change_event_callbacks


@pytest.fixture(name="ps_change_event_callbacks")
def ps_change_event_callbacks(
    test_proxies: pytest.fixture,
) -> MockTangoEventCallbackGroup:
    change_event_attr_list = ["state"]
    change_event_callbacks = MockTangoEventCallbackGroup(
        *change_event_attr_list, timeout=15.0
    )
    for lru in test_proxies.power_switch:
        test_utils.change_event_subscriber(
            lru, change_event_attr_list, change_event_callbacks
        )
    return change_event_callbacks
