############################################################################
#                                                                          #
# Copyright (c)2008, 2009, Digi International (Digi). All Rights Reserved. #
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
The SMTP presentation object.

This presentation object is designed to monitor a specified channel and treat
it as a flag to indicate whether or not to trigger an email being sent to a 
smtp server.

The monitored channel is defined by the configuration file setting 
'monitored_channel'. The channel is then subscribed to so when a new sample
is given, the value of the sample is evaluated in a boolean context, and if 
true, builds a message and queues it for sending.

The message is currently built in a predefined pattern. It will query the 
channel datebase, and extract all the current samples from each channel, and
use it to build a string containing the name and value of each channel.

The 'run' function is intended to act as a worker thread. It monitors the
message queue, pulls out entries as they arrive, and sends them to the defined
SMTP destination. In cases where some or all messages are met with a 
undeliverable status, it prints the undeliverables to the console and returns 
to wait for the next message in the queue.

The generic intention of the email presentation is to be used with the 
transform device. Use the transform device to perform a calculation or a group
of comparisons. For example::

    expr = '(condition1) and (condition2) and (condition3)'

If those three conditions are met, the transform device channel will be
evaluated as true and an email message will be queued, provided the SMTP
presentation was configured to monitor the transform device.

Configuration settings:

* **to_address:** The email address to send the email to
* **from_address:** The from address of the email, defaults to: digi_dia@digi.com
* **subject:** The subject of the email, defaults to: iDigi Dia Alert
* **server_address:** The address of the SMTP server
* **port:** The port of the SMTP server, defaults to: 25
* **monitored_channel:** The Channel that is subscribed to and its samples are
  evaluated to determine queing of the email message.

"""

# import

import threading
import re
import socket
import smtplib
from Queue import Queue
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from channels.channel_publisher import ChannelDoesNotExist
from common.helpers.format_channels import dump_channel_db_as_text

# constants

# classes

class SMTPHandler(PresentationBase, threading.Thread):
    def __init__(self, name, core_services):
        """ Create the SMTPHandler presentation service """
        self.__name = name
        self.__core = core_services
             
        self.queue = Queue()
        self.started_flag = False
        self.monitored_channel = None
        
        settings_list = [Setting(name="to_address", type=str, required=True),
                             Setting(name="from_address", type=str, required=False, 
                                             default_value="lewiswight1@yahoo.com"),
                             Setting(name="subject", type=str, required=False, 
                                             default_value=" "),
                             Setting(name="server_address", type=str, required=True, default_value="smtp.gmail.com"),
                             Setting(name="port", type=int, required=False, 
                                             default_value=465),
                             Setting(name="monitored_channel", type=str, required=True)]

        PresentationBase.__init__(self, name=name, settings_list=settings_list)
        
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)
        
    def gethostbyaddr(ip_addr):
        """Workaround for no 'gethostbyaddr()' on the ConnectPort"""
        return ip_addr, [], [ip_addr]

        socket.gethostbyaddr = gethostbyaddr
    
    
    def apply_settings(self):
        """    Apply settings as they are defined by the configuration file """
        
        email_reg = re.compile('[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}', re.IGNORECASE)
        
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        
        ## Validate email addresses
        if not email_reg.search(accepted['to_address']):
            raise Exception("to_address was invalid: %s" %accepted['to_address'])
        if not email_reg.search(accepted['from_address']):
            raise Exception("from_address was invalid: %s" %accepted['from_address'])
        
        ## Validate port
        try:            
            if int(accepted['port']) < 1 or (int(accepted['port']) > 65535):
                raise Exception("port is an invalid port number %s" %accepted['port'])
        except ValueError:
            raise Exception("port is an invalid port number %s" %accepted['port'])
        
        ## Get handle to channel manager, which gives us channel publisher
        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
    
        ##Unsubscribe to the 'old' channel if we have subscribed before 
        if self.monitored_channel is not None:
            try:
                cp.unsubscribe(self.monitored_channel, self.queue_msg)
            except ChannelDoesNotExist:
                print "The channel %s does not exist, it cannot be unsubscribed to" % \
                            (self.monitored_channel)
        
        ## subscribe to monitored_channel         
        self.monitored_channel = accepted['monitored_channel']
        cp.subscribe(self.monitored_channel, self.queue_msg)
        
        SettingsBase.commit_settings(self, accepted)
        return (accepted, rejected, not_found)
    
    def start(self):
        """ Starts the presentation object """
        self.started_flag = True
        threading.Thread.start(self)
        self.apply_settings()
        return True
    
    def queue_msg(self, channel):
        """ Call back for the channel publisher's __notify function. If the sample
        from the channel evaluates to boolean True, queues message """
        monitored_sample = channel.get()
                        
        if not self.started_flag:
            raise Exception("Cannot queue message, presentation is stopped")
        
        if monitored_sample.value:
            cm = self.__core.get_service("channel_manager")
            cdb = cm.channel_database_get()

            frm    = SettingsBase.get_setting(self, 'from_address')
            to     = SettingsBase.get_setting(self, 'to_address')
            sbj    = SettingsBase.get_setting(self, 'subject')
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % \
                                (frm, to, sbj)
            msg += "motion event in the kitchen"
            self.queue.put(msg)
    
    def run(self):
        """ Worker thread for the SMTP handler. This monitors the queue and 
        attempts to send the queued message to the specified address""" 
                
        while self.started_flag:
            msg = self.queue.get()
            
            if not self.started_flag:
                return

            host = "smtp.mail.yahoo.com" # SettingsBase.get_setting(self, 'server_address')
            port = 25 #SettingsBase.get_setting(self, 'port')
            frm    = "lewiswight1@yahoo.com"# SettingsBase.get_setting(self, 'from_address')
            to     = "4357645431@txt.att.net" # SettingsBase.get_setting(self, 'to_address')
            smtpserver = 'smtp.mail.yahoo.com'
            smtpuser = 'lewiswight1@yahoo.com'         # set SMTP username here
            smtppass = 'columbus1' 
            
            
            
            
            
          #  try:
            s = smtplib.SMTP(host, port)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(smtpuser, smtppass)
           # error_list = s.sendmail(frm, to, msg)
            #except Exception, e:
             #   print "Failed to connect to SMTP server"
            #    print "If using a DNS name, make sure the Digi device is configured to use the correct DNS server"
               
            try:
                error_list = s.sendmail(frm, to, msg)    
            except:
                print "SMTP: Failed to send messages, please double check server/port"
            s.quit()
          #  else:
         #       for err in error_list:
        #            print "SMTP: Failed to send message to %s address" % (err)
       #     s = smtplib.SMTP(host, port)
            
                
    def stop(self):
        """ Stop the presentation object """
        if not self.started_flag:
                return False

        self.started_flag = False
        # Queuing anything with the start_flag set to False will
        # cause the thread running in the run() loop to terminate.
        self.queue.put("quit")

        return True
