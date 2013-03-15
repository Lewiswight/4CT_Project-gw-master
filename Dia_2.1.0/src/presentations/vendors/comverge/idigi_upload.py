############################################################################
#                                                                          #
# Copyright (c)2008-2011 Digi International (Digi). All Rights Reserved.   #
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

* **interval** is obsolete - use clean_minutes_inveral.

* **sample_threshold** is the mininum number of samples required before
  sending data to the iDigi Manager Database.

* **collection** is the collection on the database where the data will
  be stored

* **file_count** is the number of unique files we will keep on iDigi.

* **filename** is the name of the xml file we will push to iDigi, with
  a number appended to the end (cycling from 1 to file_count)

* **filename_format** is a Python string format used to build the name name.
  It defaults to "%s%i.xml" with (filename,filenumber) applied in that order.

* **channels** is the list of channels the module is subscribed to.
  If no channels are listed, all channels are subscribed to.

* **compact_xml** (when set to True) will produce output XML with the
  information stored as attributes to the sample node instead of
  separately tagged, resulting in smaller XML output.

* **cache** is obsolete. Caching is always true in this presentation

* **cache_size** is the maximum bytes contained in the cache.

* **clean_minute_interval** is an alternative to the interval setting.  It
  accepts only minutes in the set (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60)
  It causes upload ON THE HOUR, then minute intervals in a predictable
  pattern. So setting 10 cause uploads at 00:00:00, 00:10:00, 00:20:00 and
  so on. Setting clean_minute_interval to non-zero over-rides the interval
  setting.

