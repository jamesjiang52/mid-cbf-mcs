#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Slim."""

from __future__ import annotations

# Standard imports
import os
import time
from typing import Iterator
from unittest.mock import Mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_mid_cbf_mcs.slim.slim_device import Slim
from ska_mid_cbf_mcs.testing import context

from ... import test_utils

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports

# SKA imports

CONST_WAIT_TIME = 1


class TestSlim:
    """
    Test class for SLIM tests.
    """

    @pytest.fixture(name="test_context")
    def slim_test_context(
        self: TestSlim, initial_mocks: dict[str, Mock]
    ) -> Iterator[context.TTCMExt.TCExt]:
        harness = context.TTCMExt()
        # This device is set up as expected
        harness.add_device(
            device_name="mid_csp_cbf/slim/001",
            device_class=Slim,
            Links=[
                "mid_csp_cbf/slim_link/001",
                "mid_csp_cbf/slim_link/002",
                "mid_csp_cbf/slim_link/003",
                "mid_csp_cbf/slim_link/004",
            ],
        )
        # This device uses SlimLink mocks that will return ResultCode.FAILED
        harness.add_device(
            device_name="mid_csp_cbf/slim_fail/001",
            device_class=Slim,
            Links=[
                "mid_csp_cbf/slim_link_fail/001",
                "mid_csp_cbf/slim_link_fail/002",
                "mid_csp_cbf/slim_link_fail/003",
                "mid_csp_cbf/slim_link_fail/004",
            ],
        )

        for name, mock in initial_mocks.items():
            harness.add_mock_device(device_name=name, device_mock=mock)

        with harness as test_context:
            yield test_context

    def test_State(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test State

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.State() == DevState.DISABLE

    def test_Status(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Status

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.Status() == "The device is in DISABLE state."

    def test_adminMode(
        self: TestSlim, device_under_test: context.DeviceProxy
    ) -> None:
        """
        Test Admin Mode

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert device_under_test.adminMode == AdminMode.OFFLINE

    def test_adminModeOnline(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.State() == DevState.OFF

    def test_On(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
    ) -> None:
        """
        Test Admin Mode Online

        :param device_under_test: fixture that provides a
            :py:class:`context.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
        # prepare device
        assert test_utils.device_online_and_on(device_under_test)

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [
            ("./tests/data/slim_test_config.yaml"),
            ("./tests/data/slim_test_config_inactive.yaml"),
        ],
    )
    def test_Configure(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert test_utils.device_online_and_on(device_under_test)
        time.sleep(CONST_WAIT_TIME)

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(
                mesh_config.read()
            )

        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "Configure completed OK"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_fail_config.yaml")],
    )
    def test_Configure_too_many_links(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert test_utils.device_online_and_on(device_under_test)
        time.sleep(CONST_WAIT_TIME)

        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test.Configure(
                mesh_config.read()
            )

        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[3, "Too many links defined in the link configuration. Not enough SlimLink devices exist."]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./tests/data/slim_test_config.yaml")],
    )
    def test_Configure_slim_link_init_fails(
        self: TestSlim,
        device_under_test_fail: context.DeviceProxy,
        change_event_callbacks_fail: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Configure() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """
        assert test_utils.device_online_and_on(device_under_test_fail)

        time.sleep(CONST_WAIT_TIME)
        with open(mesh_config_filename, "r") as mesh_config:
            result_code, command_id = device_under_test_fail.Configure(
                mesh_config.read()
            )

        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks_fail[
            "longRunningCommandResult"
        ].assert_change_event(
            (
                f"{command_id[0]}",
                '[3, "ConnectTxRx Failed: Mock"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks_fail.assert_not_called()

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [
            ("./tests/data/slim_test_config.yaml"),
            ("./tests/data/slim_test_config_inactive.yaml"),
        ],
    )
    def test_Off(
        self: TestSlim,
        device_under_test: context.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the Off() command

        :param device_under_test: fixture that provides a
        :py:class:`tango.DeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
        """

        self.test_Configure(
            device_under_test, change_event_callbacks, mesh_config_filename
        )

        result_code, command_id = device_under_test.Off()
        assert result_code == [ResultCode.QUEUED]

        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                f"{command_id[0]}",
                '[0, "Off completed OK"]',
            )
        )
        # assert if any captured events have gone unaddressed
        change_event_callbacks.assert_not_called()
