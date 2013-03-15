"""
Python ZigBee Class
Michael Sutherland
Davis, Ca office
Digi International
All Rights Reserved
Copyright 2008-2009

History
12/03/08 - Creation
02/11/09 - Added remote AT commands, getnodelist, and blocking calls.
02/12/09 - Fixed select bug that broke non-blocking select.
"""

# Warning: 
# This library is still under development.  
# It has not been fully tested.
# Use at your own risk.  
# Digi International takes no responsibility and assumes no liability for code use.

# Requirements:
# Must have pySerial and associated libraries (win32 module for Windows)
# Serial connection to xbee must be configured with following commands:
#    zigbee.default_xbee.serial = serial.Serial("COM#", 115200, rtscts = 0)
#    zigbee.ddo_set_param("", "AO", chr(1)) # get explicit messages
# Serial configuration can be stored in different file.  
#    "default_xbee_config.py" is checked by the library when zigbee.py is imported.
# XBee must be API mode firmware.  ZB or ZNet2.5. 

# Limitations:
# Must import zigbee before doing either "from socket import *" or "from select import *"
# Must import zigbee to use zigbee socket.
# Must import zigbee to use zigbee select.
# Zigbee socket options not support (except non_blocking)
# Short network addressing not supported.
# Incomplete error checking.
# Anything else not implemented from the TODO list below.

# TODO List:
#    Add support for network (short) addresses.
#    Add socket options.
#    Add more error checking and match ConnectPort errors
#    Support for blocking calls for sendto
#    Support Node Discovery for non-XBee devices.

# Try importing _zigbee.py.  This will work on a ConnectPort.
try: 
    from _zigbee import * 

