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

# imports
from core.tracing import get_tracer
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import ChannelSourceDeviceProperty
import time
from devices.xbee.common.addressing import *
import traceback
# constants

# exception classes
class DeviceBasePropertyNotFound(KeyError):
    pass

# interface functions

# classes

class DeviceBase(SettingsBase):
    """
    Base class that any device driver must derive from.

    The :class:`DeviceBase` class is extended in order to create new
    Dia device drivers. :class:`DeviceBase` defines several properties
    and methods for use in iDigi Dia devices including a name for the
    device, a set of property channels that can be populated with
    information about the device as well as the methods for
    interacting with those channels, and virtual *start* and *stop*
    methods that must be implemented in each driver.

    Parameters:

    * *name*: the name of the device
    * *settings*: configures device settings. Used to initialize
      :class:`~settings.settings_base.SettingsBase`
    * *core_services*: The system
      :class:`~core.core_services.CoreServices` object.

    """

    DEF_TRACE = '' # None - no change

    def __init__(self, name, core_services, settings, properties):
        self._name = name
        self._core = core_services
        self._tracer = get_tracer(name)

        # Initialize settings:
        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='trace', type=str, required=False,
                default_value=self.DEF_TRACE),
        ]
        # Add our settings_list entries into the settings passed to us.
        settings = self.merge_settings(settings, settings_list)

        self.__settings = settings
        SettingsBase.__init__(self, binding=("devices", (name,), "settings"),
                                    setting_defs=settings)

        # Initialize properties:
        self.__properties = { }
        for property in properties:
            self.add_property(property)

        # pre_start - check if special trace level requested
        trace = SettingsBase.get_setting(self, "trace")
        try:
            self._tracer.set_level(trace)
        except:
            self._tracer.warning("Ignoring bad trace level \'%s\' for this device", trace)

        self._tracer.calls("DeviceBase.__init__()")


    # def __del__(self):
    #     channel_db = \
    #         self._core.get_service("channel_manager").channel_database_get()

    #     # Walk the pending registry, if this device is in there, remove it.
    #     try:
    #         for tmp in self._settings_global_pending_registry['devices']['instance_list']:
    #             if tmp['name'] == self._name:
    #                 try:


    def merge_settings(self, orig, addin):
        # safely add-in settings to those from derived classes
        #
        # NOTE: If a setting with the same name is found,
        #       save the original and discard the new/add-in one
        
        if orig is None or len(orig) == 0:
            # then there are no original-class settings
            return addin
            
        for add1 in addin:
            # for each new setting
            use = True
            for orig1 in orig:
                # compare to those from original/derived class
                if orig1.name == add1.name:
                    # then ignore new setting, use original/derived classes
                    
                  #  self._tracer.warning("Discard Duplicate Setting: %s", add1.name)
                    use = False
                    break
                    
            if use: # else append new setting to derived classes
                orig.append(add1)
                
        return orig


    def merge_properties(self, orig, addin):
        # safely add-in properties to those from from derived classes
        if orig is None or len(orig) == 0:
            # then there are no original/derived-class settings
            orig = addin

        else:
            orig.extend(addin)
        return orig


    def apply_settings(self):
        """\
            Called when new configuration settings are available.

            Must return tuple of three dictionaries: a dictionary of
            accepted settings, a dictionary of rejected settings,
            and a dictionary of required settings that were not found.
        """

        self._tracer.calls("DeviceBase.apply_settings()")
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)


    def start(self):
        """
        Start the device driver.  Returns bool.
        """
        self._tracer.calls("DeviceBase.start()")
        return True


    def pre_start(self):
        """
        Call at start of start (normal DeviceBase.start called at end bool.
        """
        self._tracer.calls("DeviceBase.pre_start()")
        return True


    def stop(self):
        """
        Stop the device driver.  Returns bool.
        """
        self._tracer.calls("DeviceBase.stop()")

        self.__settings = None
        self.__properties = None
        self._name = None
        self._core = None
        
        ## leave self._tracer, deleting here is problematic during shutdown

        return True


    ## These functions are inherited by derived classes and need not be changed:
    def get_core_services(self):
        """
        Returns the core_services handle registered for this device
        """

        return self._core


    def get_name(self):
        """
        Returns the name of the device.
        """

        return self._name


    def __get_property_channel(self, name):
        """
        Returns channel designated by property *name*.

        """

        channel_db = \
            self._core.get_service("channel_manager").channel_database_get()

        channel_db.channel_get(self._name + '.' + name)
        if name not in self.__properties:
            raise DeviceBasePropertyNotFound, \
                "channel device property '%s' not found." % (name)

        return self.__properties[name]

    def add_property(self, channel_source_device_property):
        """
        Adds a channel to the set of device properties.

        """
        channel_db = \
            self._core.get_service("channel_manager").channel_database_get()
        channel_name = "%s.%s" % \
                        (self._name, channel_source_device_property.name)
        channel = channel_db.channel_add(
                                    channel_name,
                                    channel_source_device_property)
        self.__properties[channel_source_device_property.name] = channel

        return channel

    def property_get(self, name):
        """
        Returns the current :class:`~samples.sample.Sample` specified
        by *name* from the devices property list.

        """

        channel = self.__get_property_channel(name)
        return channel.producer_get()

    def property_set(self, name, sample):
        """
        Sets property specified by the string *name* to the
        :class:`~samples.sample.Sample` object *sample* and returns
        that value.

        """

        channel = self.__get_property_channel(name)
        return channel.producer_set(sample)

    
    def globe_get(self, name):
        """
        Returns the current :class:`~samples.sample.Sample` specified
        by *name* from the devices property list.

        """
        
    #    channel = self.__get_property_channel(name)
    #    return channel.producer_get()
        
        ch = self.__get_property_channel_globe(name)
        
        return ch.producer_get()
     
     
     
     
    def property_set_globe(self, name, sample):
        
        
        
        
        """
        Sets property specified by the string *name* to the
        :class:`~samples.sample.Sample` object *sample* and returns
        that value.

        """
        
        channel = self.__get_property_channel_globe(name)
        channel.consumer_set(sample)
    
        #if self.reading == 0:
            #self.update_list(name, sample.value)
        #else:
            #print "reading from files right now, cannont store settings, but I don't need to"
    
     
     
    def __get_property_channel_globe(self, name):
        """
        Returns channel designated by property *name*.

        """
        
        channel_db = \
            self._core.get_service("channel_manager").channel_database_get()

        try:
           ch = channel_db.channel_get(name)
        except:
            print "error in channel set"
            raise DeviceBasePropertyNotFound, \
                "channel device property '%s' not found." % (name)
       
        
        return channel_db.channel_get(name)
    
    
    
    def property_exists(self, name):
        """
        Determines if a property specified by *name* exists.

        """

        if name in self.__properties:
            return True
        return False

    def property_list(self):
        """
        Returns a list of all properties for the device.

        """

        return [name for name in self.__properties]

    def remove_all_properties(self):
        """
        Removes all properties from the set of device properties.

        """

        channel_db = \
            self._core.get_service("channel_manager").channel_database_get()

        for chan in self.__properties:
            channel_name = "%s.%s" % (self._name, chan)
            chan_obj = channel_db.channel_remove(channel_name)
            if chan_obj:
                del chan_obj
        self.__properties = { }

    
    def current_time_get(self):
        sec_time = time.time()
        main_addr = "mainMistaway_" + gw_extended_address()
        timezone = self.globe_get(main_addr + ".offset")
        timezone = timezone.value
        offset = int(timezone)
        time_here = sec_time + offset 
        return time_here
        
    def remove_one_property(self, chan):
        """
        Removes one named property from the set of device properties.
        """

        channel_db = \
            self._core.get_service("channel_manager").channel_database_get()

        channel_name = "%s.%s" % (self._name, chan)
        try:
            chan_obj = channel_db.channel_remove(channel_name)
            if chan_obj:
                del chan_obj
            self.__properties.pop(chan)
        except:
            self._tracer.debug(traceback.format_exc())
            pass
        return

# internal functions & classes
