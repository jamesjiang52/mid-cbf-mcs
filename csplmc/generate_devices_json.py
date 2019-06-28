with open("devices.json", "w+") as f:
    string = "[\n"

    fqdn_vcc = [*map(lambda j: "\"mid_csp_cbf/vcc/{:03d}\"".format(j), range(1, 199))]
    fqdn_fsp = [*map(lambda j: "\"mid_csp_cbf/fsp/{:02d}\"".format(j), range(1, 28))]
    fqdn_cbf_subarray = [*map(lambda j: "\"mid_csp_cbf/sub_elt/subarray_{:02d}\"".format(j), range(1, 17))]
    string_vcc = "\n                    " + \
                 ",\n                    ".join(fqdn_vcc) + \
                 "\n                "
    string_fsp = "\n                    " + \
                 ",\n                    ".join(fqdn_fsp) + \
                 "\n                "
    string_cbf_subarray = "\n                    " + \
                          ",\n                    ".join(fqdn_cbf_subarray) + \
                          "\n                "

    # Generate CBF Master
    string += "    {{\n" \
              "        \"class\": \"CbfMaster\",\n" \
              "        \"serverName\": \"CbfMaster/master\",\n" \
              "        \"devName\": \"mid_csp_cbf/sub_elt/master\",\n" \
              "        \"deviceProperties\": [\n" \
              "            {{\n" \
              "                \"devPropName\": \"MaxCapabilities\",\n" \
              "                \"devPropValue\": [\"VCC:197\", \"FSP:27\", \"Subarray:16\"]\n" \
              "            }},\n" \
              "            {{\n" \
              "                \"devPropName\": \"VCC\",\n" \
              "                \"devPropValue\": [{0}]\n" \
              "            }},\n" \
              "            {{\n" \
              "                \"devPropName\": \"FSP\",\n" \
              "                \"devPropValue\": [{1}]\n" \
              "            }},\n" \
              "            {{\n" \
              "                \"devPropName\": \"CbfSubarray\",\n" \
              "                \"devPropValue\": [{2}]\n" \
              "            }}\n" \
              "        ],\n" \
              "        \"attributeProperties\": [\n" \
              "            {{\n" \
              "                \"attributeName\": \"adminMode\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"changeEventAbs\": \"1\"\n" \
              "            }},\n" \
              "            {{\n" \
              "                \"attributeName\": \"healthState\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"changeEventAbs\": \"1\"\n" \
              "            }},\n" \
              "            {{\n" \
              "                \"attributeName\": \"State\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"changeEventAbs\": \"\"\n" \
              "            }}\n" \
              "        ]\n" \
              "    }},\n".format(string_vcc, string_fsp, string_cbf_subarray)

    # Generate TM TelState test device
    string += "    {\n" \
              "        \"class\": \"TmTelstateTest\",\n" \
              "        \"serverName\": \"TmTelstateTest/tm\",\n" \
              "        \"devName\": \"ska1_mid/tm/telmodel\",\n" \
              "        \"deviceProperties\": [],\n" \
              "        \"attributeProperties\": [\n" \
              "            {\n" \
              "                \"attributeName\": \"delayModel\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"periodicEventCadence\": \"10000\",\n" \
              "                \"changeEventAbs\": \"1\"\n" \
              "            },\n" \
              "            {\n" \
              "                \"attributeName\": \"visDestinationAddress\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"periodicEventCadence\": \"10000\",\n" \
              "                \"changeEventAbs\": \"1\"\n" \
              "            },\n" \
              "            {\n" \
              "                \"attributeName\": \"dopplerPhaseCorrection_1\",\n" \
              "                \"attrPropName\": \"\",\n" \
              "                \"attrPropValue\": \"\",\n" \
              "                \"pollingPeriod\": 1000,\n" \
              "                \"periodicEventCadence\": \"10000\",\n" \
              "                \"changeEventAbs\": \"1\"\n" \
              "            }\n" \
              "        ]\n" \
              "    },\n"

    # Generate CBF Subarrays
    for i in range(1, 17):
        fqdn_fsp_subarray = [*map(lambda j: "\"mid_csp_cbf/fspSubarray/{0:02d}_{1:02d}\"".format(j, i), range(1, 28))]
        string_fsp_subarray = "\n                    " + \
                              ",\n                    ".join(fqdn_fsp_subarray) + \
                              "\n                "
        string += "    {{\n" \
                  "        \"class\": \"CbfSubarray\",\n" \
                  "        \"serverName\": \"CbfSubarray/cbfSubarray-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/sub_elt/subarray_{0:02d}\",\n" \
                  "        \"deviceProperties\": [\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"SubID\",\n" \
                  "                \"devPropValue\": {0}\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"CbfMasterAddress\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/sub_elt/master\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"SW1Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/sw1/{0:02d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"SW2Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/sw2/{0:02d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"VCC\",\n" \
                  "                \"devPropValue\": [{1}]\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"FSP\",\n" \
                  "                \"devPropValue\": [{2}]\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"FspSubarray\",\n" \
                  "                \"devPropValue\": [{3}]\n" \
                  "            }}\n" \
                  "        ],\n" \
                  "        \"attributeProperties\": [\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"adminMode\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"healthState\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"State\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"scanID\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }}\n" \
                  "        ]\n" \
                  "    }},\n".format(i, string_vcc, string_fsp, string_fsp_subarray)

    # Generate VCCs
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"Vcc\",\n" \
                  "        \"serverName\": \"Vcc/vcc\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc/{0:03d}\",\n" \
                  "        \"deviceProperties\": [\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"VccID\",\n" \
                  "                \"devPropValue\": {0}\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"Band1And2Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_band12/{0:03d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"Band3Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_band3/{0:03d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"Band4Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_band4/{0:03d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"Band5Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_band5/{0:03d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"SW1Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_sw1/{0:03d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"SW2Address\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/vcc_sw2/{0:03d}\"\n" \
                  "            }}\n" \
                  "        ],\n" \
                  "        \"attributeProperties\": [\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"adminMode\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"healthState\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"State\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"subarrayMembership\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }}\n" \
                  "        ]\n" \
                  "    }},\n".format(i)

    # Generate FSPs
    for i in range(1, 28):
        string += "    {{\n" \
                  "        \"class\": \"Fsp\",\n" \
                  "        \"serverName\": \"Fsp/fsp-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/fsp/{0:02d}\",\n" \
                  "        \"deviceProperties\": [\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"FspID\",\n" \
                  "                \"devPropValue\": {0}\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"CorrelationAddress\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/fsp_corr/{0:02d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"PSSAddress\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/fsp_pss/{0:02d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"PSTAddress\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/fsp_pst/{0:02d}\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"devPropName\": \"VLBIAddress\",\n" \
                  "                \"devPropValue\": \"mid_csp_cbf/fsp_vlbi/{0:02d}\"\n" \
                  "            }}\n" \
                  "        ],\n" \
                  "        \"attributeProperties\": [\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"adminMode\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"healthState\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"State\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"\"\n" \
                  "            }},\n" \
                  "            {{\n" \
                  "                \"attributeName\": \"subarrayMembership\",\n" \
                  "                \"attrPropName\": \"\",\n" \
                  "                \"attrPropValue\": \"\",\n" \
                  "                \"pollingPeriod\": 1000,\n" \
                  "                \"changeEventAbs\": \"1\"\n" \
                  "            }}\n" \
                  "        ]\n" \
                  "    }},\n".format(i)

    # Generate CBF Subarray search windows (2 for each CBF Subarray)
    for i in range(1, 17):
        string += "    {{\n" \
                  "        \"class\": \"SearchWindow\",\n" \
                  "        \"serverName\": \"SearchWindow/sw1-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/sw1/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)
        string += "    {{\n" \
                  "        \"class\": \"SearchWindow\",\n" \
                  "        \"serverName\": \"SearchWindow/sw2-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/sw2/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate VCC band 1 and 2 Capabilities (for each VCC)
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"VccBand1And2\",\n" \
                  "        \"serverName\": \"VccBand1And2/vcc\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_band12/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate VCC band 3 Capabilities (for each VCC)
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"VccBand3\",\n" \
                  "        \"serverName\": \"VccBand3/vcc\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_band3/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate VCC band 4 Capabilities (for each VCC)
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"VccBand4\",\n" \
                  "        \"serverName\": \"VccBand4/vcc\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_band4/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate VCC band 5 Capabilities (for each VCC)
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"VccBand5\",\n" \
                  "        \"serverName\": \"VccBand5/vcc\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_band5/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate VCC search windows (2 for each VCC)
    for i in range(1, 198):
        string += "    {{\n" \
                  "        \"class\": \"VccSearchWindow\",\n" \
                  "        \"serverName\": \"VccSearchWindow/vcc-sw1\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_sw1/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)
        string += "    {{\n" \
                  "        \"class\": \"VccSearchWindow\",\n" \
                  "        \"serverName\": \"VccSearchWindow/vcc-sw2\",\n" \
                  "        \"devName\": \"mid_csp_cbf/vcc_sw2/{0:03d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate FSP correlation Capabilities (for each FSP)
    for i in range(1, 28):
        string += "    {{\n" \
                  "        \"class\": \"FspCorr\",\n" \
                  "        \"serverName\": \"FspCorr/fsp-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/fsp_corr/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate FSP PSS Capabilities (for each FSP)
    for i in range(1, 28):
        string += "    {{\n" \
                  "        \"class\": \"FspPss\",\n" \
                  "        \"serverName\": \"FspPss/fsp-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/fsp_pss/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate FSP PST Capabilities (for each FSP)
    for i in range(1, 28):
        string += "    {{\n" \
                  "        \"class\": \"FspPst\",\n" \
                  "        \"serverName\": \"FspPst/fsp-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/fsp_pst/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate FSP VLBI Capabilities (for each FSP)
    for i in range(1, 28):
        string += "    {{\n" \
                  "        \"class\": \"FspVlbi\",\n" \
                  "        \"serverName\": \"FspVlbi/fsp-{0:02d}\",\n" \
                  "        \"devName\": \"mid_csp_cbf/fsp_vlbi/{0:02d}\",\n" \
                  "        \"deviceProperties\": []\n" \
                  "    }},\n".format(i)

    # Generate FSP Subarrays
    for i in range(1, 28):
        for j in range(1, 17):
            string += "    {{\n" \
                      "        \"class\": \"FspSubarray\",\n" \
                      "        \"serverName\": \"FspSubarray/fspSubarray-{0:02d}-{1:02d}\",\n" \
                      "        \"devName\": \"mid_csp_cbf/fspSubarray/{0:02d}_{1:02d}\",\n" \
                      "        \"deviceProperties\": [\n" \
                      "            {{\n" \
                      "                \"devPropName\": \"SubID\",\n" \
                      "                \"devPropValue\": {1}\n" \
                      "            }},\n" \
                      "            {{\n" \
                      "                \"devPropName\": \"FspID\",\n" \
                      "                \"devPropValue\": {0}\n" \
                      "            }},\n" \
                      "            {{\n" \
                      "                \"devPropName\": \"VCC\",\n" \
                      "                \"devPropValue\": [{2}]\n" \
                      "            }},\n" \
                      "            {{\n" \
                      "                \"devPropName\": \"CbfMasterAddress\",\n" \
                      "                \"devPropValue\": \"mid_csp_cbf/sub_elt/master\"\n" \
                      "            }},\n" \
                      "            {{\n" \
                      "                \"devPropName\": \"CbfSubarrayAddress\",\n" \
                      "                \"devPropValue\": \"mid_csp_cbf/sub_elt/subarray_{1:02d}\"\n" \
                      "            }}\n" \
                      "        ]\n" \
                      "    }},\n".format(i, j, string_vcc)

    string = string[:-2] + "\n]"
    f.write(string)
