"""File to configure the serial port location of the XBee connected to this device.
This file does not need to be uploaded to a ConnectPort."""

import zigbee
import serial

#zigbee.default_xbee.serial = serial.Serial("COM1", 115200, rtscts = 0)
zigbee.default_xbee.serial = serial.Serial("COM13", 115200, rtscts = 0)
#zigbee.default_xbee.serial = serial.Serial("COM22", 115200, rtscts = 0)

# set AO = 1, get full explicit messages
zigbee.ddo_set_param(None, "AO", chr(1))
