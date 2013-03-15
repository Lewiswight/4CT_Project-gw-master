# Simple PCCC App Data Unit Class

import random
import types

# codes to use for the message class
# cif = PLC2 / Common-Interchange-File; unprotected rd/wr
# slc = protected rd/wr with 3-address; sub-fnc A2/AA/AB
# plc3 = word range read/write; sub-fnc 00/01
# plc5 = typed read/write; sub-fnc 67/68
msg_cls = { 'cif' : 1, 'slc' : 2, 'range' : 3 }

# codes to use for PLC addressing forms
# 2adr = SLC500 for 2-address (not 3); sub-fnc A1/A9
# plc3 = PLC3/5; 0x3C form
# plc5 = PLC3/5; 0x07 form
# asc = PLC3/5; "$N7:0" form
msg_adr = { '2adr' : 1, 'plc3' : 2, 'plc5' : 3, 'asc' : 4 }

# codes to use for the message function
msg_fnc = { 'read' : 1, 'write' : 2 }

# codes to use for the message data type
msg_typ_code = { 'B' : 0x85, 'N' : 0x89, 'F' : 0x8A, 'ST' : 0x8D }
msg_typ_size = { 'B' : 2, 'N' : 2, 'F' : 4, 'ST' : 84 }

TNS_MIN = 0x0010
TNS_MAX = 0x7FFF

def getTNS(xdct):
    # get TNS - no incr
    if not xdct.has_key('tns'):
        # create a base TNS value
        xdct['tns'] = random.randint(TNS_MIN,TNS_MAX)
    return xdct['tns']

def getNextTNS(xdct):
    # get next TNS and incr/roll TNS
    tns = getTNS(xdct)
    xdct['tns'] = tns + 1
    if xdct['tns'] > TNS_MAX:
        # roll back over to min
        xdct['tns'] = TNS_MIN
    return tns

def getNextTNS_str(xdct):
    # get TNS as 2-byte little-endian string
    tns = getNextTNS(xdct)
    st = chr(tns % 256) + chr(tns / 256)
    return st

def getFileType(st):
    """Given string like 'N7' or 'ST25', return 'N' or 'ST'
    """
    if isinstance(st, types.StringType) and len(st) > 0:
        # must be string and not empty/''

        if (st[-1] == ':') or (st[-1] == '.'):
            # then malformed of "N7:10.1" as "N7:" or "N7:10."
            return None

        st = st.upper()
        if msg_typ_code.has_key(st):
            # then was direct, st = a name like 'N' or 'ST'
            return st

        if (len(st) > 2) and msg_typ_code.has_key(st[:2]):
            # then was form like "ST10", return "ST"
            return st[:2]

        if (len(st) > 1) and msg_typ_code.has_key(st[0]):
            # then was form like "F12", return "F"
            return st[0]

    # else was unknown
    return None

def getSlc5FileTypeCode(st):
    """Given string like 'N7' or 'ST25', return 0x89 and so on
    """
    typ = getFileType(st)
    if typ is not None:
        return msg_typ_code[typ]
    else:
        return None

def getFileTypeSize(st):
    """Given string like 'N7' or 'ST25', return 'N' or 'ST'
    """
    typ = getFileType(st)
    if typ is not None:
        return msg_typ_size[typ]
    else:
        return None

def getFileNumber(st):
    """Given string like 'N7:23' or 'ST25', return 7 or 25
    """
    if isinstance(st, types.IntType):
        return st

    fil_typ = getFileType(st)

    if fil_typ is not None:

        # chop off the fil_typ chars, "N7:2" > "7:2"
        st = st[len(fil_typ):]

        if len(st) > 0:
            n = st.find( ":")
            if( n >= 0):
                # chop off any trailing element offset info
                st = st[:n]

            return  int(st)

    return None

def getElemOffset(st):
    """Given string like 'N7:15' or 'ST25', return 15 or 0
    """
    if isinstance(st, types.IntType):
        return st

    fil_typ = getFileType(st)

    if fil_typ is not None:

        if len(fil_typ) == len(st):
            # then malformed as "N" or "ST"
            return None

        # return any elem offset, assume zero/0 if none
        n = int(st.find( ":"))
        if n >= 0:
            # then found, incr past the ':'
            n += 1
            st = st[n:]

            # now might be "0" or "0.xx"
            n = int(st.find("."))
            if (n >= 0):
                # then found, chop off sub-element part
                return int(st[:n])

            return int(st)

        # not found - is "N7" assume zero/0/start of file
        return 0

    return None

def getSubElemOffset(st):
    """Given string like 'N7:15.2' or 'ST25:0.1', return 2 or 1
    """
    if isinstance(st, types.IntType):
        return st

    fil_typ = getFileType(st)

    if fil_typ is not None:
        # then atleast string (maybe) and starts valid

        if len(fil_typ) == len(st):
            # then malformed as "N" or "ST"
            return None

        # return any elem offset, assume zero/0 if none
        n = st.find( ":")
        if n >= 0:
            # then found, incr past the ':'
            n += 1
            st = st[n:]

            # now might be "0" or "0.xx"
            n = st.find(".")
            if (n >= 0):
                # then found, chop off sub-element part
                return int(st[n+1:])

        # not found - is "N7" assume zero/0/start of file
        return 0

    return None

