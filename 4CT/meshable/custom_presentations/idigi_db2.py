############################################################################
#                                                                          #
# Copyright (c)2008, 2009 Digi International (Digi). All Rights Reserved.  #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its	   #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,	and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. Contact Product Management, Digi International, Inc., 11001 Bren   #
# Road East, Minnetonka, MN, +1 952-912-3444, for commercial licensing	   #
# opportunities for non-Digi products.                                     #
#                                                                          #
# DIGI SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED   #
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A          #
# PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, #
# PROVIDED HEREUNDER IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND. #
# DIGI HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,         #
# ENHANCEMENTS, OR MODIFICATIONS.                                          #
#                                                                          #
# IN NO EVENT SHALL DIGI BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,	   #
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,   #
# ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF   #
# DIGI HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.                #
#                                                                          #
############################################################################

"""\
iDigi.Com Database Synchronization Module

--THIS MODULE WILL NOT FUNCTION EXCEPT ON DIGI DEVICES--

.. Note::
    This tool requires the Digi idigi_data module.
    idigi_data should be placed on your device in the python section.

Sample Config::

  - name: idigi_db1
    driver: presentations.idigi_db.idigi_db:iDigi_DB
    settings:
        interval: 60
        sample_threshold: 10
        collection: my_collection
        file_count: 10
        filename: sample
        channels: [template.counter, template.adder_reg1]

##########################################################################

This presentation allows for the iDigi Dia to utilize the iDigi.Com Storage
service to store sample information.

Whenever the specified interval of time has expired, or the number of new
samples exceeds the sample_threshold, this presentation pushes up channel
information to iDigi.  It retrieves a list of all channels, and pushes
up any that have had new samples since the last push to iDigi.

In order to provide the most efficient operation possible for this
presentation, we offer a filter on the channels you wish to subscribe to.
Omitting the channels setting causes this presentation to listen on all
channels, but it is recommended to specify the channels you are interested
in if possible.

* **interval** is the maximum inveral in seconds that this module waits before
  sending data to the iDigi Manager Database.

* **sample_threshold** is the mininum number of samples required before
  sending data to the iDigi Manager Database.

* **collection** is the collection on the database where the data will
  be stored

* **file_count** is the number of unique files we will keep on iDigi.

* **filename** is the name of the xml file we will push to iDigi, with
  a number appended to the end (cycling from 1 to file_count)

* **channels** is the list of channels the module is subscribed to.
  If no channels are listed, all channels are subscribed to.

* **compact_xml** (when set to True) will produce output XML with the 
  information stored as attributes to the sample node instead of
  separately tagged, resulting in smaller XML output.

"""

# imports
import sys
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from samples.sample import Sample
from common.helpers.format_channels import iso_date

import threading
import time
import idigi_data
import Queue
import cStringIO


# constants
ENTITY_MAP = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
}

# exception classes

# interface functions

# classes
class iDigi_DB(PresentationBase, threading.Thread):
    def __init__(self, name, core_services):
	self.__name = name
	self.__core = core_services

	settings_list = [
	    Setting(
		name='interval', type=int, required=False, default_value=60),
	    Setting(
		name='sample_threshold', type=int, required=False, default_value=10),
	    Setting(
		name='collection', type=str, required=False, default_value=""),
	    Setting(
		name="channels", type=list, required=False, default_value=[]),
	    Setting(
		name='file_count', type=int, required=False, default_value=20),
	    Setting(
		name='filename', type=str, required=False, default_value="sample"),
	    Setting(
		name='secure', type=bool, required=False, default_value=True),
		Setting(
		name='compact_xml', type=bool, required=False, default_value=False),
	]

	PresentationBase.__init__(self, name=name,
                                  settings_list=settings_list)
	self.__stopevent = threading.Event()
	threading.Thread.__init__(self, name=name)
	threading.Thread.setDaemon(self, True)

    def start(self):
        """Start the iDigi data instance.	 Returns bool."""

        # Start by appending 1 to filename of pushed data
        self.__current_file_number = 1

        # Event to use for notification of meeting the sample threshold
        self.__threshold_event = threading.Event()

        # Count of samples since last data push
        self.__sample_count = 0

        # Here we grab the channel publisher
        channels = SettingsBase.get_setting(self, "channels")
        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()

        # And subscribe to receive notification about new samples
        if len(channels) > 0:
            for channel in channels:
                cp.subscribe(channel, self.receive)
        else:
            cp.subscribe_to_all(self.receive)

        threading.Thread.start(self)
        self.apply_settings()
        return True


    def stop(self):
        """Stop the iDigi data instance.	Returns bool."""
        self.__stopevent.set()
        return True

    def apply_settings(self):
        """Commits the settings to the Settings Base"""
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        SettingsBase.commit_settings(self, accepted)
        return (accepted, rejected, not_found)

    def receive(self, channel):
        """
        Called whenever there is a new sample
        
        Keyword arguments:
        
        channel -- the channel with the new sample
        """
        
        # Check how many samples it takes to meet the sample threshold
        sample_threshold = SettingsBase.get_setting(self, "sample_threshold")
        
        self.__sample_count += 1

