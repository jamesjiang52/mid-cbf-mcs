from inspect import cleandoc

configurescan_validation_rules_data = {
    "headers": [
        "Scan Configuration Parameter",
        "AA4 Ranges (see TM)",
        "Supported",
        "Comment"
    ], 
    "data": [
        {
            "Scan Configuration Parameter": "band_5_tuning",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "channel_count",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": cleandoc(
                """
                Range: Integer from 1 to 58982 inclusive
                
                Checks:
                
                * Must be a multiple of 20
                
                """
                ),
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "channel_width",
            "AA4 Ranges (see TM)": "See TM for enum",
            "Supported": "Integer of exactly 13440",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "frequency_band",
            "AA4 Ranges (see TM)": "Strings of values: 1, 2, 5a, 5b",
            "Supported": "Strings of values: 1, 2",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "frequency_band_offset_stream1",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "frequency_band_offset_stream2",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "fsp_id",
            "AA4 Ranges (see TM)": "Integer from 1 to 27 inclusive",
            "Supported": cleandoc(
                """
                Checks:
                
                * if ``CORR``: Integer from 1 to 4 inclusive
                """
                ),
            "Comment": "``PST``: 5 - 8 when implemented",
        },
        {
            "Scan Configuration Parameter": "fsp_ids",
            "AA4 Ranges (see TM)": "Array of 1 to 26 ``fsp_id``",
            "Supported": "Array of 1 to 4 ``fsp_id``",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "integration_factor",
            "AA4 Ranges (see TM)": "Integer from 1 - 10 inclusive",
            "Supported": "Integer from 1 - 10 inclusive",
            "Comment": "No additional checks needed",
        },
        {
            "Scan Configuration Parameter": "output_link_map",
            "AA4 Ranges (see TM)": cleandoc(
                """
                Ranges: See TM
                
                Checks:
                
                * First entry ``start_channel_id`` must match the ``sdp_start_channel_id``
                
                """),
            "Supported": "[[``sdp_start_channel_id``, 1]]",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "output_port",
            "AA4 Ranges (see TM)": cleandoc(
                """
                Ranges: See TM
                
                Checks:
                
                * First entry ``start_channel_id`` must match the ``sdp_start_channel_id``

                """),
            "Supported": cleandoc(
                """
                In addition to AA4 ranges:
                
                * ``start_channel_id``'s must be in ascending order
                
                * ``start_channel_id``'s must be multiples of 20
                
                * At most 20 chanels can be sent to the same port per host

                """),
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "receptors",
            "AA4 Ranges (see TM)": "all SKA and MKT",
            "Supported": "all",
            "Comment": "No additional checks needed",
        },
        {
            "Scan Configuration Parameter": "rfi_flagging_mask",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "sdp_start_channel_id",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "Same as TM",
            "Comment": "No additional checks needed",
        },
        {
            "Scan Configuration Parameter": "search_window",
            "AA4 Ranges (see TM)": "",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "start_freq",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported":  cleandoc(
                """
                Checks:

                * Entire processing region must fall inside specified band
                
                * Required bandwidth [``start_freq`` - (1/2 * ``start_freq``) +
                (``channel_width`` * ``channel_count``)] must not require more
                FSP's than provided in ``fsp_ids``

                """),
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "subarray_id",
            "AA4 Ranges (see TM)": "Integer from 1 to 16 inclusive",
            "Supported": "Integer of value 1",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "vlbi",
            "AA4 Ranges (see TM)": "",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
    ]
}
