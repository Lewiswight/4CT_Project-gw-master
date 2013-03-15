gateways = []
path = "/ws/data/~/"
req = urllib2.Request("http://%s%s" % (host, path))
req.add_header("Authorization", "Basic %s" % auth)
dom = minidom.parse(urllib2.urlopen(req))
for node in dom.getElementsByTagNameNS("http://exist.sourceforge.net/NS/exist","collection" ):
     if re.search("[0-9A-F\\-]+",node.attributes['name'].value):
	 gateways.append(node.attributes['name'].value)
