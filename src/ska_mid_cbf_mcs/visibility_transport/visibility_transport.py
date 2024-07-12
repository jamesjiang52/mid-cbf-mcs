"""
The Visibility Transport class controls the HPS device servers responsible for
routing the visibilties from FSPs to SDP.

It is assumed that TalonDX boards will only be used in Mid-CBF up to AA1,
supporting up to 8 boards.
"""
import logging

from tango import DevFailed, Except

from ska_tango_testing import context
from ska_mid_cbf_mcs.slim.slim_config import SlimConfig


class VisibilityTransport:
    # number of fine channels in a output stream. Each FSP has 744 channel groups,
    # so 744 * 20 = 14880 fine channels.
    CHANNELS_PER_STREAM = 20

    def __init__(self, logger: logging.Logger):
        """
        Constructor

        :param logger: the logger object
        """
        self.logger = logger

        # Tango device proxies
        self._host_lut_s1_fqdns = []
        self._host_lut_s2_fqdn = None
        self._spead_desc_fqdns = None
        self._dp_host_lut_s1 = []
        self._dp_host_lut_s2 = None
        self._dp_spead_desc = None

        self._channel_offsets = []
        self._fsp_config = None

    def configure(self, fsp_config: list, vis_slim_yaml: str) -> None:
        """
        Configure the visibility transport devices.
        - determine which board is responsible for outputting visibilities
        - connect the host lut s1 devices to the host lut s2
        - write the channel offsets of each FSP to host lut s2
        - configure all the spead descriptor DS's

        :param fsp_config: FSP part of the scan configuration json object
        :param vis_slim_yaml: the visibility mesh config yaml
        :param board_to_fsp_id: a dict to convert talon board str to fsp ID
        """
        self.logger.info("Configuring visibility transport devices")

        self._fsp_ids = [fc["fsp_id"] for fc in fsp_config]
        self._channel_offsets = [fc["channel_offset"] for fc in fsp_config]

        if len(self._channel_offsets) == 0:
            self._channel_offsets = [0]

        self.logger.info(
            f"FSP IDs = {self._fsp_ids}, channel_offsets = {self._channel_offsets}"
        )

        # Parse the visibility SLIM yaml to determine which board will output
        # visibilities.
        vis_out_map = self._get_vis_output_map(vis_slim_yaml)

        try:
            self._create_device_proxies(vis_out_map)

            # connect the host lut s1 devices to the host lut s2
            for s1_dp, ch_offset in zip(
                self._dp_host_lut_s1, self._channel_offsets
            ):
                self.logger.info(
                    f"Connecting to {self._host_lut_s2_fqdn} with channel offset {ch_offset}"
                )
                s1_dp.host_lut_stage_2_device_name = self._host_lut_s2_fqdn
                s1_dp.channel_offset = ch_offset
                s1_dp.connectToHostLUTStage2()

            # write the channel offsets of each FSP to host lut s2
            self._dp_host_lut_s2.host_lut_s1_chan_offsets = (
                self._channel_offsets
            )
        except DevFailed as df:
            msg = str(df.args[0].desc)
            self.logger.error(
                f"Failed to configure visibility transport devices: {msg}"
            )

        self._fsp_config = fsp_config

    def enable_output(
        self,
        subarray_id: int,
    ) -> None:
        """
        Enable the output of visibilities. This should be called after
        the FSP App on HPS has finished the scan command. This function does
        the following.
        - start sending SPEAD descriptors
        - program the host lut s2 device
        - program all the host lut s1 devices

        :param fsp_config: FSP part of the scan configuration json object
        :param n_vcc: number of receptors
        :param scan_id: the scan ID
        """
        self.logger.info("Enable visibility output")

        dest_host_data = self._parse_visibility_transport_info(
            subarray_id, self._fsp_config
        )

        try:
            # FSP App is responsible for calling the "Configure" command.
            # If not already called, StartScan will fail.
            self._dp_spead_desc.command_inout("StartScan", dest_host_data)

            self._dp_host_lut_s2.command_inout("Program", dest_host_data)

            for dp in self._dp_host_lut_s1:
                dp.command_inout("Program")
        except DevFailed as df:
            msg = str(df.args[0].desc)
            self.logger.error(
                f"Failed to configure visibility transport devices: {msg}"
            )

    def disable_output(self):
        """
        Disable the output of visibilities
        - Issue EndScan command to SPEAD Descriptor DS
        - Unprogram all the host lut s1 devices
        - Unprogram the host lut s2 device
        """
        self.logger.info("Disable visibility output")

        try:
            self._dp_spead_desc.command_inout("EndScan")
            for dp in self._dp_host_lut_s1:
                dp.command_inout("Unprogram")
            self._dp_host_lut_s2.command_inout("Unprogram")
        except DevFailed as df:
            msg = str(df.args[0].desc)
            self.logger.error(
                f"Failed to configure visibility transport devices: {msg}"
            )

    def _parse_visibility_transport_info(
        self, subarray_id: int, fsp_config: list
    ):
        """
        output_hosts are in format [[channel_id, ip_addr]]
        output_ports are in format [[channel_id, port]]

        Need to match the two by channel_id to get a list of [[ip_addr, port]]

        :return: a list of [subarray, channel_id, ip_addr, port] as 1D array
        """
        out = []

        # Merge the output hosts and ports from FSP entries to one
        output_hosts = []
        output_ports = []
        for fsp in fsp_config:
            # the channel IDs are relative to the channel offset of the FSP entry
            if (
                "channel_offset" in fsp
                and "output_host" in fsp
                and "output_port" in fsp
            ):
                output_hosts += [
                    [h[0] + fsp["channel_offset"], h[1]]
                    for h in fsp["output_host"]
                ]
                output_ports += [
                    [p[0] + fsp["channel_offset"], p[1]]
                    for p in fsp["output_port"]
                ]

        next_host_idx = 1
        host_int = self._ip_to_int(output_hosts[0][1])
        for p in output_ports:
            if (
                next_host_idx < len(output_hosts)
                and output_hosts[next_host_idx][0] == p[0]
            ):
                host_int = self._ip_to_int(output_hosts[next_host_idx][1])
                next_host_idx += 1

            dest_info = [subarray_id, p[0], host_int, p[1]]
            out += dest_info
        return out

    def _ip_to_int(self, inet: str) -> int:
        return sum(
            [
                int(v) << (i * 8)
                for i, v in enumerate(reversed(inet.split(".")))
            ]
        )

    def _create_device_proxies(self, vis_out_map: dict) -> None:
        """
        Create Tango device proxies for the HPS device servers
        used for outputting data for this subarray

        :param vis_out_map: dict mapping fsp_id to the board responsible
                            for sending visibilities to SDP
        """
        vis_out_board = None
        for fsp in self._fsp_ids:
            if fsp in vis_out_map:
                # Only one board is expected to be used to output visibilities
                # to SDP
                if (
                    vis_out_board is not None
                    and vis_out_map[fsp] != vis_out_board
                ):
                    Except.throw_exception(
                        "Visibility_Transport",
                        "Only one board can be used to output visibilities",
                        "configure()",
                    )
                vis_out_board = vis_out_map[fsp]

        if vis_out_board is None:
            # this happens when visibility mesh is not used. Only
            # 1 FSP is supported in this case.
            vis_out_board = f"talondx-00{self._fsp_ids[0]}"

        self._host_lut_s1_fqdns = [
            f"talondx-00{id}/dshostlutstage1/host_lut_s1"
            for id in self._fsp_ids
        ]
        self._host_lut_s2_fqdn = f"{vis_out_board}/dshostlutstage2/host_lut_s2"
        self._spead_desc_fqdn = f"{vis_out_board}/dsspeaddescriptor/spead"

        # Create device proxies
        self._dp_host_lut_s1 = [
            context.DeviceProxy(device_name=f)
            for f in self._host_lut_s1_fqdns
        ]
        self._dp_host_lut_s2 = context.DeviceProxy(
            device_name=self._host_lut_s2_fqdn
        )
        self._dp_spead_desc = context.DeviceProxy(
            device_name=self._spead_desc_fqdn
        )

    def _get_vis_output_map(self, vis_slim_yaml: str) -> dict:
        """
        Determine which board does each FSP output route to.

        :return: a dict with fsp_id as key. The value is the TalonDX board
                 ("talondx-00x") that will output visibilities.
        :raise TangoException: if configuration is not valid
        """
        slim_cfg = SlimConfig(vis_slim_yaml, self.logger)
        active_links = slim_cfg.active_links()
        vis_out_map = {}
        for link in active_links:
            tx = link[0].split("/")[0]  # extract the "talondx-00x" part
            tx_num = int(tx[-3:])
            rx = link[1].split("/")[0]
            vis_out_map[tx_num] = rx
        return vis_out_map
