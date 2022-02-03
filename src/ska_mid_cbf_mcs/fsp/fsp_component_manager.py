# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada
from __future__ import annotations
from typing import Callable, Optional, Tuple, List

import logging
import tango

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)
from ska_tango_base.control_model import PowerMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.group_proxy import CbfGroupProxy

class FspComponentManager(CbfComponentManager):
    """A component manager for the Fsp device."""

    def __init__(
        self: FspComponentManager,
        logger: logging.Logger,
        fsp_corr_subarray_fqdns_all: List[str],
        fsp_pss_subarray_fqdns_all: List[str],
        fsp_pst_subarray_fqdns_all: List[str],
        fsp_corr_subarray_address: str,
        fsp_pss_subarray_address: str,
        fsp_pst_subarray_address: str,
        vlbi_address: str,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param push_change_event: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        """
        self._logger = logger
        
        self._connected = False

        self._fsp_corr_subarray_fqdns_all = fsp_corr_subarray_fqdns_all
        self._fsp_pss_subarray_fqdns_all = fsp_pss_subarray_fqdns_all
        self._fsp_pst_subarray_fqdns_all = fsp_pst_subarray_fqdns_all
        self._fsp_corr_subarray_address = fsp_corr_subarray_address
        self._fsp_pss_subarray_address = fsp_pss_subarray_address
        self._fsp_pst_subarray_address = fsp_pst_subarray_address
        self._vlbi_address = vlbi_address

        self._group_fsp_corr_subarray = None
        self._group_fsp_pss_subarray = None
        self._group_fsp_pst_subarray = None
        self._proxy_correlation = None
        self._proxy_pss = None
        self._proxy_pst = None
        self._proxy_vlbi = None
        self._proxy_fsp_corr_subarray = None
        self._proxy_fsp_pss_subarray = None
        self._proxy_fsp_pst_subarray = None

        self._subarray_membership = []

        super().__init__(
            logger,
            push_change_event_callback,
            communication_status_changed_callback,
            component_power_mode_changed_callback,
            None,
        )
    
    @property
    def subarray_membership(self: FspComponentManager) -> List[int]:
        """
        Subarray Membership

        :return: an array of affiliations of the FSP.
        :rtype: List[int]
        """
        return self._subarray_membership
    
    def start_communicating(
        self: FspComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self.__get_capability_proxies()
        self.__get_group_proxies()

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)
    
    def stop_communicating(self: FspComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
    
    def __get_capability_proxies(
            self: FspComponentManager, 
    ) -> None:
        """Establish connections with the capability proxies"""
        # for now, assume that given addresses are valid

        if self._proxy_correlation is None:
            if self._fsp_corr_subarray_address:
                self._proxy_correlation = CbfDeviceProxy(
                    fqdn=self._fsp_corr_subarray_address,
                    logger=self._logger
                )
            
        if self._proxy_pss is None:
            if self._fsp_pss_subarray_address:
                self._proxy_pss = CbfDeviceProxy(
                    fqdn=self._fsp_pss_subarray_address,
                    logger=self._logger
                )
            
        if self._proxy_pst is None:
            if self._fsp_pst_subarray_address:
                self._proxy_pst = CbfDeviceProxy(
                    fqdn=self._fsp_pst_subarray_address,
                    logger=self._logger
                )
            
        if self._proxy_vlbi is None:
            if self._vlbi_address:
                self._proxy_vlbi = CbfDeviceProxy(
                    fqdn=self._vlbi_address,
                    logger=self._logger
                )

        if self._proxy_fsp_corr_subarray is None:
            if self._fsp_corr_subarray_fqdns_all:
                self._proxy_fsp_corr_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self._logger) \
                    for fqdn in self._fsp_corr_subarray_fqdns_all]

        if self._proxy_fsp_pss_subarray is None:
            if self._fsp_pss_subarray_fqdns_all:
                self._proxy_fsp_pss_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self._logger) \
                    for fqdn in self._fsp_pss_subarray_fqdns_all]

        if self._proxy_fsp_pst_subarray is None:
            if self._fsp_pst_subarray_fqdns_all:
                self._proxy_fsp_pst_subarray = \
                    [CbfDeviceProxy(fqdn=fqdn, logger=self._logger) \
                    for fqdn in self._fsp_pst_subarray_fqdns_all]
    
    def __get_group_proxies(
        self: FspComponentManager, 
    ) -> None:
        """Establish connections with the group proxies"""
        if self._group_fsp_corr_subarray is None:
            self._group_fsp_corr_subarray = CbfGroupProxy("FSP Subarray Corr", logger=self._logger)
            for fqdn in list(self._fsp_corr_subarray_fqdns_all):
                self._group_fsp_corr_subarray.add(fqdn)
        if self._group_fsp_pss_subarray is None:
            self._group_fsp_pss_subarray = CbfGroupProxy("FSP Subarray Pss", logger=self._logger)
            for fqdn in list(self._fsp_pss_subarray_fqdns_all):
                self._group_fsp_pss_subarray.add(fqdn)
        if self._group_fsp_pst_subarray is None:
            self._group_fsp_pst_subarray = CbfGroupProxy("FSP Subarray Pst", logger=self._logger)
            for fqdn in list(self._fsp_pst_subarray_fqdns_all):
                self._group_fsp_pst_subarray.add(fqdn)
    
    def _remove_subarray_membership(
        self: FspComponentManager,
        argin: int,
        ) -> None:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing 
        (no subarray is using this FSP), set function mode to empty.

        :param argin: an integer representing the subarray affiliation
        """
        if argin in self._subarray_membership:
            self._subarray_membership.remove(argin)
            # change function mode to IDLE if no subarrays are using it.
            if not self._subarray_membership:
                self._function_mode = 0
        else:
            log_msg = "FSP does not belong to subarray {}.".format(argin)
            self._logger.warn(log_msg)
    
    def on(      
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn on the controller and its subordinate devices 

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            self._proxy_correlation.SetState(tango.DevState.DISABLE)
            self._proxy_pss.SetState(tango.DevState.DISABLE)
            self._proxy_pst.SetState(tango.DevState.DISABLE)
            self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            self._group_fsp_corr_subarray.command_inout("On")
            self._group_fsp_pss_subarray.command_inout("On")
            self._group_fsp_pst_subarray.command_inout("On")
            
            message = "CbfController On command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp On command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
    
    def off(      
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Turn off the fsp and its subordinate devices 

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            self._proxy_correlation.SetState(tango.DevState.OFF)
            self._proxy_pss.SetState(tango.DevState.OFF)
            self._proxy_pst.SetState(tango.DevState.OFF)
            self._proxy_vlbi.SetState(tango.DevState.OFF)
            self._group_fsp_corr_subarray.command_inout("Off")
            self._group_fsp_pss_subarray.command_inout("Off")
            self._group_fsp_pst_subarray.command_inout("Off")

            for subarray_ID in self._subarray_membership[:]:
                self.RemoveSubarrayMembership(subarray_ID)

            
            message = "Fsp Off command completed OK"
            return (ResultCode.OK, message)

        else:
            log_msg = "Fsp Off command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)
        
    def standby(      
        self: FspComponentManager,
    ) -> Tuple[ResultCode, str]:
        """
        Put the fsp into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        message = "Fsp Standby command completed OK"
        return (ResultCode.OK, message)
    
    def set_function_mode(      
        self: FspComponentManager,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """
        Put the fsp into low power standby mode

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """

        if self._connected:

            if argin == "IDLE":
                self._function_mode = 0
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "CORR":
                self._function_mode = 1
                self._proxy_correlation.SetState(tango.DevState.ON)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "PSS-BF":
                self._function_mode = 2
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.ON)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "PST-BF":
                self._function_mode = 3
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.ON)
                self._proxy_vlbi.SetState(tango.DevState.DISABLE)
            elif argin == "VLBI":
                self._function_mode = 4
                self._proxy_correlation.SetState(tango.DevState.DISABLE)
                self._proxy_pss.SetState(tango.DevState.DISABLE)
                self._proxy_pst.SetState(tango.DevState.DISABLE)
                self._proxy_vlbi.SetState(tango.DevState.ON)
            else:
                # shouldn't happen
                self._logger.warn("functionMode not valid. Ignoring.")
                message = "Fsp SetFunctionMode command failed: \
                    functionMode not valid"
                return (ResultCode.FAILED, message)

            message = "Fsp SetFunctionMode command completed OK"
            return (ResultCode.OK, message)
        
        else:
            log_msg = "Fsp SetFunctionMode command failed: \
                    proxies not connected"
            self._logger.error(log_msg)
            return (ResultCode.FAILED, log_msg)

    