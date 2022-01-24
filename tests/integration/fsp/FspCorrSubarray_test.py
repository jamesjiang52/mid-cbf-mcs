#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.
"""Contain the tests for the FspSubarray."""
from __future__ import annotations

import pytest
import time

import tango
from tango import DevState

from ska_tango_base.control_model import AdminMode

class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    def test_Connect(
        self: TestFspCorrSubarray, 
        test_proxies,         
        fsp_id: int,
        sub_id: int):
        """
        Test the initial states and verify the component manager 
        can start communicating
        """
        device_under_test = test_proxies.fspSubarray["CORR"][sub_id][fsp_id]

        assert device_under_test.State() == DevState.DISABLE 

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        # controller device should be in OFF state after start_communicating 
        time.sleep(1)
        assert device_under_test.State() == DevState.OFF