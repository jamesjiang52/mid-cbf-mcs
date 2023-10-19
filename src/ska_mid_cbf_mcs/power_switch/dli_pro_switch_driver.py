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
from typing import List

import requests
from requests.structures import CaseInsensitiveDict
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode

from ska_mid_cbf_mcs.power_switch.pdu_common import Outlet

__all__ = ["DLIProSwitchDriver"]


class DLIProSwitchDriver:
    """
    A driver for the DLI web power switch.
    The PDU provides a restapi through http.
    Valid outlet IDs are 0 to 7.

    :param ip: IP address of the power switch
    :param login: Login username of the power switch
    :param password: Login password for the power switch
    :param logger: a logger for this object to use
    """

    query_timeout_s = 6
    """Timeout in seconds used when waiting for a reply from the power switch"""

    def __init__(
        self: DLIProSwitchDriver,
        ip: str,
        login: str,
        password: str,
        logger: logging.Logger,
    ) -> None:
        """
        Initialise a new instance.
        """
        self.logger = logger

        # Initialize the various URLs for monitoring/controlling the power switch
        self.base_url = f"http://{ip}"
        self.outlet_list_url = f"{self.base_url}/restapi/relay/outlets/"
        self.outlet_state_url = (
            f"{self.base_url}/restapi/relay/outlets/REPLACE_OUTLET/"
        )
        self.outlet_control_url = (
            f"{self.base_url}/restapi/relay/outlets/REPLACE_OUTLET/state/"
        )

        # Initialize the login credentials
        self.login = login
        self.password = password

        # Initialize the request header
        self.header = CaseInsensitiveDict()
        self.header["Accept"] = "application/json"
        self.header["X-CSRF"] = "x"
        self.header["Content-Type"] = "application/x-www-form-urlencoded"

        # Initialize the value of the payload data to pass to
        # the request to turn on/off an outlet
        self.turn_on_action = "value=true"
        self.turn_off_action = "value=false"

        # Initialize the expected on/off values of the response
        # to the request to turn on/off an outlet
        self.state_on = "True"
        self.state_off = "False"

        # valid range 0 to 7
        self.outlet_id_list: List(str) = [str(i) for i in range(0, 8)]

        # Initialize outlets
        self.outlets: List(Outlet) = []

    def initialize(self: DLIProSwitchDriver) -> None:
        """
        Initializes any variables needed for further communication with the
        power switch. Should be called once before any of the other methods.
        """
        self.outlets = self.get_outlet_list()

    def stop(self: DLIProSwitchDriver) -> None:
        """
        Stops communicating with the PDU and cleans up.
        """
        pass

    @property
    def num_outlets(self: DLIProSwitchDriver) -> int:
        """
        Get number of outlets present in this power switch.

        :return: number of outlets
        """
        return len(self.outlets)

    @property
    def is_communicating(self: DLIProSwitchDriver) -> bool:
        """
        Returns whether or not the power switch can be communicated with.

        :return: whether the power switch is communicating
        """
        try:
            response = requests.get(
                url=self.base_url,
                verify=False,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code == requests.codes.ok:
                return True
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return False
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return False

    def get_outlet_power_mode(
        self: DLIProSwitchDriver, outlet: str
    ) -> PowerMode:
        """
        Get the power mode of a specific outlet.

        :param outlet: outlet ID
        :return: power mode of the outlet

        :raise AssertionError: if outlet ID is out of bounds
        :raise AssertionError: if outlet power mode is different than expected
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        url = self.outlet_state_url.replace("REPLACE_OUTLET", outlet)
        outlet_idx = self.outlet_id_list.index(outlet)

        try:
            response = requests.get(
                url=url,
                verify=False,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )
            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                try:
                    resp = response.json()
                    state = str(resp["state"])

                    if state == self.state_on:
                        power_mode = PowerMode.ON
                    elif state == self.state_off:
                        power_mode = PowerMode.OFF
                    else:
                        power_mode = PowerMode.UNKNOWN

                except IndexError:
                    power_mode = PowerMode.UNKNOWN

                if power_mode != self.outlets[outlet_idx].power_mode:
                    raise AssertionError(
                        f"Power mode of outlet ID {outlet} ({power_mode})"
                        f" is different than the expected mode {self.outlets[outlet_idx].power_mode}"
                    )
                return power_mode
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return PowerMode.UNKNOWN
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return PowerMode.UNKNOWN

    def turn_on_outlet(
        self: DLIProSwitchDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn on a specific outlet.

        :param outlet: outlet ID to turn on
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """
        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        url = self.outlet_control_url.replace("REPLACE_OUTLET", outlet)
        data = self.turn_on_action
        outlet_idx = self.outlet_id_list.index(outlet)

        try:
            response = requests.patch(
                url=url,
                verify=False,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                self.outlets[outlet_idx].power_mode = PowerMode.ON
                return ResultCode.OK, f"Outlet {outlet} power on"
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return ResultCode.FAILED, "HTTP response error"
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"

    def turn_off_outlet(
        self: DLIProSwitchDriver, outlet: str
    ) -> tuple[ResultCode, str]:
        """
        Tell the DLI power switch to turn off a specific outlet.

        :param outlet: outlet ID to turn off
        :return: a tuple containing a return code and a string
                 message indicating status

        :raise AssertionError: if outlet ID is out of bounds
        """

        assert (
            outlet in self.outlet_id_list
        ), f"Outlet ID {outlet} must be in the allowable outlet_id_list"

        url = self.outlet_control_url.replace("REPLACE_OUTLET", outlet)
        data = self.turn_off_action
        outlet_idx = self.outlet_id_list.index(outlet)

        try:
            response = requests.patch(
                url=url,
                verify=False,
                data=data,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code in [
                requests.codes.ok,
                requests.codes.no_content,
            ]:
                self.outlets[outlet_idx].power_mode = PowerMode.OFF
                return ResultCode.OK, f"Outlet {outlet} power off"
            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return ResultCode.FAILED, "HTTP response error"
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return ResultCode.FAILED, "Connection error"

    def get_outlet_list(self: DLIProSwitchDriver) -> List(Outlet):
        """
        Query the power switch for a list of outlets and get their name
        and current state.

        :return: list of all the outlets available in this power switch,
                 or an empty list if there was an error
        """

        url = self.outlet_list_url

        try:
            response = requests.get(
                url=url,
                verify=False,
                headers=self.header,
                auth=(self.login, self.password),
                timeout=self.query_timeout_s,
            )

            if response.status_code == requests.codes.ok:
                # Extract the outlet list
                outlets: List(Outlet) = []
                resp_list = response.json()

                for idx, resp_dict in enumerate(resp_list):
                    try:
                        state = str(resp_dict["state"])

                        if state == self.state_on:
                            power_mode = PowerMode.ON
                        elif state == self.state_off:
                            power_mode = PowerMode.OFF
                        else:
                            power_mode = PowerMode.UNKNOWN

                    except IndexError:
                        power_mode = PowerMode.UNKNOWN

                    outlets.append(
                        Outlet(
                            outlet_ID=str(idx),
                            outlet_name=resp_dict["name"],
                            power_mode=power_mode,
                        )
                    )
                return outlets

            else:
                self.logger.error(
                    f"HTTP response error: {response.status_code}"
                )
                return []

        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ):
            self.logger.error("Failed to connect to power switch")
            return []