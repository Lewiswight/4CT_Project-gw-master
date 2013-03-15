
# set trace state=on mask=ia:info+debug+warning

import socket
import time
import traceback

import cip

def_prm = { }

eip_cmds = { "nop" : 0x00,
             "list_targets" : 0x01,
             "list_services" : 0x04,
             "list_identity" : 0x63,
             "list_interfaces" : 0x64,
             "register_session" : 0x65,
             "unregister_session" : 0x66,
             "send_rr_data" : 0x6F,
             "send_unit_data" : 0x70 }

EIP_PORT = 0xAF12

class eip_client:
    'Lynn"s Ethernet/IP Tester Code'
    version = 1.0

    PING_THRESHOLD = 60.0

    def __init__( self):
        self.session = 0    # means we have NO session
        self.status = 0
        self.name = "eipc"
        self.sock = None
        self.attrib = {'port':EIP_PORT, "tout":20.0, 'context':"EIP_TEST"}
        self.cip_obj = cip.cip_msg()
        # create 4 connection objects
        self.con = []
        self.con.append( cip.cip_conn())
        self.con.append( cip.cip_conn())
        self.con.append( cip.cip_conn())
        self.con.append( cip.cip_conn())
        self.num_con = 4
        self.last_message = 0

        self.trace = False
        self.cip_obj.trace = self.trace
        return

    def getContext(self):
        return self.attrib['context']

    def getIp(self):
        return self.attrib['ip']

    def getName( self):
        return self.attrib['name']

    def getPort(self):
        return self.attrib['port']

    def getTout(self):
        return self.attrib['tout']

    def setName( self, name):
        self.attrib['name'] = name

    def updateFromDict( self, dict=None):
        if dict is not None:
            if( dict.has_key( "ip") ):
                self.attrib['ip'] = dict["ip"]

            if( dict.has_key( "port") ):
                self.attrib['port'] = dict["port"]

            if( dict.has_key( "session") ):
                self.session = dict["session"]

            if( dict.has_key( "status") ):
                self.status = dict["status"]

            if( dict.has_key( "context") ):
                tmp = dict["context"] + "        "
                self.attrib['context'] = tmp[:8]

        return

    ## network overloading
    def isOpen(self):
        return self.sock is not None

    def open(self):

        if self.trace:
            print "EIPC: open to IP:%s TCP:%d" % (self.attrib["ip"], self.attrib["port"])

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.getTout())
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        try:
            self.sock.connect( (self.getIp(), self.getPort()) )
            self.last_message = time.time()
            return True

        except socket.timeout:
            if self.trace:
                print "EIPC: open failed - timeout. Target is offline?"

        except:
            if self.trace:
                print "EIPC: open failed"
            traceback.print_exc()

        self.sock = None
        return False

    def send( self, st):
        if self.isOpen():
            try:
                self.sock.send(st)
                self.last_message = time.time()
                return len(st)
            except:
                # print "exc:send "
                self.sock = None
                return -1
        else:
            print ">>>> Error, socket NOT open!"
            return -1

    def recv(self, max):
        if self.isOpen():
            try:
                rtn = self.sock.recv( max)
                self.last_message = time.time()
                return rtn
            except:
                if( self.attrib.get( "no_data_cls", False) == False):
                    # no data is NOT an error
                    return
                else: # else no data is error, close socket
                    self.sock = None
                    return -1
        else:
            print ">>>> Error, socket NOT open!"
            return -1

    def flush( self):
        # do nothing for now
        return

    def close(self):
        if self.isOpen():
            time.sleep( 1.0)
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        self.session = 0
        return 0


    def ping(self, x_context=None):
        """Force encap to test itself"""
        if (time.time() - self.last_message) > self.PING_THRESHOLD:
            msg = self.buildNOP(0, x_context)

        return True

    ## EIP Encap Routines

    # build a message - UCMM, CM3, etc as appropriate
    def build( self, x_prm):
        use_con = x_prm.get( "use_con", -1)
        if( (use_con >= 0) and (use_con < self.num_con)):
            return self.buildCM3( x_prm)

        elif( self.haveRegisteredSession( )):
            return self.buildUCMM( x_prm)
        return "???"

    def buildHeader( self, data, x_prm):

        # import any new settings
        self.updateFromDict( x_prm)

        # EIP Encap command
        cmd = x_prm.get( "command", "nop")
        if( not eip_cmds.has_key( cmd) ):
            raise "bad EIP command!"
        eip_hdr = self.str_AddLE16( eip_cmds[cmd])

        # EIP Encap attached data length
        if( not data):
            len_data = 0
        else:
            len_data = len( data)
        eip_hdr += self.str_AddLE16( len_data)

        # EIP Encap Session Handle
        eip_hdr += self.str_AddLE32( self.session)

        # EIP Encap Status
        eip_hdr += self.str_AddLE32( self.status)

        # EIP Encap Sender Context
        eip_hdr += self.getContext()

        # EIP Encap Options
        eip_hdr += self.str_AddLE32( 0)

        # print "EIP Hdr, len=%d" % len(eip_hdr)
        # print list( eip_hdr)

        eip_hdr += data

        return eip_hdr

    def buildNOP( self, data_len, x_prm=None):
        # build a NOP
        if( data_len == 0):
            st = ""
        else:
            st = '@' * data_len
            if self.trace:
                print st
                print len(st)
        return self.buildHeader( st, { "command" : "nop" } )

    def buildListIdentity( self, x_prm=None):
        # build a NOP
        st = "" # there is NO attached data for this command
        return self.buildHeader( st, { "command" : "list_identity" } )

    def buildListTargets( self, x_prm=None):
        # build a NOP
        st = "" # there is NO attached data for this command
        return self.buildHeader( st, { "command" : "list_targets" } )

    def buildListInterfaces( self, x_prm=None):
        # build a NOP
        st = "" # there is NO attached data for this command
        return self.buildHeader( st, { "command" : "list_interfaces" } )

    def buildListServices( self, x_prm=None):
        # build a NOP
        st = "" # there is NO attached data for this command
        return self.buildHeader( st, { "command" : "list_services" } )

    def OpenSession( self, x_prm=None):
        # register a session

        if( self.session != 0):
            print "Warning: session %d already open?" % self.session
            self.session = 0

        # import any new settings
        self.updateFromDict(x_prm)

        if self.trace: print 'opening EIP Session'
        if not self.isOpen():
            self.open()

        if not self.isOpen():
            return 0

        req = self.buildRegisterSession()
        if self.trace:
            print_bytes( "Reg Session Req:", req)
            self.printHeader(req)

        self.send(req)
        rsp = self.recv( 1024)
        # print_bytes( "Reg Session Rsp:", rsp)
        self.parseRegisterSessionReply(rsp)
        return(self.session)

    def buildRegisterSession(self, x_prm=None):

        # build data first
        # add protocol version = 1 or LE is '\x01\x00'
        # add protocol options = 0 or LE is '\x00\x00'

        # append to EIP Header
        reg_sess = self.buildHeader( '\x01\x00\x00\x00', \
                        { "command" : "register_session" } )

        return reg_sess

    def parseRegisterSessionReply(self, rsp):

        if self.trace: print "Parse Register Session Response:",

        if( not rsp or (len(rsp) != 28)):
            if self.trace: print "bad length!"
            self.session = 0
            return False

        if( self.n_ParseLE16( rsp[:2])!= 0x65):
            if self.trace: print "bad command!"
            self.session = 0
            return False

        if( self.n_ParseLE32( rsp[8:12])!= 0):
            if self.trace: print "bad status!"
            self.session = 0
            return False

        # ignore the rest

        n = self.n_ParseLE32( rsp[4:8])
        self.session = n
        if self.trace: print "new Session Handle = %d (0x%08x)" % (n,n)

        return True

    def haveRegisteredSession( self):
        return( self.session != 0)

    def buildUnregisterSession( self, x_prm):
        # there is NO attached data for this command
        return self.buildHeader( '', { "command" : "unregister_session" } )

    def str_AddLE16( self, n): # convert 16-bit integer into 2xbyte
        st = chr( n % 256) + chr( (n >> 8) % 256)
        return st

    def str_AddLE32( self, n): # convert 32-bit integer into 4xbyte
        st = chr( n % 256) + chr( (n >> 8) % 256) \
           + chr( (n >> 16) % 256) + chr( (n >> 24) % 256)
        return st

    def n_ParseLE16( self, st): # convert 16-bit integer into 2xbyte
        n = ord( st[0]) + (ord( st[1]) * 256)
        return n

    def n_ParseLE32( self, st): # convert 32-bit integer into 4xbyte
        n = ord( st[0]) + (ord( st[1]) << 8) \
            + (ord( st[2]) << 16) + (ord( st[3]) << 24)
        return n

    def printHeader( self, eip_hdr):

        print
        n = len( eip_hdr)
        print "  Full length of EIP = %d (0x%04x)" % (n,n)

        cmd = self.n_ParseLE16( eip_hdr[:2])
        print "         EIP Command =",
        if( cmd == 0):
            print "NOP"
        elif( cmd == 0x01):
            print "List Targets"
        elif( cmd == 0x04):
            print "List Services"
        elif( cmd == 0x63):
            print "List Identity"
        elif( cmd == 0x64):
            print "List Interfaces"
        elif( cmd == 0x65):
            print "Register Session"
        elif( cmd == 0x66):
            print "Unregister Session"
        else:
            print "Unknown command: 0x%02x" % cmd

        nAttachedData = self.n_ParseLE16( eip_hdr[2:4])
        print "Attached Data Length = %d" % nAttachedData

        n = self.n_ParseLE32( eip_hdr[4:8])
        print "      Session Handle = %d (0x%08x)" % (n,n)

        n = self.n_ParseLE32( eip_hdr[8:12])
        print "      Session Status = %d (0x%08x)" % (n,n)

        print "      Sender Context =", list(eip_hdr[12:20])

        n = self.n_ParseLE32( eip_hdr[20:24])
        print "    Protocol Options = %d (0x%08x)" % (n,n)

        if( nAttachedData > 0):
            if( nAttachedData < 500):
                print "data =", list(eip_hdr[24:])
            else:
                print "attached data is longer than 500 bytes"

        return

    # build UCMM (unconnected message)
    def buildCM3( self, x_prm):

        # first build the CIP portion
        x_prm.update( { "cip_mode": "cm3" } )
        cpf = self.buildCPF( x_prm)

        if self.trace: print_bytes( "CPF:", cpf)

        # 32-bit interface handle MUST be zero
        msg = self.buildHeader( cpf, { "command" : "send_unit_data" } )

        return msg

    # build UCMM (unconnected message)
    def buildUCMM(self, x_prm):

        # first build the CIP portion
        x_prm.update( { "cip_mode": "ucmm" } )
        cpf = self.buildCPF( x_prm)

        # 32-bit interface handle MUST be zero
        msg = self.buildHeader( cpf, { "command" : "send_rr_data" } )

        return msg

    def buildCPF( self, x_prm):
        # 32-bit interface handle MUST be zero
        msg = self.str_AddLE32( 0)

        # 16-bit timeout, default to 10 seconds
        msg += self.str_AddLE16( x_prm.get( "eip_to", 10) )

        # 16-bit item count
        msg += self.str_AddLE16( 2)

        # 16-bit Address item type id & length (NULL type)
        mode = x_prm.get( "cip_mode", "ucmm")
        if self.trace: print "mode = ", mode
        if( mode in [ "cm", "cm3" ] ):
            # then connected messaging - special address item
            msg += self.str_AddLE16( 0xA1)
            msg += self.str_AddLE16( 4)

            # handle the conn
            use_con = x_prm.get( "use_con", 0)
            # msg += self.str_AddLE32( self.con[use_con].getConId() )
            msg += self.con[use_con].conid_O2T

            # 16-bit Data item type id
            msg += self.str_AddLE16( 0xB1) # CM
            cip = self.buildCPF_CipData( x_prm)
            msg += self.str_AddLE16( len(cip) + 2 ) # add length
            # add seq number
            sn = self.con[use_con].assignNewConnSerNum()
            msg += self.str_AddLE16( sn)
            msg += cip

        elif( mode == "epic"):
            # then connected messaging - special address item
            msg += self.str_AddLE16( 0x85)
            dst_ip = x_prm.get( "ip", "10.20.20.111")
            dst_ip += chr( 0) # add null term?
            msg += self.str_AddLE16( len( dst_ip))
            msg += dst_ip

            # 16-bit Data item type id
            msg += self.str_AddLE16( 0x91) # EPIC

            # use PCCC 'local' to simulate EPIC
            x_prm.update( { "service" : 0x4D } )

            if( x_prm.has_key( "cip") ):
                # then cip (or PCCC) given here
                epic = x_prm["cip"]
            else:
                # else build a simple PCCC packet
                epic = self.cip_obj.buildPcccExec( x_prm)
            msg += self.str_AddLE16( len(epic) )
            msg += epic

        else: # ucmm
            # else unconnected messaging - NULL address item
            msg += self.str_AddLE16( 0) # type is NULL
            msg += self.str_AddLE16( 0) # length is ZERO

            # 16-bit Data item type id
            msg += self.str_AddLE16( 0xB2) # UCMM type
            cip = self.buildCPF_CipData( x_prm)
            msg += self.str_AddLE16( len(cip) ) # add length
            msg += cip

        return msg

    def buildCPF_CipData( self, x_prm):
        # build CIP portion of CPF data portion
        if(x_prm.has_key( "cip") ):
            # then cip given here
            if self.trace: print 'build_cip'
            cip = x_prm["cip"]

        elif(x_prm.has_key( "symbol") ):
            # then cip given here
            if self.trace: print 'build symbol'
            cip = self.cip_obj.buildServPath(x_prm)
            cip += self.str_AddLE16(1)

        else:
            # else build a simple IOI path only
            cip = self.cip_obj.buildServPath( x_prm)

        if( x_prm.has_key( "appdata") ):
            # append any application data
            cip += x_prm["appdata"]

        return cip

    def breakupCPF(self, buf):
        encap = ''
        addr = ''
        data = ''
        payl = ''

        x = self.n_ParseLE16(buf)
        if x == 0x6F:
            # print 'send_rr_data response'
            encap = buf[:24]
            buf = buf[24:]
            x = self.n_ParseLE32(encap[8:12])
            if x != 0:
                if self.trace:
                    print "Encap Status Error = %d (0x%08x)" % (x,x)
                return encap, addr, data, payl

        elif x == 0x70:
            # print 'send_unit_data response'
            encap = buf[:24]
            buf = buf[24:]
            x = self.n_ParseLE32(encap[8:12])
            if x != 0:
                if self.trace:
                    print "Encap Status Error = %d (0x%08x)" % (x,x)
                return encap, addr, data, payl

        elif x == 0:
            # print 'assume is CPF already'
            # no change to encap, buf
            pass

        else:
            if self.trace:
                print "CPF is of unknown form"
            return encap, addr, data, payl

        # 16-bit item count
        x = self.n_ParseLE16(buf[6:])
        if x != 2:
            if self.trace:
                print_bytes('item cnt not 2', buf[6:])
            return encap, addr, data, payl
        buf = buf[8:]

        # 16-bit Address item type id & length (NULL type)
        x = self.n_ParseLE16(buf[:2])
        if x == 0xA1:
            # then connected messaging, 2 + 2 + 4 bytes
            # print 'connected message address item'
            addr = buf[:8]
            buf = buf[8:]

        elif x == 0:
            # then connected messaging, 2 + 2 + 0 bytes
            # print 'unconnected message address item'
            addr = buf[:4]
            buf = buf[4:]

        else:
            if self.trace:
                print_bytes('unknown address item', buf)
            return encap, addr, data, payl

        # 16-bit Data item type id & length (NULL type)
        x = self.n_ParseLE16(buf[:2])
        if x == 0xB1:
            # then connected messaging, 2 + 2 + 2
            # print 'connected message data item'
            data = buf
            buf = buf[6:]

        elif x == 0xB2:
            # then unconnected messaging, 2 + 2 + 0 bytes
            # print 'unconnected message data item'
            data = buf
            buf = buf[4:]

        else:
            if self.trace:
                print_bytes('unknown data item', buf)
            return encap, addr, data, payl

        if buf[0] == '\xCB':
            # pccc_exec
            payl = buf[11:]
        elif buf[0] == '\xCC':
            # pccc_virtual_DHP
            payl = buf[12:]
        elif buf[0] == '\xCD':
            # pccc_local
            payl = buf[4:]
        else:
            if self.trace:
                print_bytes('unknown payload', buf)

        return encap, addr, data, payl

    def OpenConnection( self, x_prm):
        # register a session

        if( self.session == 0):
            self.OpenSession( x_prm)

        if( self.session == 0):
            print "Warning: session could not be registered?"
            return false

        use_con = x_prm.get( "use_con", 0)
        if( use_con == -1):
            # use next available ...
            i = 0
            while( i < self.num_con):
                if( not self.con[i].isConnected() ):
                    use_con = i
                i += 1
            if( use_con >= self.num_con):
                raise "too many connections open"

        if self.trace: print 'opening CIP Connection[%d]' % use_con

        st = self.con[use_con].buildForwardOpen( x_prm )

        # ST is just the raw CIP, so we feed in as ["cip"]
        x_prm.update( { "cip_mode": "ucmm", "cip" : st } )
        cpf = self.buildCPF( x_prm)

        # 32-bit interface handle MUST be zero
        msg = self.buildHeader( cpf, { "command" : "send_rr_data" } )

        if self.trace: print_bytes( "FwdOpen Req:", msg)

        self.send( msg)
        rsp = self.recv( 150)
        if self.trace: print_bytes( "Reg Session Rsp:", rsp)
        self.con[use_con].parseForwardOpenReply( rsp)
        x_prm.update( { "cip_mode": "cm3" } )

        return( self.con[use_con].isConnected() )

    def CloseConnection( self, x_prm):

        use_con = x_prm.get( "use_con", 0)
        if( use_con == -1):
            # use next available ...
            i = 0
            while( i < self.num_con):
                if( self.con[i].isConnected() ):
                    use_con = i
                i += 1
            if( use_con >= self.num_con):
                raise "too many connections open"

        if self.trace: print 'closing CIP Connection[%d]' % use_con
        st = self.con[use_con].buildForwardClose( x_prm )

        # ST is just the raw CIP, so we feed in as ["cip"]
        x_prm.update( { "cip_mode": "ucmm", "cip" : st } )
        cpf = self.buildCPF( x_prm)

        # 32-bit interface handle MUST be zero
        msg = self.buildHeader( cpf, { "command" : "send_rr_data" } )

        if self.trace: print_bytes( "FwdCls Req:", msg)

        self.send( msg)
        rsp = self.recv( 150)
        if self.trace: print_bytes( "FwdClose Rsp:", rsp)

        self.con[use_con].status = False
        self.con[use_con].conid_O2T = 0
        self.con[use_con].conid_T2O = 0

        return( self.con[use_con].isConnected() )

    # CIP Connection info
    def openCipConn( self, x_prm):
        if( not self.isOpen() ):
            if self.trace: print "CIP Conn Failed - No Session"
            return -1

        nCon = len( self.conn) + 1

        con = cip.cip_conn()


def print_bytes( msg, bytes):
    print msg
    for ch in bytes:
        print ("%02X " % ord(ch)),
    print
