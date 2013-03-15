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
Custom Channel Viewer Presentation module

Prints into the Telnet Session all the channels from the given channel list
and their values each configurated time (in seconds).

Configuration settings:

channels       = The list of channels that will be printed
update_rate    = (Optional) The number of seconds between each update, 5 by 
                 default

Presentation declaration example:

- name: viewer0
    driver: custom_presentations.channel_viewer:CViewer
    settings:
        channels: [translator0.InputString,translator0.OutputString]
        update_rate: 10
"""

# Imports
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
import sys, traceback, cgi, os.path
import time
import threading

#Main Class
class CViewer(PresentationBase):
    #Class vars    
    __channels =[]
    __update_rate = 5
    channels_to_update = []
    
    class Timer(threading.Thread):        
        runTime = 0
        tick = None
        #Given parameters are the time between ticks and the 
        #method to execute in each tick
        def __init__(self, seconds, method):
            self.runTime = seconds
            self.tick = method
            self.stop_event = threading.Event()
            threading.Thread.__init__(self)
        
        def stop(self):
            self.stop_event.set()
        
        def run(self):
            #Use global vars
            #Do forever...
            while not self.stop_event.isSet():
                #Wait (sleep) configured time
                time.sleep(self.runTime)
                self.tick()
                
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__xbee_display = None

        #Declare the settings list
        settings_list = [
            Setting(name="channels", type=list, required=True),
            Setting(name="update_rate", type=int, required=False, 
                    default_value=5)
        ]
                             
        PresentationBase.__init__(self, name=name, settings_list=settings_list)
  
    def apply_settings(self):
        """  Apply settings as they are defined by the configuration file """

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        if len(rejected) or len(not_found):
            print "Settings rejected/not found: %s %s" % (rejected, not_found)
            
        self.__channels = accepted['channels']
        self.__update_rate = accepted['update_rate']
        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)
    
    def start(self):
        """ Starts the presentation object """
                
        self.cm = self.__core.get_service("channel_manager")
        self.cp = self.cm.channel_publisher_get()
        self.cdb = self.cm.channel_database_get()
        
        #Get all the channels that will be displayed
        for channel in self.__channels:
            self.channels_to_update.append(self.cdb.channel_get(channel))
        
        #Create and start the updater timer
        self.updater = self.Timer(self.__update_rate, self.print_channels)
        self.updater.start()
    
    def stop(self):
        """ Stop the presentation object """
        self.updater.stop()
        return True
    
    def print_channels(self):
        """ Print the channels table """
        
        #Pint time stamp
        print "\nChannels status at: "+str(time.ctime())
        #Print the header
        print ("-"*74)
        print (" Channel"+33*" "+"| Value"+11*" "+"| Unit"+8*" "+"|")
        print ("-"*74)
        # Print all channels from 'channels_to_update' list with their values
        for channel in self.channels_to_update:
            name = str(channel.name())
            value = str(channel.get().value)
            unit = str(channel.get().unit)
            print(" "+name+" "*(40-len(name))+"| "+
                  value+" "*(16-len(value))+"| "+unit+
                  " "*(12-len(unit))+"|")
        print ("-"*74)
            
            