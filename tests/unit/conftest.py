# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Ported from the SKA Low MCCS project:
# https://gitlab.com/ska-telescope/ska-low-mccs/-/blob/main/testing/src/tests/unit/conftest.py
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module contains pytest-specific test harness for MCS unit tests."""

import unittest
from typing import Callable

import pytest
import tango

from ska_mid_cbf_mcs.testing.mock.mock_callable import (
    MockCallable,
    MockChangeEventCallback,
)
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder


def pytest_itemcollected(item: pytest.Item) -> None:
    """
    Modify a test after it has been collected by pytest.

    This pytest hook implementation adds the "forked" custom mark to all
    tests that use the ``tango_harness`` fixture, causing them to be
    sandboxed in their own process.

    :param item: the collected test for which this hook is called
    """
    if "tango_harness" in item.fixturenames:  # type: ignore[attr-defined]
        item.add_marker("forked")


@pytest.fixture()
def mock_callback_called_timeout() -> float:
    """
    Return the time to wait for a mock callback to be called when a call is expected.

    This is a high value because calls will usually arrive much much
    sooner, but we should be prepared to wait plenty of time before
    giving up and failing a test.

    :return: the time to wait for a mock callback to be called when a
        call is asserted.
    """
    return 10.0


@pytest.fixture()
def mock_callback_not_called_timeout() -> float:
    """
    Return the time to wait for a mock callback to be called when a call is unexpected.

    An assertion that a callback has not been called can only be passed
    once we have waited the full timeout period without a call being
    received. Thus, having a high value for this timeout will make such
    assertions very slow. It is better to keep this value fairly low,
    and accept the risk of an assertion passing prematurely.

    :return: the time to wait for a mock callback to be called when a
        call is unexpected.
    """
    return 0.5


@pytest.fixture()
def mock_callback_factory(
    mock_callback_called_timeout: float,
    mock_callback_not_called_timeout: float,
) -> Callable[[], MockCallable]:
    """
    Return a factory that returns a new mock callback each time it is called.

    Use this fixture in tests that need more than one mock_callback. If
    your tests only needs a single mock callback, it is simpler to use
    the :py:func:`mock_callback` fixture.

    :param mock_callback_called_timeout: the time to wait for a mock
        callback to be called when a call is expected
    :param mock_callback_not_called_timeout: the time to wait for a mock
        callback to be called when a call is unexpected

    :return: a factory that returns a new mock callback each time it is
        called.
    """
    return lambda: MockCallable(
        called_timeout=mock_callback_called_timeout,
        not_called_timeout=mock_callback_not_called_timeout,
    )


@pytest.fixture()
def device_state_changed_callback(
    mock_change_event_callback_factory: Callable[
        [str], MockChangeEventCallback
    ],
) -> MockChangeEventCallback:
    """
    Return a mock change event callback for device state change.

    :param mock_change_event_callback_factory: fixture that provides a
        mock change event callback factory (i.e. an object that returns
        mock callbacks when called).

    :return: a mock change event callback to be registered with the
        device via a change event subscription, so that it gets called
        when the device state changes.
    """
    return mock_change_event_callback_factory("state")


@pytest.fixture()
def device_admin_mode_changed_callback(
    mock_change_event_callback_factory: Callable[
        [str], MockChangeEventCallback
    ],
) -> MockChangeEventCallback:
    """
    Return a mock change event callback for device admin mode change.

    :param mock_change_event_callback_factory: fixture that provides a
        mock change event callback factory (i.e. an object that returns
        mock callbacks when called).

    :return: a mock change event callback to be registered with the
        device via a change event subscription, so that it gets called
        when the device admin mode changes.
    """
    return mock_change_event_callback_factory("adminMode")


@pytest.fixture()
def device_health_state_changed_callback(
    mock_change_event_callback_factory: Callable[
        [str], MockChangeEventCallback
    ],
) -> MockChangeEventCallback:
    """
    Return a mock change event callback for device health state change.

    :param mock_change_event_callback_factory: fixture that provides a
        mock change event callback factory (i.e. an object that returns
        mock callbacks when called).

    :return: a mock change event callback to be called when the
        device health state changes. (The callback has not yet been
        subscribed to the device; this must be done as part of the
        test.)
    """
    return mock_change_event_callback_factory("healthState")


@pytest.fixture()
def mock_controller() -> unittest.mock.Mock:
    builder = MockDeviceBuilder()
    builder.set_state(tango.DevState.ON)
    builder.add_attribute("receptorToVcc", ["1:1", "36:2", "63:3", "100:4"])
    builder.add_attribute("maxCapabilities", ["VCC:4", "FSP:4", "Subarray:1"])
    builder.add_property(
        "MaxCapabilities",
        {"MaxCapabilities": ["VCC:4", "FSP:4", "Subarray:1"]},
    )
    return builder()