except: 

    import struct
    import string
    import serial
    import time
    import socket
    import select
    
    # set parameters
    __all__ = ["ddo_get_param", "ddo_set_param", "getnodelist", "get_node_list"]
    
    def __register_with_socket_module(object_name):
        "Register object with socket module (add to __all__)"
        try:
            if socket.__all__ is not None:
                if object_name not in socket.__all__:
                    socket.__all__.append(object_name)
        except:
            # there is no __all__ defined for socket object
            pass
    
    def MAC_to_address_string(MAC_address, num_bytes = 8):
        """Convert a MAC address to a string with "[" and "]" """
        address_string = "["
        for index in range(num_bytes - 1, -1, -1):
            address_string += string.hexdigits[0xF & (MAC_address >> (index * 8 + 4))]
            address_string += string.hexdigits[0xF & (MAC_address >> (index * 8))]
            if index:
                address_string += ":"
            else:
                address_string += "]!"
        return address_string
            
    def address_string_to_MAC(address_string):
        "Convert an address string to a MAC address"
        MAC_address = 0
        if address_string[0] == "[":
            return int("0x" + string.replace(address_string[1:-2], ":", ""), 16)
        else:
            return int("0x" + string.replace(address_string[0:-1], ":", ""), 16)
            
    
    def short_to_address_string(short_address):
        "Convert a short (network) address to a string"
        return "[%02X%02X]!" % ((short_address >> 16) & 0xFF, short_address & 0xFF)    
        
    def address_string_to_short(address_string):
        "Convert an address string to a short (network) address"
        short_address = 0
        return int("0x" + address_string[1:-2], 16)
    
    
    class API_Data:
        """Base class for storing data in an API message
        Also stores a static frame ID for different messages to use."""
    
        xbee_frame_id = 1
        "Frame ID for transmitting to the XBee node"
        rx_id = 0
        "Receive API message type ID"
        tx_id = 0
        "Transmit API message type ID"
    
        def __init__(self):
            "Creates API_Data object"
            self.data = ""
            self.frame_id = 0
    
        def next_frame(self):
            "Returns the next frame ID for sending a message"
            self.xbee_frame_id = (self.xbee_frame_id + 1) & 0xFF
            return self.xbee_frame_id
        
        def extract(self, cmd_data):
            "Base class just grabs the whole buffer"
            self.data = cmd_data
            
        def export(self):
            "Returns the whole buffer as a string"
            return self.data
        
    
    class ZB_Data(API_Data):
        "Extracts a ZigBee frame from the XBee Rx message and outputs a ZigBee transmit frame."
        BROADCAST_RADIUS = 0
        "Number of hops on the ZigBee network."
        OPTIONS = 0
        "Options in the ZigBee message (should be set to zero)"
        rx_id = 0x91
        "Receive API message type ID"
        tx_id = 0x11
        "Transmit API message type ID"
        
        def __init__(self, source_address = None, destination_address = None, payload = ""):
            "Initializes the zb_data with no data."
            API_Data.__init__(self)        
            self.source_address = source_address
            self.destination_address = destination_address
            self.payload = payload
    
        def extract(self, cmd_data):
            "Extract a ZigBee message from a 0x91 xbee frame cmd_data"
            if len(cmd_data) < 17:
                #Message too small, return error
                return -1
            source_address_64, = struct.unpack("!Q", cmd_data[0:8])
            source_address_16, = struct.unpack("!H", cmd_data[8:10])
            source_endpoint = ord(cmd_data[10])
            destination_endpoint = ord(cmd_data[11])
            cluster_id, = struct.unpack("!H", cmd_data[12:14])
            profile_id, = struct.unpack("!H", cmd_data[14:16])
            options = ord(cmd_data[16])
            self.payload = cmd_data[17:]
            # convert source address to proper string format, create address tuple        
            self.source_address = (MAC_to_address_string(source_address_64), source_endpoint, profile_id, cluster_id)
            self.destination_address = ("", destination_endpoint, profile_id, cluster_id)
            return 0
            
        def export(self):
            "Export a ZigBee message as a 0x11 xbee frame cmd_data"
            self.frame_id = self.next_frame()
            cmd_data = chr(self.frame_id) #frame id
            cmd_data += struct.pack(">Q", address_string_to_MAC(self.destination_address[0])) # destination_address_64
            cmd_data += chr(0xFF) + chr(0xFE) # destination_address_16
            cmd_data += chr(self.source_address[1]) # source_endpoint
            cmd_data += chr(self.destination_address[1]) # destination_endpoint
            cmd_data += struct.pack("!H", self.destination_address[3]) # cluster_id
            cmd_data += struct.pack("!H", self.destination_address[2]) # profile_id
            cmd_data += chr(self.BROADCAST_RADIUS) # broadcast radius
            cmd_data += chr(self.OPTIONS) # options
            cmd_data += self.payload
            return cmd_data
        
    
    class Local_AT_Data(API_Data):
        "Extracts from an AT Response frame and exports to an AT Command frame."
        rx_id = 0x88
        "Receive API message type ID"
        tx_id = 0x08
        "Transmit API message type ID"
        def __init__(self, AT_cmd = "", value = ""):
            API_Data.__init__(self)
            "Initializes the AT frame with no data."
            self.AT_cmd = AT_cmd
            "Two character string of the character command"
            self.status = 0
            "Status of a received message"
            self.value = value
            "Value received or to be set for the AT command"
    
        def extract(self, cmd_data):
            "Extract an AT response message from a 0x88 xbee frame cmd_data"
            if len(cmd_data) < 5:
                #Message too small, return error
                return -1
            self.frame_id = ord(cmd_data[0])
            self.AT_cmd = cmd_data[1:3]
            self.status = ord(cmd_data[3])
            self.value = cmd_data[4:]
            return 0
            
        def export(self):
            "Export an AT message as a 0x08 xbee frame cmd_data"
            self.frame_id = self.next_frame()
            cmd_data = chr(self.frame_id)
            cmd_data += self.AT_cmd
            cmd_data += self.value
            return cmd_data
    
    
    class Remote_AT_Data(API_Data):
        "Extracts from a Remote AT Response frame and exports to a Remote AT Command frame."
        rx_id = 0x97
        "Receive API message type ID"
        tx_id = 0x17
        "Transmit API message type ID"
        def __init__(self, remote_address = None, AT_cmd = "", value = ""):
            API_Data.__init__(self)
            "Initializes the AT frame with no data."
            self.remote_address = remote_address
            "Extended address of XBee that is having AT parameter set, stored as formatted string."
            self.AT_cmd = AT_cmd
            "Two character string of the character command"
            self.status = 0
            "Status of a received message"
            self.value = value
            "Value received or to be set for the AT command"
    
        def extract(self, cmd_data):
            "Extract a remote AT response message from a 0x97 xbee frame cmd_data"
            if len(cmd_data) < 15:
                #Message too small, return error
                return -1
            self.frame_id = ord(cmd_data[0])
            source_address_64, = struct.unpack("!Q", cmd_data[1:9])
            self.remote_address = MAC_to_address_string(source_address_64)
            source_address_16, = struct.unpack("!H", cmd_data[9:11]) # we don't care about this value...
            self.AT_cmd = cmd_data[11:13]
            self.status = ord(cmd_data[13])
            self.value = cmd_data[14:]
            return 0
            
        def export(self):
            "Export a remote AT message as a 0x17 xbee frame cmd_data"
            self.frame_id = self.next_frame()
            cmd_data = chr(self.frame_id)
            cmd_data += struct.pack(">Q", address_string_to_MAC(self.remote_address)) # destination_address_64
            cmd_data += chr(0xFF) + chr(0xFE) # destination_address_16
            cmd_data += chr(0x02) # Command Options (Always set immediately)        
            cmd_data += self.AT_cmd
            cmd_data += self.value
            return cmd_data
    
    class API_Message:
        "Creates API message for the XBee"
        
        API_IDs = {ZB_Data.rx_id: ZB_Data, Local_AT_Data.rx_id: Local_AT_Data, Remote_AT_Data.rx_id: Remote_AT_Data}
        "Stores the different APIs"
        
        def __init__(self):
            self.length = 0
            "Length field of the frame"
            self.API_ID = 0
            "Frame message ID."
            self.cmd_data = ""
            "Data payload for the frame"
            self.api_data = API_Data()
            "Formatted command data"
            self.checksum = 0
            "Checksum value for the message"
            
        def __len__(self):
            "Length of the entire message"
            return self.length + 4
    
        def calc_checksum(self):
            "Calculates the checksum, based on cmd_data"
            checksum = self.API_ID
            for byte in self.cmd_data:
                checksum += ord(byte)
                checksum &= 0xFF
            return 0xFF - checksum
        
        def set_length(self):
            "Calculates the length and sets it, based on cmd_data"
            self.length = len(self.cmd_data) + 1
    
        def set_API_ID(self):
            "Sets the API_ID from the message data type"
            if self.api_data.tx_id:
                self.API_ID = self.api_data.tx_id 
        
        def is_valid(self):
            "Verifies that the checksum is correct"
            return self.checksum == self.calc_checksum()
            
        def extract(self, buffer):
            """Extracts the message from a string
            returns number of bytes used on success
            -1 when the buffer is not big enough(string not long enough)"""
            index = 0
            # make sure buffer starts with the Start Delimiter 0x7E
            start_found = 0
            while len(buffer[index:]) >= 5:
                if ord(buffer[index]) != 0x7E:
                    index += 1
                else:
                    # pull out length (MSB)
                    length = ord(buffer[index+1]) * 255 + ord(buffer[index + 2])
                    # make sure we have enough of the buffer to get the full message
                    if len(buffer[index:]) >= length + 4:
                        # we have a full ZigBee message, lets extract it.
                        self.length = length
                        self.API_ID = ord(buffer[index + 3])
                        self.cmd_data = buffer[index + 4: index + length + 3]
                        if self.API_ID in self.API_IDs.keys():
                            self.api_data = self.API_IDs[self.API_ID]()
                        else:
                            self.api_data = API_Data()
                        self.api_data.extract(self.cmd_data)
                        self.checksum = ord(buffer[index + length + 3])
                        return len(self)
                    break
            return -1
            
        def export(self, recalculate_checksum = 1):
            """Exports the message to a string, will recalculate checksum by default.
            Will also re-calculate the length field and lookup API_ID from message type."""
            self.set_API_ID() # must be done before calculating checksum
            self.cmd_data = self.api_data.export() # must be done before calculating checksum
            self.checksum = self.calc_checksum() # calculate the new checksum and set it
            self.set_length() # set the new length
            return chr(0x7E) + chr(self.length / 255) + chr(self.length & 0xFF) + chr(self.API_ID) + self.cmd_data + chr(self.checksum)
    
    
    class XBee:
        "Handles the connection to an XBee module"
        
        def __init__(self, serial = None):
            "Creates the connection to the XBee using the serial port."
            self.serial = serial
            "Serial port that connects to the xbee"
            self.addresses = []
            "List of accepted addresses for messages"
            self.rx_messages = {}
            "Messages received from the XBee."
            self.rx_buffer = ""
            "Receive buffer for the serial port"
    
        def register_address(self, local_address):
            "Registers an address to save messages for"
            local_address = ("", local_address[1], 0, 0)
            if local_address not in self.addresses:
                self.addresses.append(local_address)
    
        def unregister_address(self, local_address):
            "Un-registers an address, so that the messages are no long saved"
            local_address = ("", local_address[1], 0, 0)
            if local_address in self.addresses:
                self.addresses.remove(local_address)
            if local_address in self.rx_messages:
                del self.rx_messages[local_address]
    
        def recv(self, local_address):
            "Reads the messages from the XBee.  Returns from address and payload as a string"
            if self.serial is None or not self.serial.isOpen():
                return None
            # checks for any new messages
            self.read_messages()
            # check to see if there are any messages waiting
            if local_address in self.rx_messages.keys():
                # there was a message
                recv_tuple = self.rx_messages[local_address][0]
                self.rx_messages[local_address].remove(recv_tuple)
                if not self.rx_messages[local_address]:
                    # remove the entry if there are no more messages
                    del self.rx_messages[local_address]
                return recv_tuple[0], recv_tuple[1] #payload, address
            return None, None
    
        def send(self, message):
            "Send an API message"
            # dev_idea: could keep track of frame_id and the responses.
            if self.serial is not None and self.serial.isOpen():
                #print "tx: %s" % [ord(x) for x in message.export()]
                self.serial.write(message.export())
            
        def send_zb(self, source_address, destination_address, payload):
            "Sends message to the XBee."
            if destination_address[0] == "":
                # this is a local message, loop back to received messages
                # mask out profile and cluster ID
                local_address = ("", destination_address[1], 0, 0)
                if local_address in self.addresses:
                    # create the tuple to store the message
                    # the source address will not have the profile and cluster IDs
                    # these are added based on the destination address
                    full_source_address = (source_address[0], source_address[1], destination_address[2], destination_address[3])
                    recv_tuple = (payload, full_source_address)
                    # add data to the message queue
                    if local_address in self.rx_messages.keys():
                        self.rx_messages[local_address].append(recv_tuple)
                    else:
                        self.rx_messages[local_address] = [recv_tuple]            
            else:
                # send message out the XBee
                message = API_Message()
                message.API_ID = 0x11
                zb_data = ZB_Data()
                zb_data.source_address = source_address
                zb_data.destination_address = destination_address
                zb_data.payload = payload
                message.api_data = zb_data
                self.send(message)
            
        def read_messages(self, AT_frame_id = 0):
            """Reads messages from the serial port, return message if it matches
            the AT_frame_id (meant to be used for AT commands)"""
            self.rx_buffer += self.serial.read(self.serial.inWaiting()) #read everything that is available
            while 1:
                message = API_Message() #create message and try to fill it from the serial port data.
                status = message.extract(self.rx_buffer)
                if status < 0:
                    # not enough buffer for the message
                    break
                # received frame, remove from buffer
                #print "rx: %s" % [ord(x) for x in self.rx_buffer[:status]]
                self.rx_buffer = self.rx_buffer[status:]
                if message.is_valid():
                    if message.API_ID == ZB_Data.rx_id: #magic number for explicit receive
                        #extract the zb_data
                        zb_data = message.api_data
                        # make sure the address is registered, check with address = ""
                        local_address = ("", zb_data.destination_address[1], 0, 0)
                        if local_address in self.addresses:
                            # create the tuple to store the message
                            recv_tuple = (zb_data.payload, zb_data.source_address)
                            # add data to the message queue
                            if local_address in self.rx_messages.keys():
                                self.rx_messages[local_address].append(recv_tuple)
                            else:
                                self.rx_messages[local_address] = [recv_tuple]
                    elif message.API_ID == Local_AT_Data.rx_id: #magic number for local AT response
                        #extract the at_data
                        at_data = message.api_data
                        # check if this is the message we are waiting for
                        if at_data.frame_id == AT_frame_id:
                            return message
                    elif message.API_ID == Remote_AT_Data.rx_id: #magic number for remote AT response
                        #extract the at_data
                        at_data = message.api_data
                        # check if this is the message we are waiting for
                        if at_data.frame_id == AT_frame_id:
                            return message
                    else:
                        # we are currently not handling this message type
                        pass
            return None
        
        def ddo_get_param(self, addr_extended, id, timeout = 500):
            "Get a Digi Device Objects parameter value (only local address currently supported)"
            # check format of id
            if not isinstance(id, str):
                raise Exception("ddo_get_param() argument 2 must be string or read-only buffer, not " + str(id.type()))
            elif len(id) != 2:
                raise Exception("ddo_get_param: id string must be two characters!")
            # create message to send.
            message = API_Message()
            if addr_extended is None:
                message.api_data = Local_AT_Data(id)    
                self.send(message)
            else:
                if not isinstance(addr_extended, str):
                    # TTDO: this should be type error
                    raise Exception("ddo_get_param: addr_extended must be a string or None.")
                if len(addr_extended) != 26:
                    #TTDO: should do better test of format...
                    raise Exception("ddo_get_param: addr_extended format is invalid!")
                message.api_data = Remote_AT_Data(addr_extended, id)    
                self.send(message)            
            # wait to receive response
            AT_frame_id = message.api_data.frame_id
            at_response = None
            start_time = time.time()
            while start_time + timeout > time.time():
                at_response = self.read_messages(AT_frame_id)
                if at_response is not None:
                    break
            else:
                raise Exception("ddo_get_param: error fetching DDO parameter.")
                return ""
            return at_response.api_data.value       
            
        def ddo_set_param(self, addr_extended, id, value):
            "Set a Digi Device Objects parameter value"
            # check format of id
            if not isinstance(id, str):
                # TTDO: this should be a type error
                raise Exception("ddo_set_param() argument 2 must be string or read-only buffer, not " + str(id.type()))
            elif len(id) != 2:
                raise Exception("ddo_set_param: id string must be two characters!")
            # convert integer values to a string
            if isinstance(value, int):
                value_str = "" 
                # convert to big endian string representation
                while value > 0:
                    value_str = chr(value & 0xFF) + value_str
                    value /= 0xFF
                if value_str == "":
                    # default to zero 
                    value_str = chr(0)
                value = value_str
                        
            # create message to send.
            message = API_Message()
            if addr_extended is None:
                message.api_data = Local_AT_Data(id, value)    
                self.send(message)
            else:
                if not isinstance(addr_extended, str):
                    # TTDO: this should be type error
                    raise Exception("ddo_set_param: addr_extended must be a string or None.")
                if len(addr_extended) != 24 and len(addr_extended) != 26: # depends on "[" and "]"
                    #TTDO: should do better test of format...
                    raise Exception("ddo_set_param: addr_extended format is invalid!")
                message.api_data = Remote_AT_Data(addr_extended, id, value)    
                self.send(message)            
            #TTDO: should be waiting for a response
            #raise Exception("ddo_set_param: error setting DDO parameter.") # on timeout or error

        def getnodelist(self):
            "Perform a node discovery (blocking)"
            nt_str = ddo_get_param(None, "NT")
            # support 1 or 2 byte return
            if len(nt_str) == 1:
                nt, = struct.unpack(">B", nt_str)
            elif len(nt_str) == 2:
                nt, = struct.unpack(">H", nt_str)
            else:
                nt = 0xFF
            node_discovery_timeout = nt / 10.0 # in seconds
            response_list = []
            node_list = []
            # start Node discovery
            message = API_Message()
            message.api_data = Local_AT_Data("ND")    
            self.send(message)            
            # wait to receive responses
            AT_frame_id = message.api_data.frame_id
            at_response = None
            start_time = time.time()
            while start_time + node_discovery_timeout > time.time():
                at_response = self.read_messages(AT_frame_id)
                if at_response is not None:
                    # store responses for parsing later.
                    response_list.append(at_response)
            # parse responses
            device_types = ["coordinator", "router", "end"]
            for at_response in response_list:
                msg = at_response.api_data.value
                addr_short, addr_extended = struct.unpack(">HQ", msg[0:10]) 
                # convert 16-bit address into a formatted string
                addr_short = short_to_address_string(addr_short)
                # convert 64-bit address into a formatted string
                addr_extended = MAC_to_address_string(addr_extended)
                label = ""
                for character in msg[10:]:
                    if character != chr(0):
                        label += character
                    else:
                        break
                index = 11 + len(label)
                addr_parent, type, status, profile_id, manufacturer_id = struct.unpack(">HBBHH", msg[index:index + 8])
                # turn type into a string
                type = device_types[type]
                node_list.append(Node(type, addr_extended, addr_short, addr_parent, profile_id, manufacturer_id, label))
            return node_list
    
    # Create local XBee to refer to by default
    default_xbee = XBee()
    "XBee that communication defaults to (would be the only XBee on a ConnectPort)" 
    
    def ddo_get_param(addr_extended, id):
        "Get a Digi Device Objects parameter value (only local address currently supported)"
        return default_xbee.ddo_get_param(addr_extended, id)
    
    def ddo_set_param(addr_extended, id, value):
        "Set a Digi Device Objects parameter value (only local address currently supported)"
        return default_xbee.ddo_set_param(addr_extended, id, value)
    
    def getnodelist():
        "Perform a node discovery (blocking)"
        return default_xbee.getnodelist()

    # second name for getting a node list
    get_node_list = getnodelist        
    
      
    # Constants for the socket class
    socket.AF_ZIGBEE = 98
    __register_with_socket_module("AF_ZIGBEE")    
    socket.ZBS_PROT_APS = 81    
    __register_with_socket_module("ZBS_PROT_APS")
    socket.ZBS_PROT_TRANSPORT = 80
    __register_with_socket_module("ZBS_PROT_TRANSPORT")
    socket.MSG_DONTWAIT = 128
    __register_with_socket_module("MSG_DONTWAIT")
    # socket option constants
    socket.ZBS_SOL_ENDPOINT = 65562
    __register_with_socket_module("ZBS_SOL_ENDPOINT")
    socket.ZBS_SOL_EP = socket.ZBS_SOL_ENDPOINT
    __register_with_socket_module("ZBS_SOL_EP")
    socket.ZBS_SOL_APS = 65563
    __register_with_socket_module("ZBS_SOL_APS")
    # SOL_SOCKET parameters
    socket.SO_NONBLOCK = 0
    __register_with_socket_module("SO_NONBLOCK")
    # ZBS_SOL_ENDPOINT / ZBS_SOL_EP parameters
    # ZBS_SOL_APS parameters
    class ZigBee_Socket:
        "ZigBee Socket that emulates the one on a Digi ConnectPort X."
        
        def __init__(self, family = socket.AF_ZIGBEE, type = socket.SOCK_DGRAM, proto = socket.ZBS_PROT_APS, xbee = default_xbee):
            "Create a ZigBee socket for communication"
            self.family = family
            self.type = type
            if proto is None:
                proto = socket.ZBS_PROT_APS
            self.proto = proto
            self.xbee = xbee
            self.address = None
            # initialize the socket options
            self.options = {}
            # SOL_SOCKET
            self.options[socket.SOL_SOCKET] = [  
                                                0 # SO_NONBLOCK
                                                ]
            # ZBS_SOL_ENDPOINT
            self.options[socket.ZBS_SOL_ENDPOINT] = []
            # ZBS_SOL_APS
            self.options[socket.ZBS_SOL_APS] = []
            
        def __del__(self):
            "Delete the socket"
            self.close()
    
        def close(self):
            "Close the socket"
            # remove self from xbee
            self.xbee.unregister_address(self.address)
            
        def getsockopt(self, level, optname):
            "Get socket options"
            if level in self.options.keys():
                if 0 <= self.options[level] < optname:
                    return self.options[level][optname]
            return None
    
        def _pending_message(self):
            "Check to see if there is a message ready"
            self.xbee.read_messages()
            return self.address in self.xbee.rx_messages.keys()
            
        def recvfrom(self, buflen, flags = 0):
            "Receive a message from the socket."
            nonblocking = False
            if flags == socket.MSG_DONTWAIT or self.getsockopt(socket.SOL_SOCKET, socket.SO_NONBLOCK) != 0:
                nonblocking = True
            if self.address is None:
                raise Exception("error: socket not bound yet") #Note: this is a different error
            while (1):
                payload, address = self.xbee.recv(self.address)
                if payload is not None:
                    return payload[:buflen], address
                elif nonblocking:
                    return None, None
            
        def sendto(self, data, flags, addr = None):
            "Send a message from a socket"
            if addr is None:
                addr = flags
                flags = 0
            #TTDO: Should support the MSG_DONTWAIT flag and do a blocking call.
            if self.address is not None:
                self.xbee.send_zb(self.address, addr, data)
            return len(data)
        
        def setsockopt(self, level, optname, value):
            "Set socket options"
            if level == socket.SOL_SOCKET and optname == socket.SO_NONBLOCK:
                self.options[level][optname] = value 
            #TTDO: figure out the return value
        
        def bind(self, address):
            "Bind a socket to an address"
            # reformat address to only look at the endpoint
            address = ("", address[1], 0, 0)
            # remove address from the XBee if needed
            if self.address in self.xbee.addresses:
                del self.xbee.addresses[self.address]
            # make sure there isn't already a socket bound to this address.
            if address in self.xbee.addresses:
                self.address = None
                raise Exception("error: socket already bound on this address")
            else:
                # add the address
                self.xbee.addresses.append(address)
            # set our current address
            self.address = address
            return 0
            
        def setblocking(self, value):
            "Set the socket to be blocking or non-blocking"
            return self.setsockopt(socket.SOL_SOCKET, socket.SO_NONBLOCK, value)
    
        def debug_add_message(self, payload, source_address):
            "Debugging function to artificially add an incoming message to a socket"
            # create the tuple to store the message
            recv_tuple = (payload, source_address)
            # add data to the message queue
            if self.address in self.xbee.rx_messages.keys():
                self.xbee.rx_messages[self.address].append(recv_tuple)
            else:
                self.xbee.rx_messages[self.address] = [recv_tuple]
                
    
    class Node:
        "An object returned from a node discovery"
        
        def __init__(self, type = None, addr_extended = None, addr_short = None, addr_parent = None, profile_id = None, manufacturer_id = None, label = None):
            self.type = type
            """The node type ("coordinator", "router", or "end")"""
            self.addr_extended = addr_extended
            "64-bit colon-delimited extended hardware address"
            self.addr_short = addr_short
            "16-bit network assigned address"
            self.addr_parent = addr_parent
            "16-bit network parent address"
            self.profile_id = profile_id
            "node profile ID"
            self.manufacturer_id = manufacturer_id
            "node manufacturer ID"
            self.label = label
            "the nodes string label"
    
        def to_socket_addr(self, endpoint, profile_id, cluster_id, use_short):
            "Transform a node into a socket address tuple"
            if use_short:
                return [MAC_to_address_string(self.addr_short, 2), endpoint, profile_id, cluster_id]
            else:
                return [MAC_to_address_string(self.addr_extended), endpoint, profile_id, cluster_id]
    
        def __str__(self):
            "Print only the type and address of the node"
            return "<node type=%s addr_extended=%s>" % (self.type, self.addr_extended)
    
    #
    # socket and select keyword redirect
    #
    # The following is a bit of Python trickery that replaces functions in the socket and select modules
    # with functions in the zigbee module.  This allows functions calls like socket.socket() or select.select()
    # to actually call zigbee.zigbee_socket and zigbee.zigbee_select().
    
    original_select = select.select
    "Storage for the non-ZigBee type of Python select"
    SELECT_SLEEP_TIME = 0.05
    "Time to sleep in seconds between polls of the sockets"
    
    def zigbee_select(rlist, wlist, xlist, timeout = None):
        "Select which sockets are ready to read, write, and have exceptions"
        #TTDO: support xlist
        if timeout is not None:
            start_time = time.time()
    
        # various list variables
        rlist_nonzigbee = []
        wlist_nonzigbee = []
        xlist_nonzigbee = []
        rlist_zigbee = []
        wlist_zigbee = []
        rlist_out = []
        wlist_out = []
        xlist_out = []
        
        # split zigbee and non-zigbee sockets
        for sock in rlist:
            if sock.__class__ is ZigBee_Socket:   
                rlist_zigbee.append(sock)
            else:
                rlist_nonzigbee.append(sock)
        for sock in wlist:
            if sock.__class__ is ZigBee_Socket:   
                wlist_zigbee.append(sock)
            else:
                wlist_nonzigbee.append(sock)
        for sock in xlist:
            if sock.__class__ is not ZigBee_Socket:   
                xlist_nonzigbee.append(sock)
    
        # use the original select if no zigbee sockets
        if not len(rlist_zigbee) and not len(wlist_zigbee): 
            return original_select(rlist_nonzigbee, wlist_nonzigbee, xlist_nonzigbee)
        
        # flag if there are any non_zigbee sockets
        nonzigbee_socket = len(rlist_nonzigbee) or len(wlist_nonzigbee) or len(xlist_nonzigbee)
        
        # loop over zigbee and non-zigbee sockets
        first_loop = True
        while first_loop or (timeout is None or start_time + timeout >= time.time()):
            if first_loop:
                # immediately check for matches on the first loop
                first_loop = False
            else:
                # on subsequent loops, sleep between polls.
                time.sleep(min(SELECT_SLEEP_TIME, abs(start_time + timeout - time.time())))
                
            # check original sockets
            if nonzigbee_socket:
                rlist_out, wlist_out, xlist_out = original_select(rlist_nonzigbee, wlist_nonzigbee, xlist_nonzigbee, 0)
            
            # check ZigBee sockets
            for sock in rlist_zigbee:
                if sock._pending_message():
                    rlist_out.append(sock)  
            # zigbee sockets are always ready for write
            wlist_out.extend(wlist_zigbee)
        
            # check for any matches
            if len(rlist_out) or len(wlist_out) or len(xlist_out):
                break
        
        return  rlist_out, wlist_out, xlist_out
    
    # replace the original select with the zigbee select
    select.select = zigbee_select
    
    original_socket = socket.socket
    "Storage for the non-ZigBee type of Python socket"
    
    def zigbee_socket(family = socket.AF_ZIGBEE, type = socket.SOCK_DGRAM, proto = None, xbee = default_xbee):
        """Create either a normal socket or a ZigBee socket"""
        if family == socket.AF_ZIGBEE:
            return ZigBee_Socket(family, type, proto, xbee)
        else:
            if proto is None:
                return original_socket(family, type)
            else:
                return original_socket(family, type, proto)
    
    # replace the original socket with the zigbee_socket
    socket.socket = zigbee_socket
    # NOTE: SocketType will not be changed and will still refer to the non-ZigBee socket class.
    
    #
    # Configuration
    #
    try:
        import default_xbee_config
    except:
        pass  
        