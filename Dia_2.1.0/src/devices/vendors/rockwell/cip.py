
import time
import random
import types
import traceback

cip_id_class = 0x01

id_cls_getAttribAll = { "service" : 0x01, "class" : 0x01, "instance" : 0x01 }
cm_cls_UnconnSend = { "service" : 0x52, "class" : 0x06, "instance" : 0x01 }
cm_cls_FwdOpn = { "service" : 0x54, "class" : 0x06, "instance" : 0x01 }
cm_cls_FwdCls = { "service" : 0x4E, "class" : 0x06, "instance" : 0x01 }
pccc_exec  = { "service" : 0x4B, "class" : 0x67, "instance" : 0x01 }
pccc_VDHP  = { "service" : 0x4C, "class" : 0x67, "instance" : 0x01 }
pccc_local = { "service" : 0x4D, "class" : 0x67, "instance" : 0x01 }

pccc_TNS = 1

cip_vendor_id = 805 # this is Digi's!
cip_serial_number = 0x12345678
con_serial_number = random.randint(101,9999)

class cip_msg:
    'Manage a CIP message'
    version = 1.0

    def __init__( self):
        self.status = 0
        self.trace = False

    def buildServPath( self, dict):
        serv = dict.get("service", 0x01)
        svPath = chr( serv) # default = GetAllAttrib
        ePath = self.buildIoi( dict)
        svPath += chr(len(ePath)/2) + ePath

        # if( (serv >= 0x4B) and (serv <= 0x4D) ):
        #    svPath += self.buildPcccExec( dict)
        return svPath

    # from dict, build up the class+instance+?? path
    def buildIoi( self, dict):
        # dict["class"] is class to use (is required)
        # dict["instance"] is instance to use (is required)
        # dict["attribute"] is class to use (is optional)
        # dict["symbol"] to use symbolic segment, not logical
        # dict["padded"] can be null, True, or False (def is True)
        # dict["clas_size"] can be null, 8, 16 or 32 (def is 8-bit)
        # dict["inst_size"] can be null, 8, 16 or 32 (def is 8-bit)
        # dict["attr_size"] can be null, 8, 16 or 32 (def is 8-bit)
        ePath = ""
        # if self.trace: print "LogSeg Dict", dict
        padded = dict.get("padded", True)

        # check for Symbolic segment
        value = dict.get("symbol", None)
        if value is not None:
            # add symbolic segment
            ePath += self.buildSymbolicSegment(value, padded)

        else: # assume logical

            # Class Logical Segment
            value = dict.get("class", 0x01)
            ePath += self.buildLogicalSegment( 0x20, dict.get("clas_size", 8), value, padded)

            # Instance Logical Segment
            value = dict.get("instance", 0x01)
            ePath += self.buildLogicalSegment( 0x24, dict.get("inst_size", 8), value, padded)

            # Attribute Logical Segment
            value = dict.get("attribute", "")
            if( value != "" ):
                ePath += self.buildLogicalSegment( 0x30, dict.get("attr_size", 8), value, padded)

        if self.trace:
            print "ePath = ",
            for by in ePath:
                print "%02x " % ord(by),
            print
        return ePath

    # from dict, build up the class+instance+?? path
    def buildLogicalSegment( self, tag, size, value, padded):
        st = ""
        if( size == 16):
            # print "seg:16 tag:%02x val:%04x" % ( tag, value)
            tag += 0x01 # tag as 16-bit
            st+= chr( tag)
            if( padded):
                st+= chr( 0)
            if( value > 0xFFFF):
                raise "buildLogicalSegment() size 16-bit; value too big ", value
            st += chr( value % 0xFF)  # lo byte
            st += chr( value // 0xFF) # hi byte

        elif( size == 32):
            # print "seg:32 tag:%02x val:%04x" % ( tag, value)
            tag += 0x02 # tag as 16-bit
            st+= chr( tag)
            if( padded):
                st+= chr( 0)
            st += chr( value % 0xFF)  # lo byte
            value //= 0xFF
            st += chr( value % 0xFF)
            value //= 0xFF
            st += chr( value % 0xFF)
            value //= 0xFF
            st += chr( value % 0xFF)  # hi byte

        else:
            # print "seg:8 tag:%02x val:%04x" % ( tag, value)
            st+= chr( tag) # tag as 8-bit, no padded needed
            if( value > 0xFF):
                raise "buildLogicalSegment() size 8-bit; value too big ", value
            st += chr( value)

        return st

    def buildRoutePath( self, route):

        # route is a string consisting of these tokens:
        # "sN" by backplane to SLOT N
        # "pN" to this nodes PORT N
        # "nN" to Node/MAC N

        if self.trace: print 'see route ', route

        route = route.lower() # all to lower case
        path = ""

        for tok in route.split():
            link = int( tok[1:] )
            if self.trace: print "Token<%s> link<%d>" % (tok[0], link)

            if( tok[0] == 's'):
                # then SLOT segment
                path += chr( 0x01) + chr( link)

            elif( tok[0] == 'p'):
                # then PORT segment
                path += chr( link)

            elif( tok[0] == 'n'):
                # then NODE segment
                path += chr( link)

        return path

    # from dict, build up the class+instance+?? path
    def buildSymbolicSegment(self, symbol, padded=False):
        sym_len = len(symbol)
        if (sym_len == 0) or (sym_len >31):
            # then extended - not yet supported
            raise ValueError, "symbol length is outside range 1-31 bytes"

        if self.trace: print "seg:sym len:%d (%s)" % (sym_len, symbol)
        # st = chr(0x60 + sym_len)
        st = '\x91' + chr(sym_len) + symbol
        if (sym_len % 2):
            st += '\x00'

        return st

    def buildPcccExec( self, dict):
        global pccc_TNS
        global cip_vendor_id, cip_serial_number

        # start with header
        if( dict.get("service", 0x4B) == 0x4D):
            # then is PCCC local
            pccc = "" # no header

        elif( dict.get("service", 0x4B) == 0x4C):
            # then is Virtual DH+
            pccc = self.str_AddLE32( 0x00000100)
            pccc += self.str_AddLE32( 0)

        else:
            # else assume is PCCC_EXEC
            pccc_id = self.str_AddLE16( cip_vendor_id )
            pccc_id += self.str_AddLE32( cip_serial_number)
            pccc = chr( len(pccc_id)+1 ) + pccc_id

        if( dict.get("pccc", "485cif") == "485cif"):
            if( dict.get("pccc_func", "read") == "read"):
                pccc += chr( 0x01) # CMD CIF Read
            else:
                pccc += chr( 0x08) # CMD CIF Write
        else:
            pccc += chr( 0x0F) # CMD extended - see subfunc

        pccc += chr( 0x00) # STS
        pccc += self.str_AddLE16( pccc_TNS)
        pccc_TNS += 1
        if( pccc_TNS > 9999):
            pccc_TNS = 1

        if( dict.get("pccc", "485cif") == "485cif"):
            if( dict.get("pccc_func", "read") == "read"):
                pccc += self.str_AddLE16( 0) # offset address
                pccc += chr( 20)             # Size 20 bytes
            else:
                pccc += self.str_AddLE16( 5) # offset address
                time_st = time.strftime( "%H %M %S")
                for n in time_st.split():
                    pccc += self.str_AddLE16( int( n) )

        elif( dict.get("pccc", "485cif") == "slc5"):
            if( dict.get("pccc_func", "read") == "read"):
                pccc += chr( 0xA2)          # subfunc
                pccc += chr( 20)            # Size 10 words
                pccc += chr( 7)             # File Number
                pccc += chr( 0x89)          # File Type
                pccc += chr( 0)             # Elem number
                pccc += chr( 0)             # Sub-Elem number
            else:
                pccc += chr( 0xAA)          # subfunc
                pccc += chr( 6)             # Size 3 words
                pccc += chr( 7)             # File Number
                pccc += chr( 0x89)          # File Type
                pccc += chr( 5)             # Elem number
                pccc += chr( 0)             # Sub-Elem number
                time_st = time.strftime( "%H %M %S")
                for n in time_st.split():
                    pccc += self.str_AddLE16( int( n) )

        return pccc

    def buildUnconnectedSend( self, dict):
        # start with IOI to remote ConnMngr
        usnd = self.buildServPath( cm_cls_UnconnSend)

        # hard-code a timeout of about 5 seconds
        usnd += chr( 0x0A) # ticks to ~seconds
        usnd += chr( 0x09) # say 9 seconds

        # encap the CIP
        if( not dict.has_key( "cip") ):
            # then cip given here
            raise "CIP message to Unconn Send required!"

        cip = dict["cip"]
        usnd += self.str_AddLE16( len(cip) )
        usnd += cip
        if( (len(cip) % 2) != 0): # then add pad
            usnd += chr( 0)

        route = self.buildRoutePath( dict.get("route", "s0") )
        usnd += chr((len(route)+1)/2)
        usnd += chr(0) # reserved byte
        usnd += route
        if( (len( route) % 1) != 0): # then add pad
            usnd += chr( 0)

        return usnd

    def str_AddLE16( self, n): # convert 16-bit integer into 2xbyte
        st = chr( n % 256) + chr( (n >> 8) % 256)
        return st

    def str_AddLE32( self, n): # convert 32-bit integer into 4xbyte
        st = chr(n & 0xFF) + chr((n >> 8) & 0xFF) \
           + chr((n >> 16) & 0xFF) + chr((n >> 24) & 0xFF)
        return st

    def n_ParseLE16( self, st): # convert 16-bit integer into 2xbyte
        n = ord( st[0]) + (ord( st[1]) * 256)
        return n

    def n_ParseLE32( self, st): # convert 32-bit integer into 4xbyte
        n = ord( st[0]) + (ord( st[1]) << 8) \
            + (ord( st[2]) << 16) + (ord( st[3]) << 24)
        return n

    def printGetIdReply( self, rsp):

        print
        n = len( rsp)
        print "Full length of reply = %d (0x%04x)" % (n,n)
        print "         Reply Codes =", list( rsp[:4])

        if( rsp[2] != chr( 0x00) ):
            # then error!
            print "            GRC Code =", ord( rsp[2])
            print "      ERC word count =", ord( rsp[3])
            nErr = ord( rsp[3])
            i = 0
            erc = rsp[4:]
            while( i < nErr):
                n = self.n_ParseLE16( erc[0:2])
                print "         ERC Code[%d] = 0x%04X" % (i,n)
                if( len( erc) >= 2):
                    erc = erc[2:]
                else:
                    break
                i += 1

            return ord( rsp[2])

        n = self.n_ParseLE16( rsp[4:6])
        print "           Vendor Id = %d" % n

        n = self.n_ParseLE16( rsp[6:8])
        print "         Device Type = %d" % n

        n = self.n_ParseLE16( rsp[8:10])
        print "        Product Code = %d" % n

        print "     Major/Minor Rev = %d.%d" % ( ord(rsp[10]), ord(rsp[11]) )

        n = self.n_ParseLE16( rsp[12:14])
        print "              Status = %d (0x%04X)" % (n,n)

        n = self.n_ParseLE32( rsp[14:18])
        print "       Serial Number = %d (0x%08X)" % (n,n)

        n = ord( rsp[18])
        print " Len of Product Name = %d" % n
        print "        Product Name = <%s>" % rsp[19:]

        return ord( rsp[2])

def getOffsetToCip( eip_rsp):
    # assume eip_msg is full response message
    #print
    #print 'list of rsp', list( eip_rsp)
    if( len( eip_rsp) < 36):
        print "rsp is too short"
        return -1

    # fetch item count
    nOffset = 30
    if( ord(eip_rsp[nOffset]) < 2):
        print "item count isn't in correct offset"
        return -2

    # fetch address length - ignore type
    nOffset = 34
    n = ord(eip_rsp[nOffset])
    nOffset += (2 + n)

    # fetch data type
    n = ord(eip_rsp[nOffset])
    if( n == 0xB2):
        nOffset += 4 # offset to GRC
    elif( n == 0xB1):
        nOffset += 6 # offset to GRC
    else:
        return -3

    return nOffset

def getResponseCode( eip_rsp):
    # assume eip_msg is full response message

    # locate CIP response
    grc = getOffsetToCip( eip_rsp)
    if( grc > 0):
        #
        grc = ord(eip_rsp[grc+2])
    return grc

def print_bytes( msg, bytes):
    print msg,
    nOffset = getOffsetToCip( bytes)
    if( nOffset <= 0):
        print "bad message", bytes
    for ch in bytes[nOffset:]:
        print ("%02X " % ord(ch)),
    print

class cip_conn:
    'Manage a CIP connection'
    version = 1.0

    def __init__( self):
        self.status = False
        self.cip_obj = cip_msg()
        self.myConSerNum = 0
        # conPath = { "class": 0x02, "instance": 0x01, "route": "s0"}
        self.conPathLst = { "class": 0x02, "instance": 0x01, "route": ""}
        self.conid_O2T = 0   # srv requested id (we use to them)
        self.conid_T2O = 0   # cli requested id (we expect from them)

    def isConnected( self):
        return( self.status)

    def assignNewConnSerNum( self):
        global con_serial_number

        con_serial_number += 1
        if( con_serial_number > 9999):
            con_serial_number = 101
        # self.myConSerNum = con_serial_number
        return con_serial_number

    def buildConnInfo( self):
        global cip_vendor_id, cip_serial_number, con_serial_number

        st = self.cip_obj.str_AddLE16( self.myConSerNum)
        st += self.cip_obj.str_AddLE16( cip_vendor_id)
        st += self.cip_obj.str_AddLE32( cip_serial_number)
        return st

    def buildConnPath( self, wantPad, dict):
        tmpLst = self.conPathLst
        tmpLst.update( dict)
        path = self.cip_obj.buildRoutePath( tmpLst.get("route", ""))
        path += self.cip_obj.buildIoi( tmpLst)
        st = chr((len(path)+1)/2)
        if( wantPad):
            st += chr(0) # reserved byte
        st += path
        if( (len( path) % 1) != 0): # then add pad
            st += chr( 0)
        return st

    def buildForwardOpen( self, dict):
        # start with a new conn serial number
        self.myConSerNum = self.assignNewConnSerNum()

        # start with IOI to remote ConnMngr
        # cm_cls_FwdOpn = { "service" : 0x54, "class" : 0x06, "instance" : 0x01 }
        st = self.cip_obj.buildServPath( cm_cls_FwdOpn)

        # hard-code a timeout of about 5 seconds
        st += chr( 0x0A) # ticks to ~seconds
        st += chr( 0x09) # say 9 seconds

        #conid_O2T = 0   # srv requested id (we use to them)
        self.conid_T2O = self.assignNewConnSerNum()

        #print 'O2T:%s T2O:%s' % (self.conid_O2T, self.conid_T2O)
        if isinstance(self.conid_O2T, types.StringType):
            st += self.conid_O2T
        else:
            st += self.cip_obj.str_AddLE32(self.conid_O2T)
        if isinstance(self.conid_T2O, types.StringType):
            st += self.conid_T2O
        else:
            st += self.cip_obj.str_AddLE32(self.conid_T2O)

        # append conn sn, vend id,
        st += self.buildConnInfo()
        # self.myConSerNum = self.assignNewConnSerNum()

        st += chr( 4) # connection multiplier
        st += chr( 0) + chr( 0) + chr( 0) # reserved

        st += self.cip_obj.str_AddLE32( 0x000493E0)
        st += self.cip_obj.str_AddLE16( 0x420A)
        st += self.cip_obj.str_AddLE32( 0x000493E0)
        st += self.cip_obj.str_AddLE16( 0x4240)

        st += chr( 0xA3) # transport trigger

        # append connection path
        st += self.buildConnPath( False, dict)

        return st

    def buildForwardClose( self, dict):
        # start with IOI to remote ConnMngr
        # cm_cls_FwdCls = { "service" : 0x4E, "class" : 0x06, "instance" : 0x01 }
        st = self.cip_obj.buildServPath( cm_cls_FwdCls)

        # hard-code a timeout of about 5 seconds
        st += chr( 0x0A) # ticks to ~seconds
        st += chr( 0x09) # say 9 seconds

        # append conn sn, vend id,
        st += self.buildConnInfo()

        # append connection path
        st += self.buildConnPath( True, {} )

        return st

    def parseForwardOpenReply( self, rsp):

        print "Parse Forward Open Response:"

        if( not rsp or (len(rsp) != 70)):
            print "bad length!"
            self.status = False
            return False

        #if( rsp[:2] != (chr(0x6F) + chr( 0))):
        #    print "bad command!"
        #    self.status = False
        #    return False

        #if( self.n_ParseLE32( rsp[8:12])!= 0):
        #    print "bad status!"
        #    self.status = False
        #    return False

        # ignore the rest

        self.conid_O2T = rsp[0x2C:0x30]
        print "O2T = ", list( self.conid_O2T)

        # t2o = rsp[0x30:0x34]

        # n = self.n_ParseLE32( rsp[4:8])
        #self.session = n
        #print "new Session Handle = %d (0x%08x)" % (n,n)

        return True


# these 2 just for counting self-test errors
global nGood, nError

if __name__ == '__main__':
    global nGood, nError

    print "Running test of CIP routines"
    nGood = 0
    nError = 0

    cip = cip_msg()
    prm = {}

    print

    prm.update( id_cls_getAttribAll)
    idReq = cip.buildServPath( prm)
    print "Id GetAllAttrib:",
    for ch in idReq:
        print ("%02X " % ord(ch)),
    print

    prm.update( cm_cls_UnconnSend)
    UcSndReq = cip.buildServPath( prm)
    print "ConMgr UnconnSend:"
    for ch in UcSndReq:
        print ( " %02X" % ord(ch)),
    print

    spath = "s0"
    bpath = cip.buildRoutePath( spath)
    print "Route(%s):" % spath
    for ch in bpath:
        print ( " %02X" % ord(ch)),
    print

    spath = "s7 p3 n17"
    bpath = cip.buildRoutePath( spath)
    print "Route(%s):" % spath
    for ch in bpath:
        print ( " %02X" % ord(ch)),
    print

    prm.update( id_cls_getAttribAll)
    prm.update( { "cip": idReq, "route" : "s0"})
    UcSndReq = cip.buildUnconnectedSend( prm)
    print "UnconSnd to Slot0 Id GetAllAttrib :"
    for ch in UcSndReq:
        print ( " %02X" % ord(ch)),
    print

    prm.update( pccc_exec)
    prm.update( { "pccc" : "485cif", "pccc_func" : "read" } )
    plc2 = cip.buildServPath( prm)
    print "PCCC 485CIF Read :"
    for ch in plc2:
        print ( " %02X" % ord(ch)),
    print

    prm.update( pccc_exec)
    prm.update( { "pccc" : "485cif", "pccc_func" : "write" } )
    plc2 = cip.buildServPath( prm)
    print "PCCC 485CIF Write :"
    for ch in plc2:
        print ( " %02X" % ord(ch)),
    print

    prm.update( pccc_VDHP)
    prm.update( { "pccc" : "slc5", "pccc_func" : "read" } )
    plc2 = cip.buildServPath( prm)
    print "PCCC SLC500 Read :"
    for ch in plc2:
        print ( " %02X" % ord(ch)),
    print

    prm.update( pccc_VDHP)
    prm.update( { "pccc" : "slc5", "pccc_func" : "write" } )
    plc2 = cip.buildServPath( prm)
    print "PCCC SLC500 Write :"
    for ch in plc2:
        print ( " %02X" % ord(ch)),
    print

    print
    print "Finished test, good = %d, error = %d" % (nGood, nError)

