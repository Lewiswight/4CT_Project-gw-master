"""idigi_data
idigi_data provides an easy way for Digi device based python apps to
push up data files to the iDigi server the device belongs to.
See idigi_pc.py to run on a PC.
"""
import sys
import os
import time
try:
    import digi_httplib as httplib
except:
    import httplib
# from mimetypes import guess_type
from base64 import encodestring

def sunspec_upload( data, settings=None):

    trace = False

    if settings is None:
        settings = { 'url':"platform.idev.fatspaniel.net",
                 'path':"/rest/v1/data/", 'secure':True,
                 'username':"logger_180373", 'password':"WeXvxoBsaynMEcpl",
                 }

    token = encodestring( '%s:%s' % (settings['username'],settings['password']))[:-1]

    host = settings['url']
    path = settings['path']
    # host = "%s/%s" % (settings['url'],settings['path'])
    if trace:
        print 'host is %s' % host
        print 'Auth token is %s' % token

    data = '<sunSpecData v="1">' + data + '\r\n</sunSpecData>\r\n'

    if settings['secure'] == True:
        # print 'opening secure connection'
        con = httplib.HTTPSConnection(host)
    else:
        # print 'opening normal connection'
        con = httplib.HTTPConnection(host)

    if trace:
        con.set_debuglevel(1)

    con.putrequest('POST', path)
    con.putheader('Content-Type', 'text/xml')
    clen = len(data)
    con.putheader('Content-Length', clen)
    con.putheader('Authorization', 'Basic %s' % token)
    con.endheaders()
    con.send(data)

    response = con.getresponse()
    errcode = response.status
    errmsg = response.reason
    headers = response.msg
    if trace:
        print 'rsp err', errcode, errmsg
        print 'rsp header', headers
        print 'rsp.red', response.read()
    con.close()

    if errcode != 200 and errcode != 201:
        return False, errcode, errmsg
    else:
        return True, errcode, errmsg

if __name__ == '__main__':

    settings = { 'url':"platform.idev.fatspaniel.net",
                 'path':"/rest/v1/data/",
                 'username':"logger_180373", 'password':"WeXvxoBsaynMEcpl",
                 'secure':True,
                 }

    # 'tcpport':23,

    data = '<d ns="mac" lid="00:23:14:81:C9:B8" man="brultech" mod="ECM-1240" sn="34567"'
    data += ' t="%s">' % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data += '\r\n <m id="201">'
    data += '\r\n  <p id="M_AC_Power">11.10</p>'
    data += '\r\n  <p id="M_Imported">101.10</p>'
    data += '\r\n  <p id="M_AC_Current">10.10</p>'
    data += '\r\n  <p id="M_AC_Voltage">124.50</p>'
    data += '\r\n </m>'
    data += '\r\n</d>'
    data += '\r\n'

    sunspec_upload( data, settings)

