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

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState

__all__ = ["SlimLinkSimulator"]

BLOCK_LOST_COUNT_INDEX = 0
CDR_LOST_COUNT_INDEX = 1
BER_PASS_THRESHOLD = 8.000e-11


class SlimLinkSimulator:
    """
    A simulator for the SLIM Link.
    """

    def __init__(self: SlimLinkSimulator, logger: logging.Logger) -> None:
        """
        Initialize a new instance.
        """
        self._logger = logger

        self._link_name = ""
        self._tx_device_name = ""
        self._rx_device_name = ""
        self._tx_idle_ctrl_word = 0x1B849FDE
        self._rx_idle_ctrl_word = 0xFFFFFFFF
        self._bit_error_rate = 0
        self._link_enabled = False
        self._read_counters = [0] * 9
        self._block_lost_cdr_lost_count = [0] * 2
        self._update_health_state(HealthState.UNKNOWN)

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

    def connect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
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
        self._link_enabled = True
        self._link_name = f"{self._tx_device_name}->{self._rx_device_name}"
        return ResultCode.OK, "Connection to SLIM TX simulator successful"

    def verify_connection(
        self: SlimLinkSimulator,
    ) -> HealthState:
        """
        Performs a health check on the SLIM link. No check is done if the link
        is not active; instead, the health state is set to UNKNOWN.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        if not self._link_enabled:
            self._update_health_state(HealthState.UNKNOWN)
            return ResultCode.OK, "link is not active"
        if self._tx_idle_ctrl_word != self._rx_idle_ctrl_word:
            self._update_health_state(HealthState.FAILED)
            return ResultCode.OK, "link is not healthy"
        if self._bit_error_rate > BER_PASS_THRESHOLD:
            self._update_health_state(HealthState.FAILED)
            return ResultCode.OK, "link is not healthy"
        self._update_health_state(HealthState.OK)
        return ResultCode.OK, "link is healthy"

    def disconnect_slim_tx_rx(
        self: SlimLinkSimulator,
    ) -> tuple[ResultCode, str]:
        """
        Stops controlling the tx and rx devices. The link
        becomes inactive.

        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        self.clear_counters()
        self._link_enabled = False
        result_msg = "Disconnected from SLIM Tx simulator."
        return ResultCode.OK, result_msg

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
