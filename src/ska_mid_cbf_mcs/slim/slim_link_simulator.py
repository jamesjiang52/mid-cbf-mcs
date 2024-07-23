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

import logging
from threading import Lock
from typing import Callable

from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode

__all__ = ["SlimLinkSimulator"]

BLOCK_LOST_COUNT_INDEX = 0
CDR_LOST_COUNT_INDEX = 1
BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkSimulator:
    """
    A simulator for the SLIM Link.
    """

    def __init__(
        self: SlimLinkSimulator,
        health_state_callback: Callable[[HealthState], None] | None,
        logger: logging.Logger,
    ) -> None:
        """
        Initialize a new instance.
        :param logger: a logger for this object to use
        """
        self.logger = logger

        self._link_name = ""
        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_idle_ctrl_word = 0x1B849FDE
        self._rx_idle_ctrl_word = 0xFFFFFFFF
        self._bit_error_rate = 0
        self._link_enabled = False
        self._read_counters = [0] * 9
        self._block_lost_cdr_lost_count = [0] * 2
        self._health_state_lock = Lock()
        self._health_state = HealthState.UNKNOWN

        self._device_health_state_callback = health_state_callback

    # --------------------
    # Simulated Properties
    # --------------------

    @property
    def link_name(self: SlimLinkSimulator) -> str:
        """
        The name of the link.

        :return: the SLIM link's name.
        :rtype: str
        """
        return self._link_name

    @link_name.setter
    def link_name(self: SlimLinkSimulator, link_name: str) -> None:
        """
        Set the link name value.

        :param link_name: The link's name.
        """
        self._link_name = link_name

    @property
    def tx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the link's tx device.

        :return: the tx device name.
        :rtype: str
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(self: SlimLinkSimulator, tx_device_name: str) -> None:
        """
        Set the tx device name value.

        :param tx_device_name: The tx device name.
        """
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkSimulator) -> str:
        """
        The name of the link's rx device.

        :return: the rx device name.
        :rtype: str
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(self: SlimLinkSimulator, rx_device_name: str) -> None:
        """
        Set the rx device name value.

        :param rx_device_name: The rx device name.
        """
        self._rx_device_name = rx_device_name

    @property
    def tx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The idle control word generated by hashing the tx device's FQDN.

        :return: the tx idle control word.
        :rtype: int
        """
        return self._tx_idle_ctrl_word

    @property
    def rx_idle_ctrl_word(self: SlimLinkSimulator) -> int:
        """
        The last idle control word received in the datastream

        :return: the rx idle control word.
        :rtype: int
        """
        return self._rx_idle_ctrl_word

    @property
    def bit_error_rate(self: SlimLinkSimulator) -> float:
        """
        The bit error rate in 66b-word-errors per second.

        :return: A passing bit error rate.
        :rtype: float
        """
        return 8.000e-12

    @property
    def rx_debug_alignment_and_lock_status(
        self: SlimLinkSimulator,
    ) -> list[bool]:
        """
        Returns the Debug Alignment and Lock Status flags of the rx HPS device

        :return: Debug Alignment and Lock Status flags of the rx HPS Device
        :rtype: list[int]
        """
        return [0, 1, 0, 1]

    @property
    def rx_link_occupancy(self: SlimLinkSimulator) -> float:
        """
        Retrieves and return the link occupancy of the rx device

        :return: Link Occupancy of the rx Device
        :rtype: float
        """
        return 0.5

    @property
    def tx_link_occupancy(self: SlimLinkSimulator) -> float:
        """
        Retrieves and return the link occupancy of the tx device

        :return: Link Occupancy of the tx Device
        :rtype: float
        """
        return 0.5

    @property
    def read_counters(self: SlimLinkSimulator) -> list[int]:
        """
        An array holding the counter values from the tx and rx devices in the order:
        [0] rx_word_count
        [1] rx_packet_count
        [2] rx_idle_word_count
        [3] rx_idle_error_count
        [4] rx_block_lost_count
        [5] rx_cdr_lost_count
        [6] tx_word_count
        [7] tx_packet_count
        [8] tx_idle_word_count

        :return: The read_counters array.
        :rtype: list[int]
        """
        return self._read_counters

    # -------
    # Helpers
    # -------

    def _update_device_health_state(
        self: SlimLinkSimulator,
        health_state: HealthState,
    ) -> None:
        """
        Handle a health state change.
        This is a helper method for use by subclasses.
        :param state: the new health state of the
            component manager.
        """
        with self._health_state_lock:
            if self._health_state != health_state:
                self._health_state = health_state
                self._push_health_state_update(health_state)

    def _push_health_state_update(
        self: SlimLinkSimulator, health_state: HealthState
    ) -> None:
        if self._device_health_state_callback is not None:
            self._device_health_state_callback(health_state)

    def connect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> None:
        """
        Link the tx and rx devices by synchronizing their idle control words.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        if self._tx_device_name == "" or self._rx_device_name == "":
            return ResultCode.FAILED, "Tx/Rx device name not set"
        self._rx_idle_ctrl_word = self._tx_idle_ctrl_word
        self.clear_counters()
        self._read_counters = [1000, 10, 100, 0, 1, 2, 1000, 10, 100]
        self._link_enabled = True
        self._link_name = f"{self._tx_device_name}->{self._rx_device_name}"

    def verify_connection(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        """
        Performs a health check on the SLIM link. No check is done if the link
        is not active; instead, the health state is set to UNKNOWN.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        if not self._link_enabled:
            self._update_device_health_state(HealthState.UNKNOWN)
            return ResultCode.OK, "link is not active"
        if (self._tx_idle_ctrl_word != self._rx_idle_ctrl_word) or (
            self._bit_error_rate > BER_PASS_THRESHOLD
        ):
            self._update_device_health_state(HealthState.FAILED)
            return ResultCode.OK, "link is not healthy"
        self._update_device_health_state(HealthState.OK)
        return ResultCode.OK, "link is healthy"

    def disconnect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> None:
        """
        Stops controlling the tx and rx devices. The link
        becomes inactive.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.clear_counters()
        self._link_name = ""
        self._link_enabled = False

    def clear_counters(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        """
        Clears the tx and rx device's read counters.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self._read_counters = [0] * 9
        result_msg = "Cleared counters for SLIM Link simulator."
        return ResultCode.OK, result_msg
