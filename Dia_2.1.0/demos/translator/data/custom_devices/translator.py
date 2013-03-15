# -*- coding: iso-8859-1 -*-
############################################################################
#                                                                          #
# Copyright (c)2008, 2009, Digi International (Digi). All Rights Reserved. #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,  and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. ContactProduct Management, Digi International, Inc., 11001 Bren    #
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

"""
  Custom translator demo driver, this driver creates 2 channels (InputString
  and OutputString) to translate words from English to Spanish or from
  Spanish to English, depending on the 'EnglishToSpanish' setting value.

  Declaration example:

  - name: translator0
    driver: custom_devices.translator:Translator
    settings:
        EnglishToSpanish: True

"""

# Imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from samples.sample import Sample
import time


class Translator(DeviceBase):
    #Dictionaries definitions
    engtospa = {"hello": "Hola", "bye": "Adiós", "house": "Casa",
                "day": "Día", "thanks": "Gracias", "please": "Por favor",
                "water": "Agua", "sun": "Sol", "moon": "Luna",
                "sky": "Cielo", "digi": "Facilitando M2M inalámbrico",
                "idigi": "Soluciones M2M inalámbricas instantáneas"}
    spatoeng = {"hola": "Hello", "adiós": "Bye", "casa": "House",
                "día": "Day", "gracias": "Thanks", "por favor": "Please",
                "agua": "Water", "sol": "Sun", "luna": "Moon", "cielo": "Sky",
                "digi": "Making Wireles M2M Easy",
                "idigi": "Instant Wireless M2M Solutions"}

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='EnglishToSpanish', type=bool, required=False,
                default_value=True)]

        #Declare the Input and Output channels
        property_list = [
            ChannelSourceDeviceProperty(name="InputString", type=str,
                  initial=Sample(time.time(), ""),
                  perms_mask=DPROP_PERM_GET | DPROP_PERM_SET,
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda sample: self.translate(sample=sample)),
            ChannelSourceDeviceProperty(name="OutputString", type=str,
                  initial=Sample(time.time(), ""),
                  perms_mask=DPROP_PERM_GET,
                  options=DPROP_OPT_AUTOTIMESTAMP),
        ]

        ## Initialze the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:
    def apply_settings(self):
        '''
        Called when new configuration settings are available.

        Must return tuple of three dictionaries: a dictionary of
        accepted settings, a dictionary of rejected settings,
        and a dictionary of required settings that were not
        found.
        '''
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        if len(rejected) or len(not_found):
            print "Settings rejected/not found: %s %s" % (rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""
        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        return True

    def translate(self, sample):
        '''
        Translate the 'InputString' channel word from English to Spanish or
        Spanish to English (depending on the 'EnglishToSpanish' setting value)
        and put the translated word into the 'OutputString' channel. If the
        word can't be found, 'OutputString' channel will contain the same
        word as 'IntputString' one.
        '''
        input_word = sample.value
        output_word = input_word
        if SettingsBase.get_setting(self, "EnglishToSpanish"):
            if input_word.lower() in self.engtospa:
                output_word = self.engtospa[input_word.lower()]
            self.property_set("InputString", Sample(time.time(), sample.value))
            self.property_set("OutputString", Sample(time.time(), output_word))
        else:
            input_word = sample.value
            if input_word.lower() in self.spatoeng:
                output_word = self.spatoeng[input_word.lower()]
            self.property_set("InputString", Sample(time.time(), sample.value))
            self.property_set("OutputString", Sample(time.time(), output_word))