"""

# imports
import sys
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from samples.sample import Sample
from common.helpers.format_channels import iso_date

import common.helpers.sleep_aids as sleep_aids

#import common.helpers.string_file as string_file
# use the new one with flash-cache
import string_file

import threading
import time
import idigi_data
import Queue
import cStringIO
import copy
import traceback
import types

# okay if this is not available
try:
    from samples.annotated_sample import *
except:
    pass

# constants
ENTITY_MAP = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
}

# exception classes

# interface functions

# classes
class iDigi_Upload(PresentationBase, threading.Thread):
    CACHE_EXT = '_cache'
    STATS_EXT = '_stats.txt'

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        # local variables
        self.__current_file_number = 1
        self.clear_statistics()
        self.__cache = string_file.string_flash_cache()

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
            Setting(
                name='cache', type=int, required=False, default_value=0),
            Setting(
                name='cache_size', type=int, required=False, default_value=50000),
            Setting(
                name='clean_minute_interval', type=int, required=True,
                default_value=15,
                verify_function=self.__verify_clean_minutes),
            Setting(
                name='clean_minute_skew_secs', type=int, required=False,
                default_value=0),
            Setting(
                name='filename_format', type=str, required=False,
                default_value="%s%i.xml"),
            ]

        PresentationBase.__init__(self, name=name,
                                  settings_list=settings_list)
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)

    def start(self):
        """Start the iDigi data instance.	 Returns bool."""

        # fetch the last stats
        self.load_statistics()

        # Event to use for notification of meeting the sample threshold
        self.__threshold_event = threading.Event()

        # Count of samples since last data push
        self.__sample_count = 0

        # setup if the cached sample queue is to be used
        # if SettingsBase.get_setting(self, "cache") > 0:
        # semaphore to prevent multi-thread Q conflict
        # self.__cache_lock = threading.RLock()

        # 2 queues to simplify arrival of new samples during upload.
        # always alloc these queues - reduces upload to idigi work
        # self.__cache_work = []   # hold new samples
        # self.__cache_upload = [] # samples shifted here for upload

        x = SettingsBase.get_setting(self, "filename") + self.CACHE_EXT
        self.__cache.reset_filenames(x)

        x = SettingsBase.get_setting(self, "cache_size")
        self.__cache.set_max_bytes(x)

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

        # we always cache
        if SettingsBase.get_setting(self, "compact_xml"):
            sam = self.__make_compact_xml(channel.name(),channel.get())
        else:
            sam = self.__make_xml(channel.name(),channel.get())
        self.__cache.append(sam)

        self.__sample_count += 1
        print '%s:%d cache:%s' % (self.__name, self.__sample_count, sam)

        # If we have exceeded the sample threshold, notify the thread
        # responsible for pushing up data
        if self.__sample_count >= SettingsBase.get_setting(self, "sample_threshold"):
#             print "idigi_db: Reached threshold of %i, setting event flag" % sample_threshold
            self.__threshold_event.set()

        return

    def run(self):
        """
        Uploads data whenever an appropriate threshold is met
        """

        self.__last_upload_time = 0
        while not self.__stopevent.isSet():
            try:
                interval = SettingsBase.get_setting(self,
                                        "clean_minute_interval")

                # then we want 'clean minutes' interval
                interval = sleep_aids.secs_until_next_minute_period(interval)

                # add any skew of seconds to move from 00:00:00 (etc)
                interval += SettingsBase.get_setting(self,
                                    "clean_minute_skew_secs")

                # print "idigi_db: I'm waiting for an event or up to %i seconds" % interval
                self.__threshold_event.wait(interval)
                # print "idigi_db: I'm done waiting"

                # local variables
                if self.statistics['total_runs'] > 99999999:
                    self.clear_statistics()
                else:
                    self.statistics['total_runs'] += 1

                self.__sample_count = 0
                self.__threshold_event.clear()

                self.__upload_data()

            except Exception, e:
                traceback.print_exc()
                print "iDigi_DB(%s): exception while uploading: %s" % \
                    (self.__name, str(e))


#         print "idigi_db: Got out of the loop..."

    def __verify_clean_minutes(self, period):
        if period in sleep_aids.PERMITTED_VALUES:
            return True
        print "ERROR: Minute period of %d is not a factor of 60" % period
        print "       period should be in set ", sleep_aids.PERMITTED_VALUES
        return False

    def __upload_data(self):
        """
        Builds XML string of the channel state and pushes to iDigi
        """

        data = self.__cache.lock_cache()
        # print 'data = (%s)' % str(data)

        if data is None:
            # then was left unlocked
            print "idigi_db(%s): sample cache is empty" % self.__name
            # self.__cache.unlock_cache()
            return None

        print "idigi_db: Uploading to iDigi"
        xml = cStringIO.StringIO()
        xml.write("<?xml version=\"1.0\"?>")
        if SettingsBase.get_setting(self, "compact_xml"):
            xml.write("<idigi_data compact=\"True\">")
        else:
            xml.write("<idigi_data>")

        xml.write(data)
        xml.write("</idigi_data>")

        self.__last_upload_time = time.time()
        self.statistics['upload_tries'] += 1
        success = self.__send_to_idigi(xml.getvalue())

        if success:
            # if successful, delete upload list else try again next time
            # self.__cache_upload = []
            self.statistics['upload_good'] += 1

            self.statistics.update({'last_upload':iso_date()})
            self.__cache.free_cache()
        else:
            # failed, try again next time
            self.__cache.unlock_cache()

        xml.close()
        self.save_statistics()
        return

    def save_statistics(self):
        fn = self.__name + self.STATS_EXT
        self.statistics.update({ 'file_number':self.__current_file_number})
        print 'save file: %s' % fn
        string_file.save_string_to_file(fn, self.statistics)
        return

    def load_statistics(self):
        fn = self.__name + self.STATS_EXT
        print 'load file: %s' % fn
        try:
            x = string_file.load_string_from_file(fn)
            if x is not None:
                self.statistics = eval(x)
                self.__current_file_number = self.statistics['file_number']
        except:
            traceback.print_exc()

        return

    def clear_statistics(self):
        self.statistics = { 'total_runs':0L, 'upload_tries':0L, 'upload_good':0L, \
                            'file_number':self.__current_file_number}
        return

    def __make_xml(self, channel_name, sample):
        """
        Converts a sample to XML. Returns String

        Keyword arguments:

        channel_name -- the name of the channel
        sample -- the corresponding sample
        """

        data = ["<sample>"]
        data.append("<name>%s</name>" % channel_name)
        data.append("<value>%s</value>" % \
                    self.__escape_entities(sample.value))
        data.append("<unit>%s</unit>" % sample.unit)
        data.append("<timestamp>%s</timestamp>" % iso_date(sample.timestamp))

        try:
            if isinstance(sample,AnnotatedSample):
                # then add any annotated fields
                if sample.errors:
                    data.append("<errors>%s</errors>" % str(sample.errors))
                if sample.other:
                    data.append("<other>%s</other>" % str(sample.other))
        except:
            traceback.print_exc()
            pass

        data.append("</sample>")

        return "".join(data)

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
        filename_format = SettingsBase.get_setting(self, "filename_format")
        filename = filename_format % (filename, self.__current_file_number)
        collection = SettingsBase.get_setting(self, "collection")
        secure = SettingsBase.get_setting(self, "secure")

        print "idigi_upload: Uploading %s to iDigi" % filename

        success, err, errmsg = idigi_data.send_idigi_data(data, filename, collection, secure)
        if not success:
            # if successful, delete upload list else try again next time
            print "idigi_db: Uploading ERROR %s (%s)" % (err,errmsg)

        self.__current_file_number += 1

        max_files = SettingsBase.get_setting(self, "file_count")

        if self.__current_file_number >= max_files + 1:
            self.__current_file_number = 1

        return success

    def __escape_entities(self, sample_value):
        """
            Replace the existing entities of the sample value.
        """

        if not isinstance(sample_value, types.StringTypes):
            return sample_value

        for ch in ENTITY_MAP:
            sample_value = sample_value.replace(ch, ENTITY_MAP[ch])

        return sample_value


