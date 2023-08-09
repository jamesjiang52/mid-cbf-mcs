#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfController component manager."""
from __future__ import annotations

from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable


class TestControllerComponentManager:
    """Tests of the controller component manager."""

    def test_communication(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the controller component manager's management of communication.

        :param controller_component_manager: the controller component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        controller_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        controller_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    def test_On(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test on().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        (result_code, _) = controller_component_manager.on()
        assert result_code == ResultCode.OK

    def test_Off(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test off().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        (result_code, result_msg) = controller_component_manager.off()
        print(" ---- result_msg == ", result_msg)
        assert result_code == ResultCode.OK

    def test_Standby(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test standby().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        (result_code, _) = controller_component_manager.standby()
        assert result_code == ResultCode.OK
