'''
adapted from  https://github.com/Kami/python-twisted-binary-file-transfer-demo

added autoconnect layer and syncing operations
psych0der


'''



from __future__ import print_function
import os,sys,platform
import optparse

from twisted.internet import reactor, protocol, stdio, defer
from twisted.protocols import basic
from twisted.internet.protocol import ClientFactory



from common import COMMANDS,RESPONSE,display_message, validate_file_md5_hash, get_file_md5_hash, read_bytes_from_file, clean_and_split_input
import transponder


class STDINAgent(basic.LineReceiver):
    
    delimiter = '\n'
   
    def __init__(self,sender):
        self.sender = sender
        self.factory = sender.factory
    
    def lineReceived(self, line):
        """ If a line is received, call sendCommand(), else prompt user for input. """
        
        if not line:
            self._prompt()
            return
        
        self._sendCommand(line)
    
    def _sendCommand(self, line):
        """ Sends a command to the server. """
        
       
        data = clean_and_split_input(line) 
        if len(data) == 0 or data == '':
            return 

        command = data[0].lower()
        
        
		
        if not ((command in COMMANDS ) or(command in RESPONSE ) ):
            self._display_message('Invalid command')
            return
        
        if command == 'list' or command == 'help' or command == "people" or command == 'quit':
            
            self.sender.transport.write('%s\n' % (command))
            
        if command == 'finger':
            try:
                nickname = data[1]
            except IndexError:
                self._display_message('Missing nickname')
                return
            
            self.sender.transport.write('%s %s\n' % (command, nickname))
            
            
        
        elif command == 'get':
            try:
                filename = data[1]
            except IndexError:
                self._display_message('Missing filename')
                return
            
            self.sender.transport.write('%s %s\n' % (command, filename))
        elif command == 'put':
            try:
                file_path = data[1]
                filename = data[2]
            except IndexError:
                self._display_message('Missing local file path or remote file name')
                return
            
            if not os.path.isfile(file_path):
                self._display_message('This file does not exist')
                return

            file_size = os.path.getsize(file_path) / 1024
            
            print ('Uploading file: %s (%d KB)' % (filename, file_size))
            
            self.sender.transport.write('PUT %s %s\n' % (filename, get_file_md5_hash(file_path)))
            self.sender.setRawMode()
            
            for bytes in read_bytes_from_file(file_path):
                self.sender.transport.write(bytes)
            
            self.sender.transport.write('\r\n')   
            
            # When the transfer is finished, we go back to the line mode 
            self.sender.setLineMode()
        
		
        elif command == 'sync' :
            files = []
            files = [ f for f in os.listdir(self.sender.factory.files_path) if os.path.isfile(os.path.join(self.sender.factory.files_path,f)) ]
            file_list = '#'.join(files)
            self.sender.transport.write('sync %s\n' % (file_list))
            
        elif command == 'search' :
            try:
                filename = data[1]
            except IndexError:
                self._display_message('Missing filename')
                return
                
            if os.path.exists(os.path.join(self.sender.factory.files_path,filename)) :
                self._display_message('File already exists on your local folder')
                return 
                
            
            self.sender.transport.write('search %s\n' % (filename))  
                
            
            
        
        elif command == 'nick' :
            try:
                subcommand = data[1]
                nick = data[2]
                passw = data[3]
            except IndexError:
                self._display_message('Missing subcommand {and\or} nick {and\or} password')
                return
				
            self.sender.transport.write('nick %s %s %s\n' % (subcommand, nick,passw))
			
        elif command == 'recv' :
            self.sender.transport.write('%s %s\n' % (command , data[1]))
        
       # else:
        #    self.sender.transport.write('%s \n' % (command))

       
    
    
    def _display_response(self, lines = None):
        """ Displays a server response. """
       
        if str(lines).startswith('recv') :
            self.sender.setLineMode()
            self._sendCommand(message)
            
           
         
        if lines:
            for line in lines:
                print ('%s' % (line))
            
        self._prompt()
        
        
    def _prompt(self):
        """ Prompts user for input. """
        #self.sender.transport.write('> ')
      
        print ('>',end='')
        sys.stdout.flush()
       # self.transport.write('> ')
        
    def _display_message(self, message):
        """ Helper function which prints a message and prompts user for input. """
        
        print (message)
        self._prompt()