#         print "idigi_db: Received sample %i" % self.__sample_count

        # If we have exceeded the sample threshold, notify the thread
        # responsible for pushing up data
        if self.__sample_count >= sample_threshold:
#             print "idigi_db: Reached threshold of %i, setting event flag" % sample_threshold
            self.__threshold_event.set()

    def run(self):
        """
        Uploads data whenever an appropriate threshold is met
        """
        
        interval = SettingsBase.get_setting(self, "interval")
        
        self.__last_upload_time = 0
        while not self.__stopevent.isSet():
            try:
#                 print "idigi_db: I'm waiting for an event or up to %i seconds" % interval
                self.__threshold_event.wait(interval)
#                 print "idigi_db: I'm done waiting"

                self.__sample_count = 0
                self.__threshold_event.clear()
                
                self.__upload_data()
            except Exception, e:
                print "iDigi_DB(%s): exception while uploading: %s" % \
                    (self.__name, str(e))


#         print "idigi_db: Got out of the loop..."

    def __upload_data(self):
        """
        Builds XML string of the channel state and pushes to iDigi
        """
        
        xml = cStringIO.StringIO()
        
        xml.write("<?xml version=\"1.0\"?>")
        compact_xml = SettingsBase.get_setting(self, "compact_xml")    
        if compact_xml:
            xml.write("<idigi_data compact=\"True\">")
        else:
            xml.write("<idigi_data>")
        
#         print "idigi_db: Uploading to iDigi"

        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()
        channel_list = SettingsBase.get_setting(self, "channels")
        
        if len(channel_list) == 0:
            channel_list = cdb.channel_list()

        new_sample_count = 0

        for channel_name in channel_list:
            try:
                channel = cdb.channel_get(channel_name)
                sample = channel.get()
                if sample.timestamp >= self.__last_upload_time:
#                     print "Channel %s was updated since last push" % channel_name
                    new_sample_count += 1
                    compact_xml = SettingsBase.get_setting(self, "compact_xml")    
                    if compact_xml:
                        xml.write(self.__make_compact_xml(channel_name, sample))
                    else:
                        xml.write(self.__make_xml(channel_name, sample))
#                else:
#                     print "Channel %s was not updated since last push" % channel_name
            except:
                # Failed to retrieve the data
                pass

        xml.write("</idigi_data>")

        if new_sample_count > 0:
            self.__last_upload_time = time.time()
            self.__send_to_idigi(xml.getvalue())

        xml.close()

#         print "idigi_db: I uploaded to iDigi"


    def __make_xml(self, channel_name, sample):
        """
        Converts a sample to XML. Returns String
        
        Keyword arguments:
        
        channel_name -- the name of the channel
        sample -- the corresponding sample
        """

        data = "<sample>"
        data += "<name>%s</name>"
        data += "<value>%s</value>"
        data += "<unit>%s</unit>"
        data += "<timestamp>%s</timestamp>"
        data += "</sample>"

        return data % (channel_name, self.__escape_entities(sample.value),
                       sample.unit, iso_date(sample.timestamp))


    def __make_compact_xml(self, channel_name, sample):
        """
        Converts a sample to compact XML (using attributes instead of tags). Returns String
        
        Keyword arguments:
        
        channel_name -- the name of the channel
        sample -- the corresponding sample
        """

        data = "<sample name=\"%s\" value=\"%s\" unit=\"%s\" timestamp=\"%s\" />"

        return data % (channel_name, self.__escape_entities(sample.value),
                       sample.unit, iso_date(sample.timestamp))


    def __send_to_idigi(self, data):
        """
        Sends data to iDigi
        
        Keyword arguments:
        
        data - the XML string to send
        """
        
        filename = SettingsBase.get_setting(self, "filename")    
        filename = filename + "%i.xml" % self.__current_file_number
        collection = SettingsBase.get_setting(self, "collection")    
        secure = SettingsBase.get_setting(self, "secure")    
        success, err, errmsg = idigi_data.send_idigi_data(data, filename, collection, secure)
    
        self.__current_file_number += 1
    
        max_files = SettingsBase.get_setting(self, "file_count")
    
        if self.__current_file_number >= max_files + 1:
            self.__current_file_number = 1


    def __escape_entities(self, sample_value):
        """
            Replace the existing entities of the sample value.
        """

        if not isinstance(sample_value, str):
            return sample_value
        for ch in ENTITY_MAP:
            sample_value = sample_value.replace(ch, ENTITY_MAP[ch])

        return sample_value


