from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import libs.PythonInsideHTML as pyhtml
import libs.http_helper as http_helper
import base64,threading,urlparse,urllib2,os,re,cgi,sys,time
from xml.dom import minidom

__DEBUG__ = False
DEV_ID_PATTERN = re.compile("/([0-9\\-A-F]+)(/.*)")

class DiaDemoHttpHandler(BaseHTTPRequestHandler):

    def is_handled(self, path ):
      res = os.path.exists("web_content%s"%path) and not os.path.isdir("web_content%s"%path)
      res = res or os.path.exists("web_content%shtml"%path) and not os.path.isdir("web_content%shtml"%path)
      res = res and not path.endswith(".pyhtml")
      return res
  
    def log_message(self, format, *args):
        if __DEBUG__:
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))
    
    def set_dev_id(self):
        m = DEV_ID_PATTERN.match(self.path)
        if not m:
            try:
                # get gateway from config.py
                l = {"route":{}}
                execfile( sys.path[0]+"/config.py" ,l)
                self.dev_id = l["gateway"]
            except:
                # no defined dev_id or one in path
                self.dev_id = None
        else:
            id = m.group(1)
            if len(id)==32:
                id = "-".join([id[0:8],id[8:16],id[16:24],id[24:32]])
            elif len(id)==16:
                id = "-".join(["0"*8,"0"*8,id[0:8],id[8:16]])
            elif len(id)==17:
                id = "-".join(["0"*8,"0"*8,id])
            self.dev_id = id
            # set path handling to everything after /########-########-########-########
            self.path = m.group(2)     
        
    def do_GET(self):
        """
        everything needed for the execution of the web_content is generated here. available values 
        in the namespace for the web_content(py/pyhtml) include:
          * GET parameters, ie calling 'http://host/path/script.py?foo=bar' will make 
            request = {'foo':['bar']} available in the namespace of the controller and view
            
          * anything defined on the top level of the web_content.py module will be on the same
            namespace as the web_content.pyhtml.  i.e. a /web_content/path/example.py consists of
                 "message = 'hello world'"
            and a /web_content/path/example.pyhtml consists of
                 " <%= message %>"
            the result of going to http://host/path/example.py will be
                 "hello world"
                 
          * anything defined in the top level of the config.py module in the application root
          * parsed_path (see: http://www.python.org/doc/2.5.2/lib/module-urlparse.html)
        """
        t1 = 1
        if __DEBUG__: t1 = time.time()
        if self.path=="/" : self.path="/index.html"
        route={}
        execfile( sys.path[0]+"/config.py" )
        self.set_dev_id()
        if self.dev_id == None and self.path.startswith("/demo.py"):
            self.path = "/dev_id.py"
        for key in route:
            if self.path.startswith( key ): self.path = self.path.replace(key,route[key])

        parsed_path = urlparse.urlparse(self.path)
        if parsed_path[2].find("..") > 0:
            return
        request = cgi.parse_qs(parsed_path[4], keep_blank_values=1)

        self.send_response(200)
        self.send_header("Expires","-1") # for ie caching flashdata
        if parsed_path[2].endswith("py"):
            self.send_header("Content-Type", "text/html")
        self.end_headers()
        if ( self.is_handled(parsed_path[2] ) ):
          if parsed_path[2].endswith(".py"):
            ###
            # Execute Controller if exists before the view
            ###
            p = pyhtml.PIH(sys.path[0]+"/web_content%shtml"%parsed_path[2])
            if ( os.path.exists(sys.path[0]+"/web_content%s"%parsed_path[2])  ):
               execfile( sys.path[0]+"/web_content%s"%parsed_path[2] )
               exec p.pythonCode()
               self.wfile.write(py_code.getvalue())
            else:
               exec p.pythonCode()
               self.wfile.write(py_code.getvalue())
          else:
            filer = open( sys.path[0]+"/web_content%s"%parsed_path[2], "rb")
            self.wfile.write( filer.read() )
            filer.close()
        if __DEBUG__: 
            t2 = time.time()
            sys.stderr.write( '   << response took %0.3f ms\n' % ((t2-t1)*1000.0) )             
        return
        
            
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    
def main():
    try:
        # address and port to http bind server to
        listen_interface = "localhost"
        listen_port = 2323
        print 'started httpserver...'
        server = ThreadedHTTPServer((listen_interface, listen_port), DiaDemoHttpHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()
        sys.exit(-9)

if __name__ == '__main__':
    main()

