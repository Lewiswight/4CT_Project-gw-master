# File: robust_xserial_term.py
# Desc: Sample driver implimenting a poll-response at an Xbee serial adapter

############################################################################
#                                                                          #
# Copyright (c)2008-2012, Digi International (Digi). All Rights Reserved.  #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,  and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. Contact Product Management, Digi International, Inc., 11001 Bren   #
# Road East, Minnetonka, MN, +1 952-912-3444, for commercial licensing     #
# opportunities for non-Digi products.                                     #
#                                                                          #
# DIGI SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED   #
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A          #
# PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, #
# PROVIDED HEREUNDER IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND. #
# DIGI HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,         #
# ENHANCEMENTS, OR MODIFICATIONS.                                          #
#                                                                          #
# IN NO EVENT SHALL DIGI BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,      #
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,   #
# ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF   #
# DIGI HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.                #
#                                                                          #
############################################################################

"""\
Dia XBee Serial Terminal Driver

To Use:

        Issue web services channel_set call to send data to serial device
                 <data><channel_set name="serial-name.serialSend" value="string to send"/></data>

        Issue web services channel_get (or channel_dump) call to read serial device
                 <data><channel_get name="serial-name.serialReceive"/></data>
                 or
                 <data><channel_dump/></data>

"""

# imports
from settings.settings_base import SettingsBase
from channels.channel_source_device_property import *
from samples.sample import Sample

from core.tracing import get_tracer
from devices.vendors.robust.robust_xserial import RobustXSerial

# constants

# exception classes

# interface functions


# classes
class XBeeSerialTerminal(RobustXSerial):
    """\
        This class extends one of our base classes and is intended as an
        example of a concrete, example implementation, but it is not itself
        meant to be included as part of our developer API. Please consult the
        base class documentation for the API and the source code for this file
        for an example implementation.

    """
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        self.__tracer = get_tracer(name)

        ## Local State Variables:
        self.__xbee_manager = None

        # over-ride base-class defaults
        self.XSER_DEFAULT_TYPE = '232'
        self.XSER_IS_ASCII = True

        ## Settings Table Definition:
        settings_list = [

        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="read", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="write", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.serial_write),
        ]

        ## Initialize the XBeeSerial interface:
        RobustXSerial.__init__(self, self.__name, self.__core,
                                settings_list, property_list)


    ## Functions which must be implemented to conform to the XBeeSerial
    ## interface:

    def next_poll(self, trns_id=0):
        msg = "%s Poll #%d " % (self.get_name(), trns_id)
        # self._tracer.debug(msg)
        self.serial_write(msg)
        self.cancel_response_timeout()
        return

    def read_callback(self, buf, addr=None):
        self.serial_read(buf)


    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    # def start(self):
    # def stop(self):

    ## Locally defined functions:

    def serial_read(self, buf):
        # Update channel
        self.property_set("read", Sample(0, value=buf, unit=""))

    def serial_write(self, data):
        if isinstance(data, Sample):
            data = data.value
        # else send as string
        try:
            ret = self.write(data)
            if ret == False:
                raise Exception, "write failed"
        except:
            self.__tracer.warning("Error writing data: %s", data)

# internal functions & classes
