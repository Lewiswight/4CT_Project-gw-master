# host, path and auth data exist in config.py
types = []

try:
    types = sensors
except:
    gauges_xml = http_helper.xquery_request( host,auth, self.dev_id, "distinct-values(//sample/name)" )
    for node in gauges_xml.getElementsByTagNameNS("http://exist.sourceforge.net/NS/exist","value" ):
        types.append(node.firstChild.nodeValue )

#screen_width=800                

try:
   screen_width = int(request['width'][0])
except:
   pass
