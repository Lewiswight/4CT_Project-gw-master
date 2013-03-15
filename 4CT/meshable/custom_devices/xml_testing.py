import sys
from twisted.internet import reactor
from autobahn.websocket import WebSocketClientFactory, \
                               WebSocketClientProtocol, \
                               connectWS 


class EchoClientProtocol(WebSocketClientProtocol): 
    
    
    

    
  
    def onOpen(self):
        
        msg = ""
        msg = input("what do you want to send")
        self.sendMessage(msg)
        self.test = 0    
        self.sendHello() 
    
    def sendHello(self):
        print "sending Hello"
        self.test += 1   
        self.sendMessage("Hello, world!" + str(self.test))
    
    def onMessage(self, msg, binary):
        print "Got echo: " + msg
        self.sendHello()
     #   reactor.callLater(1, self.sendHello)


if __name__ == '__main__':

   #if len(sys.argv) < 2:
   #   print "Need the WebSocket server address, i.e. ws://localhost:9000"
    #  sys.exit(1)

   factory = WebSocketClientFactory("ws://echo.websocket.org")
   factory.protocol = EchoClientProtocol
   connectWS(factory)

   reactor.run()