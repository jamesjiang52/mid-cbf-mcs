# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for modifying gain"""

from __future__ import annotations  # allow forward references in type hints

import json
import logging

import numpy
import scipy
import yaml

from ska_mid_cbf_mcs.commons.global_enum import const

VCC_PARAM_PATH = "mnt/vcc_param/"

class GAINUtils:
    """
    Utilities for modifying and correcting the vcc gain.
    """

    def __init__(self: GAINUtils) -> None:
        """
        Initialize a new instance.

        :param mapping: todo
        """

    @staticmethod
    def get_vcc_ripple_correction(
        logger: logging.Logger,
    ) -> dict:
        """
        Applies VCC Gain ripple correction to a dictionary of gains

        :return: dictionary of new gain values
        """

        vcc_gain_corrections = []
        # The below source code was based off talon_FSP.py:vcc_gain_corrections
        # from ska-mid-cbf-signal-verification
        logger.info(f"About to open file")
        with open(
                    f"{VCC_PARAM_PATH}OS_Prototype_FIR_CH20.yml", "r"
                ) as file:
                    vcc_fir_prototype = yaml.safe_load(file)

        fir_proto = vcc_fir_prototype["h"]
        json_string = json.dumps(fir_proto)
        logger.info(f"file opened: {json_string}")
        # TODO how to get vcc frequency slice?
        vcc_frequency_slice = None

        if vcc_frequency_slice is None:
            return {chan: 1.0 for chan in range(16384)}

        frequency_slice_sample_rate = (
            const.INPUT_SAMPLE_RATE // const.INPUT_FRAME_SIZE
        )

        # The Normalized Center Frequencies of the Secondry Channelizer
        fc0 = numpy.linspace(
            -1, 1 - 2 / const.FINE_CHANNELS, num=const.FINE_CHANNELS
        )

        # Assuming Frequency Shifting is Applied in the ReSampler
        scf0_fsft = (vcc_frequency_slice + 1) * (
            frequency_slice_sample_rate - const.COMMON_SAMPLE_RATE
        )

        # The Actual Center Frequencies of the Secondry Channelizer
        actual_center_frequency = (
            fc0 * const.COMMON_SAMPLE_RATE / 2 - scf0_fsft
        )
        # Converting again to Normalized Frequencies
        normalized_frequency = (
            actual_center_frequency
            / frequency_slice_sample_rate
            / const.INPUT_FRAME_SIZE
        )

        # Evaluating the Gain of the Frequency response of the VCC Channelizer
        _, h = scipy.signal.freqz(
            fir_proto, a=1, worN=2 * numpy.pi * normalized_frequency
        )

        # The Gain Correction Factors
        gc_vec = numpy.clip(
            0.99 / abs(h), 0, 1
        )  # NOTE: The 0.99 factor avoids the saturation of gain correction factors

        # Initiating the Gain Correction Dictionary
        # chan = (np.arange(0,16383, dtype=int) + 8192) % 16384
        channels = numpy.arange(0, 16383, dtype=int)
        vcc_gain_corrections = dict(zip(channels, gc_vec))

        return vcc_gain_corrections
