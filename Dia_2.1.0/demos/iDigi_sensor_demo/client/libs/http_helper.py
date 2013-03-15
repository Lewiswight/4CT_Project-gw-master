import urllib, urllib2
from xml.dom import minidom
import httplib
import threading
import time
import exceptions 
import sys

def xquery_request(host, auth, gateway, query):
   try:
     path = "/ws/data/~/%s/sensor_demo/?_query="%gateway
     req = urllib2.Request("http://%s%s%s"%(host,path,urllib.quote(query)) )
     req.add_header("Authorization", "Basic %s"%auth )
     dom = minidom.parse(urllib2.urlopen(req))
   except Exception, e:
     print e
     raise Exception("http://%s%s%s"%(host,path,query))

   return dom

class CWMControl(threading.Thread):
    __shared_state = {}
    
    def __init__(self, host, auth, gateway, channel):
        #shared "self" between all instances of CWMControl
        self.__dict__ = self.__shared_state 
        self.host = host
        self.auth = auth
        if not hasattr(self, "channels"):
            self.channels = {}
            self.event = threading.Event()
            threading.Thread.__init__ ( self , name="CWMControl")
            self.start()
        key = "%s,%s"%(gateway,channel)
        if not self.channels.has_key(key):
            self.channels[key] = {}
        
    def retrieve_sample(self,gateway, channel):
        self.event.set()
        self.last_request = time.time()
        while( len(self.channels["%s,%s"%(gateway,channel)]) == 0 ): # block until value exists
            time.sleep(0.3)
        return self.channels["%s,%s"%(gateway,channel)]
    
    def run(self):
            config = {"route":{}}
            execfile( sys.path[0]+"/config.py" ,config)
            while(True):
              try:
               for channel in self.channels:
                   time.sleep(int(config['poll_interval']))
                   try:                 
                       d = channel.split(',')
                       gateway = d[0]
                       channel_name = d[1]
                       query = "subsequence(for $resp in //sample[name=\"%s\"] order by xmldb:last-modified(util:collection-name($resp), util:document-name(base-uri($resp))) descending return $resp,1,1)"%channel_name
                       sample_data_doc = xquery_request( self.host, self.auth , gateway, query)
                       if len(sample_data_doc.getElementsByTagName("name")) == 0:
                           continue
                       sample = {}
                       sample["name"] = sample_data_doc.getElementsByTagName("name")[0].firstChild.nodeValue
                       sample["value"] = sample_data_doc.getElementsByTagName("value")[0].firstChild.nodeValue
                       sample["unit"] = sample_data_doc.getElementsByTagName("unit")[0].firstChild.nodeValue
                       self.channels[channel] = sample
                       t2 = time.time()
                       if ((t2-self.last_request)*1000.0) > 12000:
                           self.event.clear() # block until request comes in
                       self.event.wait()
                   except Exception,e:
                         sys.stderr.write("Error in CWMControl loop: %s\n"%e)
              except:
                    pass

                  
