'''
copyright (c) psych0der

class for pinging hosts on ocal network

experimental server thread included for debugging purpose


'''


import socket
import sys
import thread
import time
import threading
import os
import platform
import hashlib
import getpass

#-------------------------------------------------------------------------------------
# for testing 
class ServerThread(threading.Thread):
    ''' class to handle server threads '''
    id = 0 # numer of threads
    lock = threading.Lock()
	
    def __init__(self,conn,addr):
		#invoking constructor of parent class
        threading.Thread.__init__(self)
        self.myid = ServerThread.id # assigning thread/instance number
        ServerThread.id+=1
        self.client = conn
        self.clientIp = addr[0]
        self.clinetPort = addr[1]
		
    def sendOsStamp(self):
        self.client.send('Server is running on '+os.name+' with platform '+platform.system())	
		
    def run(self):
        print 'server instance # '+str(self.myid)
        clientOs = self.client.recv(20)
        print 'client is running '+clientOs.split('#')[0]+' '+clientOs.split('#')[1]
        self.sendOsStamp()
        print 'terminating connection with '+self.clientIp
        self.client.close()					
		

# --------------------------------------------------------------------------------------		


# class for dispatching ping  threads 
class PingThread(threading.Thread):
	# class to handle ping probes
    def __init__(self,addr,key,passKey,port,cond=None):
        threading.Thread.__init__(self)
        self.clientIp = addr
        self.clientPort = 10998
        self.privateKey = key
        self.condition = cond
        self.passKey = passKey
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)	
		
        self.serverPort = 11000
	
	
	
    def handshake(self,sock):
        greet = sock.recv(20)
        print('message from node -- '+greet)
        sock.send(self.privateKey)
        greet = sock.recv(20)
        print('message from node -- '+greet)
        m = hashlib.md5()
        m.update(self.passKey)
        sock.send(str(m.hexdigest()))
        greet = sock.recv(20)
        print('message from node -- '+greet)
        if greet == 'failed' :
            print('unable to connect to node ')
            return 0
        else :
            return 1 		
		
		
		
	
    def run(self):
        print 'pinging '+self.clientIp
        MAX_TRIALS = 2
        trial = 0
        while trial <=MAX_TRIALS :
            try :
                self.sock.connect((self.clientIp,self.clientPort))
                auth = self.handshake(self.sock)
                if(auth == 1):
				
                    self.sock.send(str(self.serverPort))
                    print 'succesfully pinged '+self.clientIp
                self.sock.close()
                break
            except :
                print 'connection to client '+ self.clientIp +' failed, trial -- '+str(trial) 
            trial+=1
			
		
		
			
		

class Server(object):
    def __init__(self,s_port,key):
        self.servePort = int(s_port)
        self.clientPort = 10998
        self.privateKey = 'transponder-host'
        self.passKey = key
        self.osName = os.name
        self.platform = platform.system()
        self.clientList = []
        self.serverThreads = []
        self.pingThreads = []
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server.bind(('',self.servePort))
        self.server.listen(5)
        self.listening = 1
        self.pswdfilename = 'pass.wd'
        self.pswd = ''
		
		
		# try to fetch password from file(if it exists) otherwise prompts the user for admin password
		
		
        try :
            with open(self.pswdfilename) as fp :
                if os.path.getsize(filename) == 0:
                    self.pswd = getpass.getpass() 
                    fp.write(self.pswd)
                    fp.close()
                else:
                    self.pswd = fp.read()
        except :
            fp = open(self.pswdfilename,"w")
            self.pswd = getpass.getpass() 
            fp.write(self.pswd)
            fp.close()
		
		
		
		
		
	# -----------------------------------------------------------	
	# for runing test server threads 	
    def _loop(self):
        print 'Server is actively listening at '+str(self.servePort)
        try :
            while 1 :
                conn,addr = self.server.accept()
                th = ServerThread(conn,addr)
                self.serverThreads.append(th)
                th.start()
        except KeyboardInterrupt :
            print 'turning off listen mode'
        finally:
            self.server.close()
            for th in self.serverThreads:
                th.join()		
        self.listening = 0
	
    #------------------------------------------------------------
    


    def ipScan(self) :
        ip = socket.gethostbyname(socket.gethostname())
        subnet_mask = ip[:ip.rfind('.')]
        test_ip = ''
        proc = ''
        response  = -1

        for i in range(1,255):
            test_ip = subnet_mask +'.'+str(i)
            print 'pinging' ,test_ip
            proc = os.popen('sudo -S ping  -i 0.001 -W 0.001 -c2 '+test_ip +'> /dev/null', 'w')
            proc.write(self.pswd+'\n')  
            response = proc.close()
            if(response == None):
                self.clientList.append(test_ip)
		
		
    def pingClients(self):
        self.ipScan()
        for ip in self.clientList :
            th = PingThread(ip,self.privateKey,self.passKey,self.servePort)
            self.pingThreads.append(th)
            th.start()
        for th in self.pingThreads:
            th.join()
			
        print 'pinged all nodes'
			
    
#-------------------------------------------------
    def listen(self):
        thread.start_new_thread(self._loop,())
		
	







