#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the FspPstSubarray component manager."""
from __future__ import annotations
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray_component_manager import (
    FspPstSubarrayComponentManager,
)
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus

import json
import os

import pytest

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFspPstSubarrayComponentManager:
    """Tests of the fsp pst subarray component manager."""

    def test_communication(
        self: TestFspPstSubarrayComponentManager,
        fsp_pst_subarray_component_manager: FspPstSubarrayComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the fsp pst subarray component manager's management of communication.

        :param fsp_pst_subarray_component_manager: the fsp pst subarray component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            fsp_pst_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pst_subarray_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            fsp_pst_subarray_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        fsp_pst_subarray_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            fsp_pst_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize(
        "config_file_name",
        [("/../../data/FspPstSubarray_ConfigureScan_basic.json")],
    )
    def test_configure_scan(
        self: TestFspPstSubarrayComponentManager,
        fsp_pst_subarray_component_manager: FspPstSubarrayComponentManager,
        config_file_name: str,
    ) -> None:
        """
        Test the fsp pst subarray component manager's configure_scan command.

        :param fsp_pst_subarray_component_manager: the fsp pst subarray component
            manager under test.
        :param config_file_name: the name of the configuration file
        """
        assert (
            fsp_pst_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pst_subarray_component_manager.start_communicating()

        assert fsp_pst_subarray_component_manager.receptors == []
        assert fsp_pst_subarray_component_manager.timing_beams == []
        assert fsp_pst_subarray_component_manager.timing_beam_id == []
        assert fsp_pst_subarray_component_manager.output_enable == 0

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        fsp_pst_subarray_component_manager.configure_scan(json_str)
        f.close()

        assert (
            fsp_pst_subarray_component_manager.fsp_id
            == configuration["fsp_id"]
        )
        for i, timingBeam in enumerate(configuration["timing_beam"]):
            assert list(fsp_pst_subarray_component_manager.receptors) == list(
                timingBeam["receptor_ids"]
            )
            assert fsp_pst_subarray_component_manager.timing_beams[
                i
            ] == json.dumps(timingBeam)
            assert fsp_pst_subarray_component_manager.timing_beam_id[i] == int(
                timingBeam["timing_beam_id"]
            )

    @pytest.mark.parametrize("scan_id", [1, 2])
    def test_scan(
        self: TestFspPstSubarrayComponentManager,
        fsp_pst_subarray_component_manager: FspPstSubarrayComponentManager,
        scan_id: int,
    ) -> None:
        """
        Test the fsp pst subarray component manager's scan command.

        :param fsp_pst_subarray_component_manager: the fsp pst subarray component
            manager under test.
        :param scan_id: the scan id
        """

        assert (
            fsp_pst_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pst_subarray_component_manager.start_communicating()

        fsp_pst_subarray_component_manager.scan(scan_id)
        assert fsp_pst_subarray_component_manager.scan_id == scan_id