class Client(basic.LineReceiver):
    delimiter = '\n'
   
    def connectionMade(self):
        self.buffer = []
        self.file_handler = None
        self.file_data = ()
        
        inputForwarder = STDINAgent(self)  
        inputForwarder.normalizeNewlines = True 
        inputForwarder.sender = self 
        self.stdioWrapper = stdio.StandardIO(inputForwarder) 
        self.osType = os.name+'#'+platform.system() 
        
        self.sendLine('platform %s '%(self.osType))  # sending os stamp to server
        print ("Connected to server")
        
        
    def connectionLost(self, reason):
        self.file_handler = None
        self.file_data = ()
        
        print ('Connection to the server has been lost')
        reactor.stop()
        
    def lineReceived(self, line):
        if line == 'ENDMSG':
            self._display_response(self.buffer)
            self.buffer = []
            
                
        
        elif line.startswith('SEARCH'):
           
            data = clean_and_split_input(line)
            filename = data[1]
            files = []
            files = [ f for f in os.listdir(self.factory.files_path) if os.path.isfile(os.path.join(self.factory.files_path,f)) ]
            if filename in files :
                self.sendLine('sresponse true')
                
            else :
                self.sendLine('sresponse false')
                
            
                
            
        
        
        elif line.startswith('HASH'):
            # Received a file name and hash, server is sending us a file
            
            data = clean_and_split_input(line)

            filename = data[1]
            file_hash = data[2]
            
            self.file_data = (filename, file_hash)
            self.setRawMode()
        else:
            self.buffer.append(line)
        
    
    def rawDataReceived(self, data):
        filename = self.file_data[0]
        file_path = os.path.join(self.factory.files_path, filename)
        
        print ('Receiving file chunk (%d KB)' % (len(data)))
        
        if not self.file_handler:
            self.file_handler = open(file_path, 'wb')
            
        if data.endswith('\r\n'):
            
            # Last chunk
            data = data[:-2]
            self.file_handler.write(data)
            self.setLineMode()
            
            self.file_handler.close()
            self.file_handler = None
            
            if validate_file_md5_hash(file_path, self.file_data[1]):
                print ('File %s has been successfully transfered and saved' % (filename))
                
                self.sendLine('recv %s '%(filename))
            else:
                os.unlink(file_path)
                print ('File %s has been successfully transfered, but deleted due to invalid MD5 hash' % (filename))
        else:
            self.file_handler.write(data)
    
    
        
    def _display_response(self, lines = None):
        """ Displays a server response. """
        
        if lines:
            for line in lines:
                print ('%s' % (line))
            
        self._prompt()
        
        
    def _prompt(self):
        """ Prompts user for input. """
        
        print('> ',end='')
        sys.stdout.flush()
   
        
        
  
class StdioProxyFactory(protocol.ClientFactory):
    protocol = Client
    
    def __init__(self, files_path):
        self.files_path = files_path
        self.deferred = defer.Deferred()
        self.deferred1 = defer.Deferred()
        
    
        


if __name__ == '__main__':
    
    parser = optparse.OptionParser()
    #parser.add_option('--ip', action = 'store', type = 'string', dest = 'ip_address', default = '127.0.0.1', help = 'server IP address')
    #parser.add_option('-p', '--port', action = 'store', type = 'int', dest = 'port', default = 1234, help = 'server port')
    parser.add_option('--path', action = 'store', type = 'string', dest = 'path', default = "./ctransfers",help = 'directory where the incoming files are saved')
    
    (options, args) = parser.parse_args()
    

    if(not os.path.isdir(options.path)) :
	    os.makedirs(options.path)
        
    tr = transponder.Transponder(10998,'root')
    tr.start()

    # get server ip and port
    connectSettings = tr.getConnectSettings()
    del tr
    print ('Client started, incoming files will be saved to %s' % (options.path))
    
    
    #reactor.connectTCP(options.ip_address, options.port, StdioProxyFactory(options.path)) 
    reactor.connectTCP(connectSettings[1], connectSettings[0], StdioProxyFactory(options.path))  
    reactor.run() 
  
    