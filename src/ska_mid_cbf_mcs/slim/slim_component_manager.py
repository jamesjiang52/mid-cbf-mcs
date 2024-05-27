# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2023 National Research Council of Canada


from __future__ import annotations

import re
import threading
from typing import Any, Callable, Optional

import tango
import yaml
from ska_control_model import TaskStatus
from beautifultable import BeautifulTable
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    HealthState,
    PowerState,
    SimulationMode,
)
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)

__all__ = ["SlimComponentManager"]


class SlimComponentManager(CbfComponentManager):
    """
    Manages a Serial Lightweight Interconnect Mesh (SLIM).
    """

    def __init__(
        self: SlimComponentManager,
        *args: Any,
        link_fqdns: List[str],
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param link_fqdns: a list of SLIM Link FQDNs
        :param simulation_mode: Enum that identifies if the simulator should be used
        """
        super().__init__(*args, **kwargs)
        self.simulation_mode = simulation_mode

        self._mesh_configured = False
        self._config_str = ""

        # a list of [tx_fqdn, rx_fqdn] for active links.
        self._active_links = []

        # SLIM Link Device proxies
        self._link_fqdns = link_fqdns
        self._dp_links = []

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug("Entering SlimComponentManager.start_communicating")

        if self.communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating.")
            return

        super().start_communicating()

        self._dp_links = []
        self.logger.debug(f"Link FQDNs: {self._link_fqdns}")
        if self._link_fqdns is None:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error(
                "'Links' device property is unpopulated. Check charts."
            )
            return

        for fqdn in self._link_fqdns:
            try:
                dp = context.DeviceProxy(device_name=fqdn)
                dp.adminMode = AdminMode.ONLINE
                self._dp_links.append(dp)
            except AttributeError as ae:
                # Thrown if the device exists in the db but the executable is not running.
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self.logger.error(
                    f"Attribute error {ae}. Ensure SlimLink devices are running."
                )
                return
            except tango.DevFailed as df:
                # Thrown if the device doesn't exist in the db.
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self.logger.error(
                    f"Failed to set AdminMode of {fqdn} to ONLINE: {df.args[0].desc}"
                )
                return
        # This moves the op state model.
        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self.logger.debug("Entering SlimComponentManager.stop_communicating")

        for dp in self._dp_links:
            dp.adminMode = AdminMode.OFFLINE
        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model.
        super().stop_communicating()

    @property
    def is_communicating(self) -> bool:
        """
        Returns whether or not the SLIM can be communicated with.

        :return: whether the SLIM is communicating
        """
        return self.communication_state == CommunicationStatus.ESTABLISHED

    def on(self) -> tuple[ResultCode, str]:
        """
        On command. Currently just returns OK. The device
        does nothing until mesh configuration is provided via
        the Configure command.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering SlimComponentManager.on")

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    def get_configuration_string(self) -> str:
        """
        Returns the configurations string used to configure the SLIM.

        :return: the SLIM configuration string
        :rtype: str
        """
        return self._config_str

    def get_link_fqdns(self) -> list[str]:
        """
        Returns a list of SLIM Link FQDNs.

        :return: the SLIM links assosiated with the mesh.
        :rtype: list[str]
        """
        fqdns = []
        for idx, txrx in enumerate(self._active_links):
            fqdn = self._link_fqdns[idx]
            fqdns.append(fqdn)
        return fqdns

    def get_link_names(self) -> list[str]:
        """
        Returns a list of SLIM Link names, formatted 'tx_device_name->rx_device_name'.

        :return: the names of SLIM links assosiated with the mesh.
        :rtype: list[str]
        """
        names = []
        for idx, txrx in enumerate(self._active_links):
            name = self._dp_links[idx].linkName
            names.append(name)
        return names

    def get_health_summary(self) -> list[HealthState]:
        """
        Returns a list of HealthState enums describing the status of each link.

        :return: the health state of each SLIM link in the mesh.
        :rtype: list[HealthState]
        """
        summary = []
        for idx, txrx in enumerate(self._active_links):
            link_health = self._dp_links[idx].healthState
            summary.append(link_health)
        return summary

    def get_bit_error_rate(self) -> list[float]:
        """
        Returns a list containing the bit-error rates for each link.

        :return: the bit-error rate (BER) of each SLIM link in the mesh.
        :rtype: list[float]
        """
        bers = []
        for idx, txrx in enumerate(self._active_links):
            ber = self._dp_links[idx].bitErrorRate
            bers.append(ber)
        return bers

    def get_device_counters(self) -> list[list[int]]:
        """
        Returns a list containing the counters array for each link

        :return: the counter array for each SLIM link in the mesh
        :rtype: List[List[int]]
        """

        counters = []
        for idx, txrx in enumerate(self._active_links):
            counter = self._dp_links[idx].counters
            counters.append(counter)

        return counters

    def _calculate_rx_idle_word_rate(
        self, rx_idle_word_count: int, rx_idle_error_count: int
    ) -> tuple[str, str]:
        """
        TODO:
        Calculates and return a string the rate of Rx Idle Error Word Count over Rx Idle Word Count
        Along with a status that indicates if the Rate passes the Bit Error Rate Threshold
        Returns a tuple of the rate and the pass/fail BER status

        :return: A tuple of (rx_idle_word_error_rate,rx_ber_pass_status)
        :rtype: tuple[str,str]
        """
        if rx_idle_word_count == 0:
            rx_idle_word_error_rate = "NaN"
            rx_ber_pass_status = "Unknown"
        else:
            rx_idle_word_rate_float = rx_idle_error_count / rx_idle_word_count
            rx_idle_word_error_rate = f"{rx_idle_word_rate_float:.3e}"
            if rx_idle_word_rate_float < const.BER_PASS_THRESHOLD:
                rx_ber_pass_status = "Passed"
            else:
                rx_ber_pass_status = "Failed"
        return (rx_idle_word_error_rate, rx_ber_pass_status)

    def slim_test(self: SlimComponentManager) -> tuple[ResultCode, str]:
        counters: list[int] = []
        names: list[str] = []
        occupancy: list[list[float]]
        debug_flags: list[list[bool]]
        rx_error_rate_and_status: list[tuple[str, str]] = []

        # grab the common values we need for the individual tests
        # to minimize device proxy access
        # try block to catch exceptions from devicce proxy access

        for idx, txrx in enumerate(self._active_links):
            dp_link = self._dp_links[idx]
            counter = dp_link.counters
            rx_idle_word_count = counter[2]
            rx_idle_error_count = counter[3]
            counters.append(counter)
            names.append(dp_link.linkName)
            occupancy.append([dp_link.rx_link_occupancy, dp_link.tx_link_occupancy])
            debug_flags.append(dp_link.rx_debug_alignment_and_lock_status)
            rx_error_rate_and_status.append(
                self._calculate_rx_idle_word_rate(
                    rx_idle_word_count, rx_idle_error_count
                )
            )

        # Summary check for SLIM Link Status and Bit Error Rate
        self._slim_links_ber_check_summary(
            counters, names, rx_error_rate_and_status
        )

        # More detail table for the SLIM Link health
        self._slim_table(
            counters, names, occupancy, debug_flags, rx_error_rate_and_status
        )

        return (ResultCode.OK, "SLIM Test Completed")

    def _slim_links_ber_check_summary(
        self: SlimComponentManager,
        all_counters: list[int],
        names: list[str],
        rx_error_rate_and_status: list[tuple[str]],
    ) -> None:
        """
        Logs a summary status of the SLIM Link health for each device on the Mesh
        Specifically, this will calcualte the bit-error rate for a rx device in the mesh
        and compared to a threshold set in global_enum.py
        """

        res = "\nSLIM BER Check:\n\n"
        for idx in range(len(self._active_links)):
            counters = all_counters[idx]
            # tx rx fqdn link name
            name = names[idx]

            rx_word_count = counters[0]
            rx_idle_word_count = counters[2]

            # word error rate: a ratio of rx idle error count compared to the
            # count of rx idle word transmitted
            (
                rx_idle_word_error_rate,
                rx_ber_pass_status,
            ) = rx_error_rate_and_status[idx]
            rx_words = rx_word_count + rx_idle_word_count

            res += f"Link Name: {name}\n"
            res += f"Slim Link status (rx_status): {rx_ber_pass_status}\n"
            res += f"rx_wer:{rx_idle_word_error_rate}\n"
            res += f"rx_rate_gbps:{rx_idle_word_count / rx_words * const.GBPS if rx_words != 0 else 'NaN'}\n"
            res += "\n"
        self.logger.info(res)

    def _slim_table(
        self: SlimComponentManager,
        counters: list[int],
        names: list[str],
        occupancy: list[float],
        debug_flags: list[bool],
        rx_error_rate_and_status: list[tuple[str, str]],
    ) -> None:
        """
        Logs a summary for the rx and tx device on the Mesh
        """

        table = BeautifulTable(maxwidth=180)
        table.columns.header = [
            "Link",
            "CDR locked\n(lost)",
            "Block Aligned\n(lost)",
            "Tx Data (Gbps)\n(words)",
            "Tx Idle (Gbps)",
            "Rx Data\n(Gbps)\n(words)",
            "Rx Idle\n(Gbps)",
            "Idle Error\nCount",
            "Word\nError Rate",
        ]

        for idx in range(len(self._active_links)):
            rx_word_count = counters[idx][0]
            rx_idle_word_count = counters[idx][2]
            rx_idle_error_count = counters[idx][3]
            tx_word_count = counters[idx][6]
            tx_idle_word_count = counters[idx][8]
            tx_words = tx_word_count + tx_idle_word_count
            rx_words = rx_word_count + rx_idle_word_count

            # Making the tx rx name shorter by keeping only the board name and the tx/rx port
            tx_name = (
                (names[idx].split("->")[0].split("/"))[0] + "/" + (names[idx].split("->")[0].split("/"))[-1]
            )
            rx_name = (
                (names[idx].split("->")[1].split("/"))[0] + "/" + (names[idx].split("->")[1].split("/"))[-1]
            )

            data_row = (
                # Name
                f"{tx_name}\n->{rx_name}",
                # CDR locked/lost
                f"{debug_flags[3]}\n({debug_flags[2]})",
                # Block locked/lost
                f"{debug_flags[1]}\n({debug_flags[0]})",
                # Tx data
                f"{occupancy[idx][1] * const.GBPS:.2f}\n({tx_word_count})",
                # Tx idle - Guard for divide by zero
                f"{tx_idle_word_count/tx_words * const.GBPS:.2f}"
                if tx_words != 0
                else "NaN",
                # Rx data
                f"{occupancy[idx][0] * const.GBPS:.2f}\n({rx_word_count})",
                # Rx idle - Guard for divide by zero
                f"{rx_idle_word_count/rx_words * const.GBPS:.2f}"
                if rx_words != 0
                else "NaN",
                # Idle error count
                f"{rx_idle_error_count} /\n{rx_words:.2e}",
                # Word error rate
                rx_error_rate_and_status[idx][0],
            )
            table.rows.append(data_row)

        self.logger.info(f"\nSLIM Health Summary Table\n{table}")

    def _parse_link(self, link: str) -> list[str]:
        """
        Each link is in the format of "tx_fqdn -> rx_fqdn". If the
        link is disabled, then the text ends with [x].

        :param link: a string describing a singular SLIM link.

        :return: the pair of HPS tx and rx device FQDNs that make up a link.
        :rtype: list[str]
        """
        tmp = re.sub(r"[\s\t]", "", link)  # removes all whitespaces

        # ignore disabled links or lines without the expected format
        if tmp.endswith("[x]") or ("->" not in tmp):
            return None
        txrx = tmp.split("->")
        if len(txrx) != 2:
            return None
        return txrx

    def _validate_mesh_config(self, links: list) -> None:
        """
        Checks if the requested SLIM configuration is valid.

        :param links: a list of HPS tx and rx device pairs to be configured as SLIM links.
        :raise Tango exception: if SLIM configuration is not valid.
        """
        tx_set = set([x[0] for x in links])
        rx_set = set([y[1] for y in links])
        if len(tx_set) != len(rx_set) or len(tx_set) != len(links):
            msg = "Tx and Rx devices must be unique in the configuration."
            self.logger.error(msg)
            tango.Except.throw_exception(
                "Slim_Validate_",
                msg,
                "_validate_mesh_config()",
            )
        return

    def _parse_links_yaml(self, yaml_str: str) -> list[list[str]]:
        """
        Parse a yaml string containing the mesh links.

        :param yaml_str: the string defining the mesh links
        :raise Tango exception: if the configuration is not valid yaml.
        :return: a list of HPS tx and rx device pairs as [Tx FQDN, Rx FQDN]
        :rtype: list[list[str]]
        """
        links = list()
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to load YAML: {e}")
            tango.Except.throw_exception(
                "Slim_Parse_YAML",
                "Cannot parse SLIM configuration YAML",
                "_parse_links_yaml()",
            )
        for k, v in data.items():
            for line in v:
                txrx = self._parse_link(line)
                if txrx is not None:
                    links.append(txrx)
        self._validate_mesh_config(
            links
        )  # throws exception if validation fails
        return links

    def _initialize_links(self) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to connect and starts polling each link's health state.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Creating {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.warn(
                "No active links are defined in the mesh configuration"
            )
            return ResultCode.OK, "_initialize_links completed OK"
        if len(self._active_links) > len(self._dp_links):
            msg = "Too many links defined in the link configuration. Not enough SlimLink devices exist."
            self.logger.error(msg)
            return ResultCode.FAILED, msg
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].txDeviceName = txrx[0]
                self._dp_links[idx].rxDeviceName = txrx[1]

                # The SLIM link may need to wait for Tx/Rx to initialize
                self._dp_links[idx].set_timeout_millis(10000)
                [rc, msg] = self._dp_links[idx].ConnectTxRx()
                self._dp_links[idx].set_timeout_millis(3000)

                # TODO: Need to add guard incase LRC was rejected.
                # TODO: Need to add LRC wait mechanism
                if rc[0] is not ResultCode.OK:
                    return rc[0], msg[0]

                # TODO: Should replace polling here with a subscription to the link's healthState
                # poll link health every 20 seconds
                if self._simulation_mode is False:
                    self._dp_links[idx].poll_command("VerifyConnection", 20000)
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to initialize SLIM links: {df.args[0].desc}"
            )
            raise df
        except IndexError as ie:
            msg = "Not enough Links defined in device properties"
            self.logger.error(f"msg - {ie}")
            tango.Except.throw_exception(
                "IndexError",
                msg,
                "_initialize_links()",
            )

        self.logger.info("Successfully initialized SLIM links")
        self._mesh_configured = True
        return ResultCode.OK, "_initialize_links completed OK"

    def _disconnect_links(self) -> tuple[ResultCode, str]:
        """
        Triggers the configured SLIM links to disconnect and cease polling health states.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug(
            f"Disconnecting {len(self._active_links)} links: {self._active_links}"
        )
        if len(self._active_links) == 0:
            self.logger.info(
                "No active links are defined in the SlimLink configuration"
            )
            return ResultCode.OK, "_disconnect_links completed OK"
        try:
            for idx, txrx in enumerate(self._active_links):
                self._dp_links[idx].stop_poll_command("VerifyConnection")
                [rc, msg] = self._dp_links[idx].DisconnectTxRx()

                # TODO: Need to add guard incase LRC was rejected.
                # TODO: Need to add LRC wait mechanism
                if rc[0] is not ResultCode.OK:
                    return rc[0], msg[0]
        except tango.DevFailed as df:
            self.logger.error(
                f"Failed to disconnect SLIM links: {df.args[0].desc}"
            )
            raise df

        self.logger.info("Successfully disconnected SLIM links")
        self._mesh_configured = False
        return ResultCode.OK, "_disconnect_links completed OK"

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_off_allowed(self) -> bool:
        self.logger.debug("Checking if Off is allowed.")
        if self.power_state != PowerState.ON:
            self.logger.warning(
                f"Off not allowed; PowerState is {self.power_state}"
            )
            return False
        return True

    def _off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> tuple[ResultCode, str]:
        """
        Off command. Disconnects SLIM Links if mesh is configured, else returns OK.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self.logger.debug("Entering SlimComponentManager.off")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Off", task_callback, task_abort_event
        ):
            return

        self._update_component_state(power=PowerState.OFF)

        try:
            rc, msg = self._disconnect_links()
            if rc is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(rc, msg),
                )
                return
        except tango.DevFailed as df:
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df.args[0].desc,
                ),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Off completed OK",
            ),
        )

    def off(
        self: SlimComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._off,
            is_cmd_allowed=self.is_off_allowed,
            task_callback=task_callback,
        )

    def is_configure_allowed(self) -> bool:
        self.logger.debug("Checking if Configure is allowed.")
        if self.communication_state != CommunicationStatus.ESTABLISHED:
            self.logger.warning(
                f"Configure not allowed; CommunicationStatus is {self.communication_state}"
            )
            return False
        return True

    def _configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Configure command. Parses the mesh configuration.

        :param config_str: a string in YAML format describing the links to be created.
        :param task_callback: Calls device's _command_tracker.update_comand_info(). Set by SumbittedSlowCommand's do().
        :param task_abort_event: Calls self._task_executor._abort_event. Set by AbortCommandsCommand's do().
        """
        self.logger.debug("Entering SlimComponentManager.configure()")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set(
            "Configure", task_callback, task_abort_event
        ):
            return
        # Each element in the config is [tx_fqdn, rx_fqdn]
        self._config_str = config_str

        try:
            self._active_links = self._parse_links_yaml(self._config_str)

            self.logger.debug(
                f"Configuring {len(self._dp_links)} links with simulationMode = {self.simulation_mode}"
            )
            for dp in self._dp_links:
                dp.adminMode = AdminMode.OFFLINE
                dp.simulationMode = self.simulation_mode
                dp.adminMode = AdminMode.ONLINE

            if self._mesh_configured:
                self.logger.debug(
                    "SLIM was previously configured. Disconnecting links before re-initializing."
                )
                rc, msg = self._disconnect_links()
                if rc is not ResultCode.OK:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            rc,
                            msg,
                        ),
                    )
                    return
            self.logger.debug("Initializing SLIM Links")
            rc, msg = self._initialize_links()
            if rc is not ResultCode.OK:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(
                        rc,
                        msg,
                    ),
                )
                return
        except AttributeError as ae:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=ae,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    "AttributeError encountered. Ensure SlimLink devices are running.",
                ),
            )
            return
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            task_callback(
                exception=df,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    df.args[0].desc,
                ),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Configure completed OK",
            ),
        )

    def configure(
        self: SlimComponentManager,
        config_str: str,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[ResultCode, str]:
        self.logger.info(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._configure,
            args=[config_str],
            is_cmd_allowed=self.is_configure_allowed,
            task_callback=task_callback,
        )
