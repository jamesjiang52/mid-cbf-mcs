#!/usr/bin/env python
from tango import AttributeProxy, ChangeEventInfo, AttributeInfoEx, DevFailed
import json
import time

# Update file path to devices.json in order to test locally
# To test on docker environment use path : /app/csplmc/devices.json

with open('/app/csplmc/devices.json', 'r') as file:
    jsonDevices = file.read().replace('\n', '')

# Loading devices.json file and creating an object
json_devices = json.loads(jsonDevices)

# For some reason, this error is occurring:
# Failed to connect to device mid_csp_cbf/sub_elt/master
# The connection request was delayed.
# The last connection request was done less than 1000 ms ago

for device in json_devices:
    deviceName = device["devName"]

    if "attributeProperties" in device:
        for attributeProperty in device["attributeProperties"]:
            attributeProxy = AttributeProxy(deviceName + "/" + attributeProperty["attributeName"])
            print("Device: ", deviceName, " Attribute: ", attributeProperty["attributeName"])
            print("Polling Period: ", attributeProperty["pollingPeriod"])
            if (attributeProperty["pollingPeriod"] != ""):
                attributeProxy.poll(attributeProperty["pollingPeriod"])
            else:
                print("Skip setting polling period...")
            if (attributeProperty["changeEventAbs"] != ""):
                attrInfoEx = attributeProxy.get_config()
                absChange = ChangeEventInfo()
                absChange.abs_change = attributeProperty["changeEventAbs"]
                attrInfoEx.events.ch_event = absChange
                attributeProxy.set_config(attrInfoEx)
            else:
                print("Skip setting change event absolute...")
