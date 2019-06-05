"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import importlib
import sys
sys.path.insert(0, "../commons")

from tango import DeviceProxy
from tango.test_context import DeviceTestContext
import global_enum

@pytest.fixture(scope="class")
def create_cbf_master_proxy():
    return DeviceProxy("mid_csp_cbf/master/main")

@pytest.fixture(scope="class")
def create_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/cbfSubarray/01")

@pytest.fixture(scope="class")
def create_subarray_2_proxy():
    return DeviceProxy("mid_csp_cbf/cbfSubarray/02")

@pytest.fixture(scope="class")
def create_vcc_proxies():
    return [DeviceProxy("mid_csp_cbf/vcc/" + str(i + 1).zfill(3)) for i in range(197)]

@pytest.fixture(scope="class")
def create_tm_telstate_proxy():
    return DeviceProxy("ska1_mid/tm/telmodel")
