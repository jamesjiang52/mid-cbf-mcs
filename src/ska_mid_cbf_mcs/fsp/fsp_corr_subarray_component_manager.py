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
import json

import tango

from ska_mid_cbf_mcs.component.component_manager import (
    CommunicationStatus,
    CbfComponentManager,
)
from ska_tango_base.control_model import PowerMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.csp.obs.component_manager import CspObsComponentManager
from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

class FspCorrSubarrayComponentManager(CbfComponentManager, CspObsComponentManager):
    """A component manager for the FspCorrSubarray device."""

    def __init__(
        self: FspCorrSubarrayComponentManager,
        logger: logging.Logger,
        cbf_controller_address: str,
        vcc_fqdns_all: List[str],
        subarray_id: int,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        obs_state_model
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

        self._subarray_id = subarray_id

        self._cbf_controller_address = cbf_controller_address
        self._vcc_fqdns_all = vcc_fqdns_all

        self._receptors = []
        self._freq_band_name = ""
        self._frequency_band = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._frequency_slice_ID = 0
        self._bandwidth = 0
        self._bandwidth_actual = const.FREQUENCY_SLICE_BW
        self._zoom_window_tuning = 0
        self._integration_time = 0
        self._scan_id = 0
        self._config_id = ""
        self._channel_averaging_map = [
            [int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1, 0]
            for i in range(const.NUM_CHANNEL_GROUPS)
        ]
        self._vis_destination_address = {"outputHost": [], "outputMac": [], "outputPort": []}
        self._fsp_channel_offset = 0
        self._proxy_cbf_controller = None
        self._proxies_vcc = None

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=None,
            obs_state_model=obs_state_model
        )
    
    @property
    def frequency_band(self: FspCorrSubarrayComponentManager) -> tango.DevEnum:
        """
        Frequency Band

        :return: the frequency band 
        :rtype: tango.DevEnum
        """
        return self._frequency_band
    
    @property
    def stream_tuning(self: FspCorrSubarrayComponentManager) -> List[float]:
        """
        Band 5 Tuning

        :return: an array of float, 
                (first element corresponds to the first stream, 
                second to the second stream).
        :rtype: List[float]
        """
        return self._stream_tuning
    
    @property
    def frequency_band_offset_stream_1(self: FspCorrSubarrayComponentManager) -> int:
        """
        Frequency Band Offset Stream 1

        :return: the frequency band offset for stream 1
        :rtype: int
        """
        return self._frequency_band_offset_stream_1
    
    @property
    def frequency_band_offset_stream_2(self: FspCorrSubarrayComponentManager) -> int:
        """
        Frequency Band Offset Stream 2

        :return: the frequency band offset for stream 2
        :rtype: int
        """
        return self._frequency_band_offset_stream_2
    
    @property
    def frequency_slice_ID(self: FspCorrSubarrayComponentManager) -> int:
        """
        Frequency Slice ID

        :return: the frequency slice id
        :rtype: int
        """
        return self._frequency_slice_ID
    
    @property
    def bandwidth(self: FspCorrSubarrayComponentManager) -> int:
        """
        Bandwidth

        :return: the corr bandwidth (bandwidth to be correlated 
                 is <Full Bandwidth>/2^bandwidth).
        :rtype: int
        """
        return self._bandwidth
    
    @property
    def integration_time(self: FspCorrSubarrayComponentManager) -> int:
        """
        Integration Time

        :return: the integration time (millisecond). 
        :rtype: int
        """
        return self._integration_time
    
    @property
    def fsp_channel_offset(self: FspCorrSubarrayComponentManager) -> int:
        """
        FSP Channel Offset

        :return: the FSP channel offset
        :rtype: int
        """
        return self._integration_time
    
    @property
    def vis_destination_address(self: FspCorrSubarrayComponentManager) -> str:
        """
        VIS Destination Address

        :return: JSON string containing info about current SDP destination addresses being used
        :rtype: str
        """
        return self._vis_destination_address
    
    @property
    def output_link_map(self: FspCorrSubarrayComponentManager) -> List[List[int]]:
        """
        Output Link Map

        :return: the output link map
        :rtype: List[List[int]]
        """
        return self._output_link_map
    
    @property
    def channel_averaging_map(self: FspCorrSubarrayComponentManager) -> List[List[int]]:
        """
        Channel Averaging Map

        :return: the channel averaging map. Consists of 2*20 array of 
                integers(20 tupples representing 20* 744 channels). 
                The first element is the ID of the first channel in a channel group. 
                The second element is the averaging factor
        :rtype: List[List[int]]
        """
        return self._channel_averaging_map
    
    @property
    def zoom_window_tuning(self: FspCorrSubarrayComponentManager) -> int:
        """
        Zoom Window Tuning

        :return: the zoom window tuning
        :rtype: int
        """
        return self._zoom_window_tuning
    
    @property
    def config_id(self: FspCorrSubarrayComponentManager) -> str:
        """
        Config ID

        :return: the config id
        :rtype: str
        """
        return self._config_id
    
    @property
    def receptors(self: FspCorrSubarrayComponentManager) -> List[int]:
        """
        Receptors

        :return: list of receptor ids
        :rtype: List[int]
        """
        return self._receptors
    
    def start_communicating(
        self: FspCorrSubarrayComponentManager,
    ) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            return

        super().start_communicating()

        self._proxy_cbf_controller = CbfDeviceProxy(
            fqdn=self._cbf_controller_address,
            logger=self._logger
        )
        self._controller_max_capabilities = dict(
            pair.split(":") for pair in 
            self._proxy_cbf_controller.get_property("MaxCapabilities")["MaxCapabilities"]
        )

        # Connect to all VCC devices turned on by FspCorrSubarray:
        self._count_vcc = int(self._controller_max_capabilities["VCC"])
        self._fqdn_vcc = list(self._vcc_fqdns_all)[:self._count_vcc]
        self._proxies_vcc = [
            CbfDeviceProxy(
                logger=self._logger, 
                fqdn=address) for address in self._fqdn_vcc
        ]

        self._connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_fault(False)
        self.update_component_power_mode(PowerMode.OFF)
    
    def stop_communicating(self: FspCorrSubarrayComponentManager) -> None:
        """Stop communication with the component"""
        
        super().stop_communicating()
        
        self._connected = False
    
    def _add_receptors(
        self: FspCorrSubarrayComponentManager,
        argin: List[int]
    ) -> None:
        """
            Add specified receptors to the subarray.

            :param argin: ids of receptors to add. 
        """
        errs = []  # list of error messages
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               self._proxy_cbf_controller.receptorToVcc)
        for receptorID in argin:
            try:
                vccID = receptor_to_vcc[receptorID]
                subarrayID = self._proxies_vcc[vccID - 1].subarrayMembership

                # only add receptor if it belongs to the CBF subarray
                if subarrayID != self._subarray_id:
                    errs.append("Receptor {} does not belong to subarray {} subarrayID={}.".format(
                        str(receptorID), str(self._subarray_id), str(subarrayID)))
                else:
                    if receptorID not in self._receptors:
                        self._receptors.append(receptorID)
                    else:
                        log_msg = "Receptor {} already assigned to current FSP subarray.".format(
                            str(receptorID))
                        self._logger.warn(log_msg)

            except KeyError:  # invalid receptor ID
                errs.append("Invalid receptor ID: {}".format(receptorID))

        if errs:
            msg = "\n".join(errs)
            self._logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "_add_receptors execution",
                                           tango.ErrSeverity.ERR)

    def _remove_receptors(
        self: FspCorrSubarrayComponentManager,
        argin: List[int]
    ) -> None:
        """
            Remove specified receptors from the subarray.

            :param argin: ids of receptors to remove. 
        """
        for receptorID in argin:
            if receptorID in self._receptors:
                self._receptors.remove(receptorID)
            else:
                log_msg = "Receptor {} not assigned to FSP subarray. "\
                    "Skipping.".format(str(receptorID))
                self._logger.warn(log_msg)
    
    def _remove_all_receptors(self: FspCorrSubarrayComponentManager) -> None:
        """Remove all Receptors of this subarray"""
        self._remove_receptors(self._receptors[:])
    
    def configure_scan(
        self: FspCorrSubarrayComponentManager,
        configuration: str
    ) -> Tuple[ResultCode, str]:
        
        configuration = json.loads(configuration)

        self._freq_band_name = configuration["frequency_band"]
        self._frequency_band = freq_band_dict()[self._freq_band_name]

        self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream_1 = int(configuration["frequency_band_offset_stream_1"])
        self._frequency_band_offset_stream_2 = int(configuration["frequency_band_offset_stream_2"])

        self._remove_all_receptors()
        self._add_receptors(map(int, configuration["receptor_ids"]))

        self._frequency_slice_ID = int(configuration["frequency_slice_id"])

        self._bandwidth = int(configuration["zoom_factor"])
        self._bandwidth_actual = int(const.FREQUENCY_SLICE_BW/2**int(configuration["zoom_factor"]))

        if self._bandwidth != 0:  # zoomWindowTuning is required
            if self._frequency_band in list(range(4)):  # frequency band is not band 5
                self._zoom_window_tuning = int(configuration["zoom_window_tuning"])

                frequency_band_start = [*map(lambda j: j[0]*10**9, [
                    const.FREQUENCY_BAND_1_RANGE,
                    const.FREQUENCY_BAND_2_RANGE,
                    const.FREQUENCY_BAND_3_RANGE,
                    const.FREQUENCY_BAND_4_RANGE
                ])][self._frequency_band] + self._frequency_band_offset_stream_1
                frequency_slice_range = (
                    frequency_band_start + \
                        (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                    frequency_band_start +
                            self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                )

                if frequency_slice_range[0] + \
                        self._bandwidth_actual*10**6/2 <= \
                        int(configuration["zoom_window_tuning"])*10**3 <= \
                        frequency_slice_range[1] - \
                        self._bandwidth_actual*10**6/2:
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                        "Proceeding."
                    self._logger.warn(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                self._zoom_window_tuning = configuration["zoom_window_tuning"]

                frequency_slice_range_1 = (
                    self._stream_tuning[0]*10**9 + self._frequency_band_offset_stream_1 - \
                        const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                        (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                    self._stream_tuning[0]*10**9 + self._frequency_band_offset_stream_1 - \
                        const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                        self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                )

                frequency_slice_range_2 = (
                    self._stream_tuning[1]*10**9 + self._frequency_band_offset_stream_2 - \
                        const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                        (self._frequency_slice_ID - 1)*const.FREQUENCY_SLICE_BW*10**6,
                    self._stream_tuning[1]*10**9 + self._frequency_band_offset_stream_2 - \
                        const.BAND_5_STREAM_BANDWIDTH*10**9/2 + \
                        self._frequency_slice_ID*const.FREQUENCY_SLICE_BW*10**6
                )

                if (frequency_slice_range_1[0] + \
                        self._bandwidth_actual*10**6/2 <= \
                        int(configuration["zoom_window_tuning"])*10**3 <= \
                        frequency_slice_range_1[1] - \
                        self._bandwidth_actual*10**6/2) or\
                        (frequency_slice_range_2[0] + \
                        self._bandwidth_actual*10**6/2 <= \
                        int(configuration["zoom_window_tuning"])*10**3 <= \
                        frequency_slice_range_2[1] - \
                        self._bandwidth_actual*10**6/2):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'zoomWindowTuning' partially out of observed frequency slice. "\
                        "Proceeding."
                    self._logger.warn(log_msg)


        self._integration_time = int(configuration["integration_factor"])

        self._fsp_channel_offset = int(configuration["channel_offset"])

        if "output_host" in configuration:
            self._vis_destination_address["outputHost"] = configuration["output_host"]
        elif self._vis_destination_address["outputHost"] == []:
                self._vis_destination_address["outputHost"] = [[0, "192.168.0.1"]]
        
        if "output_mac" in configuration:
            self._vis_destination_address["outputMac"] = configuration["output_mac"]
        elif self._vis_destination_address["outputMac"] == []:
            self._vis_destination_address["outputMac"] = [[0, "06-00-00-00-00-01"]]
        
        if "output_port" in configuration:
            self._vis_destination_address["outputPort"] = configuration["output_port"]
        elif self._vis_destination_address["outputPort"] == []:
            self._vis_destination_address["outputPort"] = [[0, 9000, 1]]

        self._output_link_map = configuration["output_link_map"]

        if "channel_averaging_map" in configuration:
            self._channel_averaging_map = configuration["channel_averaging_map"]
        else:
            self._channel_averaging_map = [
                [int(i*const.NUM_FINE_CHANNELS/const.NUM_CHANNEL_GROUPS) + 1, 0]
                for i in range(const.NUM_CHANNEL_GROUPS)
            ]
            log_msg = "FSP specified, but 'channelAveragingMap not given. Default to averaging "\
                "factor = 0 for all channel groups."
            self._logger.warn(log_msg)

        self._config_id = configuration["config_id"]

        return (ResultCode.OK, "FspCorrSubarray ConfigureScan command completed OK")