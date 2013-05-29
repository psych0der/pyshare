'''
copyright (c)  
psych0der

client module to enable autoconnecting of clients by putting
in listening mode
'''




import socket
import time
import thread
import os
import hashlib
import platform


class Transponder(object):
    ''' class for handling routines to run node which acts as server/client --- still experimental '''
    
    def __init__(self,port,key,serverHost = None):
        self.port = int(port)
        self.hostPort = None
        self.mode = 0  # determines which mode to operate in (0 : transponder   1 : client)
        self.handler = {}
        self.plugin = {}
        self.serverHost = serverHost
        self.connected = 0   # signals connection to host
        self.authenticated = 0 # server authenticated
        self.privateKey = key
        self.osType = os.name+'#'+platform.system()
    
    def getSocket(self,type,serverHost = None,port = None):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR , 1)
        if type == 0:   #server
            s.bind(('',self.port))
            s.listen(5)
            return s
            
        elif type == 1 :        # client mode
            s.connect((serverHost,port))
            return s
    
    # -------------------------------------------------------------
    # for testing
    
    def connectToHost(self):
       
        try :
            sock  = self.getSocket(1,self.serverHost,self.hostPort)
            self.mode = 1
            self.connected = 1
            print 'connected to server ... '
            sock.send(self.osType)
            response = sock.recv(50)
            print 'server response -- '+response
            sock.close()
            print 'closing conection to server'
       
        except :
            raise
    # ----------------------------------------------------------------


    
    def handshake(self,sock):
        sock.send('Hello anonymous')
        response = sock.recv(30)
        
        if(response == 'transponder-host'):
            sock.send('private-key : ')
            response = sock.recv(50)
            m = hashlib.md5()
            m.update(self.privateKey)
            if(response == str(m.hexdigest())) :
                sock.send('-- authenticated --')
                self.authenticated = 1
                return 1
            else : 
                sock.send('failed')
                return 0
        else :
            sock.send('failed')
            return 0
             
    def getConnectSettings(self):
        tupple = (self.hostPort,self.serverHost)
        return tupple          
   
   
    def start(self):
        
        self.authenticated = 0
        s = self.getSocket(0)
        self.mode = 0
        print ' Waiting for Server on port '+str(self.port)
        conn , addr = s.accept()
        print 'connection request From '+str(addr[0])
        print 'authenticating ....'
        self.authenticated = self.handshake(conn)
        if(self.authenticated == 1 ):
            print 'authenticated'
            self.hostPort = int(conn.recv(10))
            self.serverHost = addr[0]
            conn.close()
            s.close()
            print 'Server IP and PORT received\n'
                   # try :
                   #    self.connectToHost()
                   # except : 
                   #    print 'could connct to server'
                        
        else :
            print ' authentication failed '
            s.close()
        self.connected = 0    
        
     
             

