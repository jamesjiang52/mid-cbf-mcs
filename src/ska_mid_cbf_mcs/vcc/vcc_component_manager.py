# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
VccComponentManager
Sub-element VCC component manager for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple, Callable, Optional

import logging
import json

# tango imports
import tango
from tango import DevState

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager, CommunicationStatus
)

from ska_tango_base.control_model import SimulationMode, PowerMode
from ska_tango_base.csp.obs import CspObsComponentManager
from ska_tango_base.commands import ResultCode

__all__ = ["VccComponentManager"]

VCC_PARAM_PATH = "mnt/vcc_param/"

class VccComponentManager(CbfComponentManager, CspObsComponentManager):
    """Component manager for Vcc class."""

    @property
    def config_id(self):
        """Return the configuration id."""
        return self._config_id

    @property
    def scan_id(self):
        """Return the scan id."""
        return self._scan_id

    @config_id.setter
    def config_id(self, config_id):
        """Set the configuration id."""
        self._config_id = config_id

    @scan_id.setter
    def scan_id(self, scan_id):
        """Set the configuration id."""
        self._scan_id = scan_id

    def __init__(
        self: VccComponentManager,
        simulation_mode: SimulationMode,
        vcc_controller: str,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[[CommunicationStatus], None],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable
    ) -> None:
        """
        Initialize a new instance.

        :param simulation_mode: simulation mode identifies if the real VCC HPS
                          applications or the simulator should be connected
        :param vcc_controller: FQDN of the HPS VCC controller device
        :param vcc_band: FQDNs of HPS VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between the 
            component manager and its component changes
        :param component_power_mode_changed_callback: callback to be called when 
            the component power mode changes
        :param component_fault_callback: callback to be called in event of 
            component fault
        """
        self._logger = logger

        self._simulation_mode = simulation_mode

        self._vcc_controller_fqdn = vcc_controller
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self.connected = False

        # initialize attribute values
        self.receptor_id = 0
        self.frequency_offset_k = 0
        self.frequency_offset_delta_f = 0

        self.scan_id = 0
        self.config_id = ""

        self.frequency_band = None
        self._freq_band_name = ""
        self.stream_tuning = (0, 0)
        self.frequency_band_offset_stream_1 = 0
        self.frequency_band_offset_stream_2 = 0
        self.rfi_flagging_mask = ""

        self.jones_matrix = [[0] * 16 for _ in range(26)]
        self.delay_model = [[0] * 6 for _ in range(26)]
        self.doppler_phase_correction = [0 for _ in range(4)]

        # initialize list of band proxies and band -> index translation;
        # entry for each of: band 1 & 2, band 3, band 4, band 5
        self._band_proxies = []
        self._vcc_controller_proxy = None
        self._freq_band_index = dict(zip(
            freq_band_dict().keys(), 
            [0, 0, 1, 2, 3, 3]
        ))

        self._sw_proxies = []

        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None
        )


    @property
    def simulation_mode(self: VccComponentManager) -> SimulationMode:
        """
        Get the simulation mode of the component manager.

        :return: simulation mode of the component manager
        """
        return self._simulation_mode


    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        if self.connected:
            self._logger.info("Already connected.")
            return

        super().start_communicating()

        if not self._simulation_mode:
            try:
                self._vcc_controller_proxy = CbfDeviceProxy(
                    fqdn=self._vcc_controller_fqdn, logger=self._logger)
                self._band_proxies = [CbfDeviceProxy(fqdn=fqdn, logger=self._logger
                    ) for fqdn in self._vcc_band_fqdn]
                self._sw_proxies = [CbfDeviceProxy(fqdn=fqdn, logger=self._logger
                ) for fqdn in self._search_window_fqdn]

                self.init_vcc_controller_parameters()
            except tango.DevFailed as dev_failed:
                self.update_component_power_mode(PowerMode.UNKNOWN)
                self.update_communication_status(CommunicationStatus.NOT_ESTABLISHED)
                self.update_component_fault(True)
                raise ConnectionError(
                    f"Error in proxy connection."
                ) from dev_failed

        self.connected = True
        self.update_component_power_mode(PowerMode.ON)
        self.update_communication_status(CommunicationStatus.ESTABLISHED)


    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.UNKNOWN)
        self.connected = False


    def init_vcc_controller_parameters(
        self: VccComponentManager
    ) -> None:
        """
        Initialize the set of parameters in the VCC Controller device that
        are common to all bands and will not change during scan configurations.
        """
        if not self._simulation_mode:
            try:
                # Skip this if the device has already been initialized
                if self._vcc_controller_proxy.State() != tango.DevState.INIT:
                    self._logger.info("VCC Controller parameters already initialized")
                    return

                param_init = {
                    "frequency_offset_k": self.frequency_offset_k,
                    "frequency_offset_delta_f": self.frequency_offset_delta_f
                }

                self._vcc_controller_proxy.InitCommonParameters(json.dumps(param_init))
            except tango.DevFailed as dev_failed:
                raise ConnectionError(
                    "Error connecting to VCC Controller device."
                ) from dev_failed

    def on(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn on VCC component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.ON)
        return (ResultCode.OK, "On command completed OK")


    def off(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn off VCC component; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.OFF)
        return (ResultCode.OK, "Off command completed OK")


    def standby(self: VccComponentManager) -> Tuple[ResultCode, str]:
        """
        Turn VCC component to standby; currently unimplemented.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.update_component_power_mode(PowerMode.STANDBY)
        return (ResultCode.OK, "Standby command completed OK")


    def configure_band(
        self: VccComponentManager,
        freq_band_name: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure the corresponding band. At the HPS level, this reconfigures the
        FPGA to the correct bitstream and enables the respective band device. All
        other band devices are disabled.

        :param freq_band_name: the frequency band name

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.debug(
            "VccComponentManager.configure_band(" + freq_band_name + ")"
        )

        (result_code, msg) = (ResultCode.OK, "ConfigureBand completed OK.")

        if not self._simulation_mode:
            try:
                self.frequency_band = freq_band_dict()[freq_band_name]
                self._freq_band_name = freq_band_name
                self._vcc_controller_proxy.ConfigureBand(self.frequency_band)
                
                # Set internal params for the configured band
                f = open(VCC_PARAM_PATH + "internal_params_receptor" + str(self.receptor_id) +
                    "_band" + freq_band_name + ".json")
                json_string = f.read()
                f.close()
                self._band_proxies[self._freq_band_index[self._freq_band_name]].SetInternalParameters(json_string)
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                (result_code, msg) = (ResultCode.FAILED, "ConfigureBand failed.")

        return (result_code, msg)

    def deconfigure(self: VccComponentManager) -> None:
        """Deconfigure scan configuration parameters."""
        self.doppler_phase_correction = [0 for _ in range(4)]
        self.jones_matrix = [[0] * 16 for _ in range(26)]
        self.delay_model = [[0] * 6 for _ in range(26)]
        self.rfi_flagging_mask = ""
        self.frequency_band_offset_stream_2 = 0
        self.frequency_band_offset_stream_1 = 0
        self.stream_tuning = (0, 0)
        self.frequency_band = None
        self._freq_band_name = ""
        self.config_id = ""
        self.scan_id = 0

        if not self._simulation_mode:
            try:
                self._vcc_controller_proxy.Unconfigure()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
        
    def configure_scan(self: VccComponentManager, argin: str) -> Tuple[ResultCode, str]:

        """
        Begin scan operation.

        :param argin: JSON string with the search window parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        configuration = json.loads(argin)
        self.config_id = configuration["config_id"]

        # TODO: The frequency band attribute is optional but 
        # if not specified the previous frequency band set should be used 
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency 
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        freq_band = freq_band_dict()[configuration["frequency_band"]]
        if self.frequency_band != freq_band:
            return (
                ResultCode.FAILED,
                f"Error in Vcc.ConfigureScan; scan configuration frequency band {freq_band} " + \
                f"not the same as enabled band device {self.frequency_band}"
            )

        if self.frequency_band in [4, 5]:
            self.stream_tuning = configuration["band_5_tuning"]

        self.frequency_band_offset_stream_1 = \
            int(configuration["frequency_band_offset_stream_1"])
        self.frequency_band_offset_stream_2 = \
            int(configuration["frequency_band_offset_stream_2"])
        
        if "rfi_flagging_mask" in configuration:
            self.rfi_flagging_mask = str(configuration["rfi_flagging_mask"])
        else:
            self._logger.warning("'rfiFlaggingMask' not given. Proceeding.")

        # Send the ConfigureScan command to the HPS
        if not self._simulation_mode:
            try:
                self._band_proxies[self._freq_band_index[self._freq_band_name]].ConfigureScan(argin)
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                return (ResultCode.FAILED, "Failed to connect to VCC band device")

        return (ResultCode.OK, "Vcc ConfigureScanCommand completed OK")

    def scan(self: VccComponentManager, scan_id: int) -> Tuple[ResultCode, str]:

        """
        Begin scan operation.

        :param argin: scan ID integer

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """

        self.scan_id = scan_id
        # Send the Scan command to the HPS
        if not self._simulation_mode:
            try:
                self._band_proxies[self._freq_band_index[self._freq_band_name]].Scan(scan_id)
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                return (ResultCode.FAILED, "Failed to connect to VCC band device")
        return (ResultCode.STARTED, "Vcc ScanCommand completed OK")

    def end_scan(self: VccComponentManager) -> Tuple[ResultCode, str]:

        """
        End scan operation.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        # Send the EndScan command to the HPS
        if not self._simulation_mode:
            try:
                self._band_proxies[self._freq_band_index[self._freq_band_name]].EndScan()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                return (ResultCode.FAILED, "Failed to connect to VCC band device")
        return (ResultCode.OK, "Vcc EndScanCommand completed OK")
    
    def abort(self):
        """Tell the current VCC band device to abort whatever it was doing."""
        if not self._simulation_mode:
            try:
                self._band_proxies[self._freq_band_index[self._freq_band_name]].Abort()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                return (ResultCode.FAILED, "Failed to connect to VCC band device")
        return (ResultCode.OK, "Vcc Abort command completed OK")

    def obsreset(self):
        """Reset the configuration."""
        if not self._simulation_mode:
            try:
                self._band_proxies[self._freq_band_index[self._freq_band_name]].ObsReset()
            except tango.DevFailed as df:
                self._logger.error(str(df.args[0].desc))
                return (ResultCode.FAILED, "Failed to connect to VCC band device")
        return (ResultCode.OK, "Vcc ObsReset command completed OK")

    def configure_search_window(
        self:VccComponentManager,
        argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure a search window by sending parameters from the input(JSON) to 
        SearchWindow self. This function is called by the subarray after the 
        configuration has already been validated, so the checks here have been 
        removed to reduce overhead.

        :param argin: JSON string with the search window parameters

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        result_code = ResultCode.OK
        msg = "ConfigureSearchWindwo completed OK"

        argin = json.loads(argin)

        # variable to use as SW proxy
        proxy_sw = None
        # Configure searchWindowID.
        if int(argin["search_window_id"]) == 1:
            proxy_sw = self._sw_proxies[0]
        elif int(argin["search_window_id"]) == 2:
            proxy_sw = self._sw_proxies[1]

        try:
            # Configure searchWindowTuning.
            if self.frequency_band in list(range(4)):  # frequency band is not band 5
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][self.frequency_band]

                if start_freq_Hz + self.frequency_band_offset_stream_1 + \
                        const.SEARCH_WINDOW_BW_HZ / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + self.frequency_band_offset_stream_1 - \
                        const.SEARCH_WINDOW_BW_HZ / 2:
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self._logger.warning(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                frequency_band_range_1 = (
                    self.stream_tuning[0] * 10 ** 9 + self.frequency_band_offset_stream_1 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self.stream_tuning[0] * 10 ** 9 + self.frequency_band_offset_stream_1 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                frequency_band_range_2 = (
                    self.stream_tuning[1] * 10 ** 9 + self.frequency_band_offset_stream_2 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self.stream_tuning[1] * 10 ** 9 + self.frequency_band_offset_stream_2 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                if (frequency_band_range_1[0] + \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                    int(argin["search_window_tuning"]) <= \
                    frequency_band_range_1[1] - \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2) or \
                        (frequency_band_range_2[0] + \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        frequency_band_range_2[1] - \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self._logger.warning(log_msg)

                # Configure tdcEnable.
                proxy_sw.tdcEnable = argin["tdc_enable"]
                if argin["tdc_enable"]:
                    proxy_sw.On()
                else:
                    proxy_sw.Off()

                # Configure tdcNumBits.
                if argin["tdc_enable"]:
                    proxy_sw.tdcNumBits = int(argin["tdc_num_bits"])

                # Configure tdcPeriodBeforeEpoch.
                if "tdc_period_before_epoch" in argin:
                    proxy_sw.tdcPeriodBeforeEpoch = int(argin["tdc_period_before_epoch"])
                else:
                    proxy_sw.tdcPeriodBeforeEpoch = 2
                    log_msg = "Search window specified, but 'tdcPeriodBeforeEpoch' not given. " \
                            "Defaulting to 2."
                    self._logger.warning(log_msg)

                # Configure tdcPeriodAfterEpoch.
                if "tdc_period_after_epoch" in argin:
                    proxy_sw.tdcPeriodAfterEpoch = int(argin["tdc_period_after_epoch"])
                else:
                    proxy_sw.tdcPeriodAfterEpoch = 22
                    log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. " \
                            "Defaulting to 22."
                    self._logger.warning(log_msg)

                # Configure tdcDestinationAddress.
                if argin["tdc_enable"]:
                    for receptor in argin["tdc_destination_address"]:
                        if receptor["receptor_id"] == self.receptor_id:
                            # TODO: validate input
                            proxy_sw.tdcDestinationAddress = \
                                receptor["tdc_destination_address"]
                            break

        except tango.DevFailed as df:
            self._logger.error(str(df.args[0].desc))
            (result_code, msg) = (ResultCode.FAILED, "Error configuring search window.")

        return (result_code, msg)


    def update_doppler_phase_correction(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's doppler phase correction

        :param argin: the doppler phase correction JSON string
        """
        argin = json.loads(argin)

        for dopplerDetails in argin:
            if dopplerDetails["receptor"] == self.receptor_id:
                coeff = dopplerDetails["dopplerCoeff"]
                if len(coeff) == 4:
                    self.doppler_phase_correction = coeff.copy()
                else:
                    log_msg = "Invalid length for 'dopplerCoeff' "
                    self._logger.error(log_msg)


    def update_delay_model(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's delay model

        :param argin: the delay model JSON string
        """
        argin = json.loads(argin)

        for delayDetails in argin:
            if delayDetails["receptor"] == self.receptor_id:
                for frequency_slice in delayDetails["receptorDelayDetails"]:
                    fsid = frequency_slice["fsid"]
                    coeff = frequency_slice["delayCoeff"]
                    if 1 <= fsid <= 26:
                        if len(coeff) == 6:
                            self.delay_model[fsid - 1] = coeff.copy()
                        else:
                            log_msg = "'delayCoeff' not valid for frequency slice " + \
                                f"{fsid} of receptor {self.receptor_id}"
                            self._logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fsid} not valid for receptor {self.receptor_id}"
                        self._logger.error(log_msg)


    def update_jones_matrix(self: VccComponentManager, argin: str) -> None:
        """
        Update Vcc's jones matrix

        :param argin: the jones matrix JSON string
        """
        argin = json.loads(argin)

        for receptor in argin:
            if receptor["receptor"] == self.receptor_id:
                for frequency_slice in receptor["receptorMatrix"]:
                    fs_id = frequency_slice["fsid"]
                    matrix = frequency_slice["matrix"]
                    if 1 <= fs_id <= 26:
                        if len(matrix) == 16:
                            self.jones_matrix[fs_id-1] = matrix.copy()
                        else:
                            log_msg = f"'matrix' not valid for frequency slice {fs_id} " + \
                                        f" of receptor {self.receptor_id}"
                            self._logger.error(log_msg)
                    else:
                        log_msg = f"'fsid' {fs_id} not valid for receptor {self.receptor_id}"
                        self._logger.error(log_msg)
