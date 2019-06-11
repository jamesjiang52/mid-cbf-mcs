# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" FspPss Tango device prototype

FspPss TANGO device class for the prototype
"""

# PyTango imports
import PyTango
from PyTango import DebugIt
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import device_property
from PyTango import AttrQuality, DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(FspPss.additionnal_import) ENABLED START #
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
from skabase.SKACapability.SKACapability import SKACapability
# PROTECTED REGION END #    //  FspPss.additionnal_import

__all__ = ["FspPss", "main"]


class FspPss(SKACapability):
    """
    FspPss TANGO device class for the prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(FspPss.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  FspPss.class_variable

    # -----------------
    # Device Properties
    # -----------------

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKACapability.init_device(self)
        # PROTECTED REGION ID(FspPss.init_device) ENABLED START #
        self.set_state(PyTango.DevState.INIT)
        self._health_state = HealthState.UNKNOWN.value
        self.set_state(PyTango.DevState.DISABLE)
        # PROTECTED REGION END #    //  FspPss.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(FspPss.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspPss.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(FspPss.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  FspPss.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------

    @command(
        dtype_in='DevState',
        doc_in='New state'
    )
    def SetState(self, argin):
        # PROTECTED REGION ID(FspPss.SetState) ENABLED START #
        self.set_state(argin)
        # PROTECTED REGION END #    //  FspPss.SetState

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(FspPss.main) ENABLED START #
    return run((FspPss,), args=args, **kwargs)
    # PROTECTED REGION END #    //  FspPss.main

if __name__ == '__main__':
    main()