def prepareSlcClean(xdct):
    """\
    Confirm xdct has the expected items

    Expected tags within xdct:
    xdct['cnt'] = element count
    xdct['elm'] (unless 'typ'/'num'/'ofs' exist) str like "N7:0"
    """

    if not xdct.get('slc_clean', False):
        # then this xdct has NOT been cleaned yet

        # expand out the address field if required
        if not xdct.has_key('typ'):
            # get the file type such as 'N' or 'ST'
            xdct['typ'] = getFileType(xdct['elm'])
        if not xdct.has_key('num'):
            # get the file number such as 7 or 23 (from N7/ST23)
            xdct['num'] = getFileNumber(xdct['elm'])
        if not xdct.has_key('ofs'):
            # get the element offset within the file
            xdct['ofs'] = getElemOffset(xdct['elm'])
        if not xdct.has_key('sub_elm'):
            # get the element offset within the file
            xdct['sub_elm'] = getSubElemOffset(xdct['elm'])
        if not xdct.has_key('typ_siz'):
            # get the byte size of the elements
            xdct['typ_siz'] = getFileTypeSize(xdct['elm'])

        if not xdct.has_key('cnt'):
            # get the element count - assume 1 if none
            xdct['cnt'] = 1

        if not xdct.has_key('dst'):
            # force in a destination byte
            xdct['dst'] = 1
        if not xdct.has_key('src'):
            # force in a source byte
            xdct['src'] = 0

        if not xdct.has_key('tns'):
            # create a base TNS value
            xdct['tns'] = random.randint(100,9999)

        xdct['slc_clean'] = True

    return

def makeSlcAddress(xdct):
    """\
    Create the 5-byte string (3-address form) with the "byte+num+type+elem+sub" format

    Expected tags within xdct:
    xdct['cnt'] = element count
    xdct['elm'] (unless 'typ'/'num'/'ofs' exist) str like "N7:0"
    xdct['2adr'] = True for the shorter 2-address form
    """

    # expand out the address field if required
    prepareSlcClean(xdct)

    if xdct.get('2adr',False):
        # two address, so no sub-element value
        st = chr(xdct['typ_siz'] * xdct['cnt']) + \
             chr(xdct['num']) +\
             chr(getSlc5FileTypeCode(xdct['typ'])) +\
             chr(xdct['ofs'])
    else:
        # three address, so include sub-element value
        st = chr(xdct['typ_siz'] * xdct['cnt']) + \
             chr(xdct['num']) +\
             chr(getSlc5FileTypeCode(xdct['typ'])) +\
             chr(xdct['ofs']) + chr(xdct['sub_elm'])

    return st

def makeSlcProtectedTypesLogicalRead(xdct):

    # expand out the address field if required
    adr = makeSlcAddress(xdct)

    if xdct.get('2adr',False):
        # create the SLC5 read with 2-address fields
        st = '\x0F' + '\x00' + getNextTNS_str(xdct) + '\xA1' + \
            makeSlcAddress(xdct)
    else:
        # create the SLC5 read with 3-address fields
        st = '\x0F' + '\x00' + getNextTNS_str(xdct) + '\xA2' + \
            makeSlcAddress(xdct)
    # print show_bytes('slc_rd', st)
    return st

def getData_SlcProtectedTypesLogicalRead(buf):

    if buf[0] != '\x4F':
        print 'bad PCCC format'
        return None

    if buf[1] != '\x00':
        print 'PCCC error response'
        return None

    return buf[4:]

def makeSlcProtectedTypesLogicalWrite(xdct):

    # expand out the address field if required
    adr = makeSlcAddress(xdct)

    if xdct.has_key('2adr'):
        # create the SLC5 read with 2-address fields
        st = '\x0F' + '\x00' + getNextTNS_str(xdct) + '\xA9' + \
            makeSlcAddress(xdct)
    else:
        # create the SLC5 read with 3-address fields
        st = '\x0F' + '\x00' + getNextTNS_str(xdct) + '\xAA' + \
            makeSlcAddress(xdct)
    # st += self.data
    return

def makeCipHeader(x_prm):
    # return CIP/PCCC header per service
    srv = x_prm.get("service", 0x4B)
    if srv == 0x4C:
        return makeCipHeader_VDHP(x_prm)
    elif srv == 0x4D:
        return makeCipHeader_Local()
    else: # assume srv is 0x4B
        return makeCipHeader_Exec()

def makeCipHeader_Local():
    # return null/empty header - none for 0x4A
    return ""

def makeCipHeader_Exec():
    st = '\x07\x23\x03\x12\x34\x56\x78'   # total 7 bytes
    # Digi's Vend Id of 803, then misc serial num
    return st

def makeCipHeader_VDHP(x_prm):
    st = '\x00' + chr(x_prm.get("dst",1)) + '\x00\x00' + \
         '\x00' + chr(x_prm.get("src",0)) + '\x00\x00'
    return st


def show_bytes(szMsg, data, bNewLine=None):
    if(not data):
        st = "%s[None]" % szMsg
    else:
        if(bNewLine==None):
            bNewLine = (len(data)>32)
        st = "%s[%d]" % (szMsg, len(data))
        nOfs = 0
        for by in data:
            if(bNewLine and ((nOfs%32)==0)):
                st += '\n[%04d]:' % nOfs
            try:
                st += " %02X" % ord(by)
                nOfs += 1
            except:
                st += ',bad type=' + str(by)
                break
    return st
