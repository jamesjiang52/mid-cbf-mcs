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

import tango
import json
import logging
import subprocess

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import SimulationMode

__all__ = [
    "TalonDxComponentManager"
]

class TalonDxComponentManager:
    """A component manager for the Talon-DX boards. Used to configure and start
    the Tango applications on the HPS of each board."""

    def __init__(
        self: TalonDxComponentManager,
        talondx_config_path: str,
        simulation_mode: SimulationMode,
        logger: logging.Logger
    ) -> None:
        """
        Initialise a new instance.

        :param talondx_config_path: path to the directory containing configuration
                                    files and artifacts for the Talon boards
        :param simulation_mode: simulation mode identifies if the real Talon boards or
                                a simulator should be used; note that currently there
                                is no simulator for the Talon boards, so the component
                                manager does nothing when in simulation mode
        :param logger: a logger for this object to use
        """
        self.talondx_config_path = talondx_config_path
        self.simulation_mode = simulation_mode
        self.logger = logger

    def configure_talons(self: TalonDxComponentManager) -> ResultCode:
        """
        Performs all actions to configure the Talon boards after power on and
        start the HPS device servers. This includes: copying the device server
        binaries and FPGA bitstream to the Talon boards, starting the HPS master
        device server and sending the configure command to each DsHpsMaster.

        :return: ResultCode.FAILED if any operations failed, else ResultCode.OK
        """
        # Simulation mode does not do anything yet
        if self.simulation_mode == SimulationMode.TRUE:
            return ResultCode.OK

        # Try to read in the configuration file
        try:
            config_path = f"{self.talondx_config_path}/talondx-config.json"
            with open(config_path) as json_fd:
                self.talondx_config = json.load(json_fd)
        except IOError:
            self.logger.error(f"Could not open {config_path} file")
            return ResultCode.FAILED

        if self._copy_binaries_and_bitstream() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._start_hps_master() == ResultCode.FAILED:
            return ResultCode.FAILED

        if self._configure_hps_master() == ResultCode.FAILED:
            return ResultCode.FAILED

    def _secure_copy(
        self: TalonDxComponentManager,
        target: str,
        src: str,
        dest: str
    ) -> None:
        """
        Execute a secure file copy to the specified target address.

        :param target: target address to copy to
        :param src: Source file path
        :param dest: Destination file path

        :raise subprocess.CalledProcessError: if the file copy fails
        """
        target_dest = f"{target}:{dest}"
        subprocess.run(["scp", src, target_dest], check=True, shell=True)

    def _copy_binaries_and_bitstream(self: TalonDxComponentManager) -> ResultCode:
        """
        Copy the relevant device server binaries and FPGA bitstream to each
        Talon board.

        :return: ResultCode.OK if all artifacts were copied successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config-commands"]:
            try:
                ip = talon_cfg["target"]
                target = f"root@{ip}"
                
                # Make the DS binaries directory
                src_dir = f"{self.talondx_config_path}/artifacts"
                dest_dir = talon_cfg["ds-path"]
                subprocess.run(["ssh", target, f"mkdir -p {dest_dir}"], check=True, shell=True)

                # Copy the HPS master binary
                self._secure_copy(
                    target=target,
                    src=f"{src_dir}/ds-hps-master/build-ci-cross/bin/dshpsmaster",
                    dest=dest_dir)

                # Copy the remaining DS binaries
                for binary_name in talon_cfg["devices"]:
                    for ds_binary in self.talondx_config["ds-binaries"]:
                        name = ds_binary["name"]
                        if binary_name == name.replace('-', ''):
                            self._secure_copy(
                                target=target,
                                src=f"{src_dir}/{name}/build-ci-cross/bin/{binary_name}",
                                dest=dest_dir)

                # Copy the FPGA bitstream
                dest_dir = talon_cfg["fpga-dest-path"]
                subprocess.run(["ssh", target, f"mkdir -p {dest_dir}"], check=True, shell=True)

                fpga_dtb_name = talon_cfg['fpga-dtb-name']
                self._secure_copy(
                    target=target, 
                    src=f"{src_dir}/{fpga_dtb_name}",
                    dest=dest_dir)

                fpga_rbf_name = talon_cfg['fpga-rbf-name']
                self._secure_copy(
                    target=target, 
                    src=f"{src_dir}/{fpga_rbf_name}",
                    dest=dest_dir)
            except subprocess.CalledProcessError as err:
                self.logger.error(f"Command '{err.cmd}' to target {target} failed with " \
                    f"error code {err.returncode}")
                ret = ResultCode.FAILED
            
        return ret

    def _start_hps_master(self: TalonDxComponentManager) -> ResultCode:
        """
        Start the DsHpsMaster on each Talon board and attempt to
        connect to each device proxy.

        :return: ResultCode.OK if all HPS masters were started successfully,
                 otherwise ResultCode.FAILED
        """
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config["config-commands"]:
            ip = talon_cfg["target"]
            target = f"root@{ip}"
            inst = talon_cfg["server-instance"]
            path = talon_cfg["ds-path"]

            try:
                subprocess.run(["ssh", target, 
                    f"source /lib/firmware/hps_software/run_hps_master.sh {path} {inst}"],
                    check=True, shell=True)
            except subprocess.CalledProcessError as err:
                self.logger.error(f"Command '{err.cmd}' to target {target} failed with " \
                    f"error code {err.returncode}")
                ret = ResultCode.FAILED   

        # Create device proxies for the HPS master devices
        self.proxies = {}
        for talon_cfg in self.talondx_config["config-commands"]:
            fqdn = talon_cfg["ds-hps-master"]

            try:
                self.proxies[fqdn] = CbfDeviceProxy(fqdn=fqdn, logger=self.logger)
            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(f"Failed connection to {fqdn} device: {item.reason}")
                ret = ResultCode.FAILED

        return ret

    def _configure_hps_master(self: TalonDxComponentManager) -> ResultCode:
        """
        Send the configure command to all the DsHpsMaster devices.

        :return: ResultCode.OK if all configure commands were sent successfully,
                 otherwise ResultCode.FAILED
        """    
        ret = ResultCode.OK
        for talon_cfg in self.talondx_config['config-commands']:
            hps_master_fqdn = talon_cfg["ds-hps-master"]
            hps_master = self.proxies[hps_master_fqdn]

            self.logger.info(f"Sending configure command to {hps_master_fqdn}")
            try:
                cmd_ret = hps_master.command_inout("configure", json.dumps(talon_cfg))
                if cmd_ret != 0:
                    self.logger.error(f"Configure command for {hps_master_fqdn}" \
                        f" device failed with error code {cmd_ret}")
                    ret = ResultCode.FAILED

            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(f"Exception while sending configure command" \
                        f" to {hps_master_fqdn} device: {str(item.reason)}")
                ret = ResultCode.FAILED

        return ret