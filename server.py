'''
adapted from https://github.com/Kami/python-twisted-binary-file-transfer-demo
added laer of autoconnect and various other features

'''


import os 
import optparse
import hashlib
import json
import datetime
import thread

from twisted.internet import reactor, protocol,defer
from twisted.protocols import basic

from common import COMMANDS,RESPONSE, display_message,log_message ,validate_file_md5_hash, get_file_md5_hash, read_bytes_from_file, clean_and_split_input
import pinger


class Transponder(basic.LineReceiver):
	delimiter = '\n'

	def connectionMade(self):
		self.authenticated = False
		self.file_handler = None
		self.file_data = ()
		self.sync = 0  # by default of 
		self.file_outbox = []
		self.osType = None
       
		
		self.ip = self.transport.getPeer().host
		self.port = self.transport.getPeer().port
		
		self.nick = 'user'+self.ip[:6]+'$$'+str(self.port)  # temporary nick
		self.factory.onlineClients.append(self)
		
		self.transport.write('-- SHARE-PY  --ver 1.2  \n')
		self.transport.write('-- CREDITS -- cyberslicks \n')
		self.transport.write('-- copyright (c) 2013  \n')
		self.transport.write('Type help for list of all the available commands\n')
		
		self.transport.write('Welcome\n')
		self.transport.write('Type help for list of all the available commands\n')
		self.transport.write('ENDMSG\n')
		
		display_message(' New client added : %s (%s), (%d clients total)' % (self.nick , self.transport.getPeer().host, len(self.factory.onlineClients)))
		log_message(' New client added : %s (%s), (%d clients total)' % (self.nick , self.transport.getPeer().host, len(self.factory.onlineClients)),self.factory.log)
		
	def connectionLost(self, reason):
		self.factory.onlineClients.remove(self)
		self.file_handler = None
		self.file_data = ()
		
		display_message('Connection from  %s (%s) lost (%d clients left)' % (self.nick,self.transport.getPeer().host, len(self.factory.onlineClients)))
		log_message('Connection from  %s (%s) lost (%d clients left)' % (self.nick,self.transport.getPeer().host, len(self.factory.onlineClients)),self.factory.log)

	
	def lineReceived(self, line):
		
		data = self._cleanAndSplitInput(line)
		if len(data) == 0 or data == '':
			return 
		
		command = data[0].lower()
		display_message('Received the following command from the client %s ,[%s]: %s' % (self.nick,self.ip, command))
		log_message('Received the following command from the client %s ,[%s]: %s' % (self.nick,self.ip, command),self.factory.log)
		
		if not ((command in COMMANDS) or (command in RESPONSE)) :
			self.transport.write('Invalid command\n')
			self.transport.write('ENDMSG\n')
			return
		
		if command == 'list':
			self._send_list_of_files()
			
		if command == 'finger':
			if not self.authenticated :
				self.transport.write('Please authenitcate using "nick identify" before using file transfer \n')
				self.transport.write('ENDMSG\n')
				return 
				
			try:
				nickname = data[1]
			except IndexError:
				self.transport.write('Missing nickname\n')
				self.transport.write('ENDMSG\n')
				return
				
			for user in self.factory.onlineClients :
				if user.nick == nickname :
					self.transport.write('-- INFORMATION --  \n')
					self.transport.write('Nickname : %s \n'%(nickname))
					self.transport.write('IP : %s \n'%(user.ip))
					self.transport.write('PORT : %d \n'%(user.port))
					self.transport.write('OS : %s \n'%(user.osType.split('#')[0]))
					self.transport.write('Platform : %s \n'%(user.osType.split('#')[1]))
					self.transport.write('ENDMSG\n')
					
					return 
				
			self.transport.write('Nickname not found\n')
			self.transport.write('ENDMSG\n')	
			
		
		elif command =='platform':
			print data[1]
			self.osType = data[1]
		
		elif command == 'get':
			if not self.authenticated :
				self.transport.write('Please authenitcate using "nick identify" before using file transfer \n')
				self.transport.write('ENDMSG\n')
				return 
				
			try:
				filename = data[1]
			except IndexError:
				self.transport.write('Missing filename\n')
				self.transport.write('ENDMSG\n')
				return
			
			if not self.factory.files:
				self.factory.files = self._get_file_list()
				
			if not filename in self.factory.files:
				self.transport.write('File with filename %s does not exist\n' % (filename))
				self.transport.write('ENDMSG\n')
				return
			
			display_message('%s : Sending file: %s (%d KB)' % (self.nick,filename, self.factory.files[filename][1] / 1024))
			log_message('%s : Sending file: %s (%d KB)' % (self.nick,filename, self.factory.files[filename][1] / 1024),self.factory.log)
			
			self.transport.write('HASH %s %s\n' % (filename, self.factory.files[filename][2]))
			self.setRawMode()
			
			for bytes in read_bytes_from_file(os.path.join(self.factory.files_path, filename)):
				self.transport.write(bytes)
			
			self.transport.write('\r\n')	
			self.setLineMode()
		
		elif command == 'put':
			if not self.authenticated :
				self.transport.write('Please authenitcate using "nick identify" before using file transfer \n')
				self.transport.write('ENDMSG\n')
				return
			
			try:
				filename = data[1]
				file_hash = data[2]
			except IndexError:
				self.transport.write('Missing filename or file MD5 hash\n')
				self.transport.write('ENDMSG\n')
				return

			self.file_data = (filename, file_hash)
			
			# Switch to the raw mode (for receiving binary data)
			print 'Receiving file: %s' % (filename)
			self.setRawMode()
		
		elif command == "people" :
			self._send_online_clients()
		
		elif command == "sync" :
			
			self.factory.files = self._get_file_list()
			self.sync = 1 			
			
				
			if not self.authenticated :
				self.transport.write('Please authenitcate using "nick identify" before using sync \n')
				self.transport.write('ENDMSG\n')
				return
			
			now = datetime.datetime.now()
			
			self.transport.write('Initiating sync \n')
			self.transport.write('ENDMSG\n')
			display_message('initiating sync with %s(%s) : %s ' % (self.nick,self.ip,now.strftime("%Y-%m-%d %H:%M")))
			log_message('initiating sync with %s(%s) : %s ' % (self.nick,self.ip,now.strftime("%Y-%m-%d %H:%M")),self.factory.log)
			
			#self.transport.write('Initiating sync\n')
			#self.transport.write('ENDMSG\n')
			try:
				cfiles = data[1].split('#')
				
			except IndexError:
				cfiles = []
				
			sfiles = [ f for f in os.listdir(self.factory.files_path) if os.path.isfile(os.path.join(self.factory.files_path,f)) ]
			file_outbox = []
			
			for file in sfiles :
				if file not in cfiles :
					self.file_outbox.append(file)
			
			no_of_files = len(self.file_outbox)
			self.transport.write('Sending %d files\n'%(no_of_files))
			self.transport.write('ENDMSG\n')
				
			if no_of_files == 0 :
				self.sync = 0
				self.transport.write('Folders are in sync \n')
				self.transport.write('ENDMSG\n')
				return
			
			file = self.file_outbox.pop()
			#self.sendFile(file)
			
			display_message('%s : Sending file: %s (%d KB)' % (self.nick,file, self.factory.files[file][1] / 1024))
			log_message('%s : Sending file: %s (%d KB)' % (self.nick,file, self.factory.files[file][1] / 1024),self.factory.log)
			
			self.transport.write('HASH %s %s\n' % (file, self.factory.files[file][2]))
			self.setRawMode()
			
			for bytes in read_bytes_from_file(os.path.join(self.factory.files_path, file)):
				self.transport.write(bytes)
			
			self.transport.write('\r\n')	
			self.setLineMode()
				
				
			'''
			@defer.inlineCallbacks
			def _sync():
				
				for file in file_outbox :
					display_message('%s : Sending file: %s (%d KB)' % (self.nick,file, self.factory.files[file][1] / 1024))
					log_message('%s : Sending file: %s (%d KB)' % (self.nick,file, self.factory.files[file][1] / 1024),self.factory.log)
					yield sendFile(file)
						
		    _sync()	
			'''
				
				#self.transport.write('ENDMSG\n')
				
			
					
		
		elif command == 'nick':
			subcommand = data[1]
			if not (subcommand and data[2] and data[3]) :
				self.transport.write('Missing nickname and/or password\n')
				self.transport.write('ENDMSG\n')
			else :
				if data[1] == "reg" :
					self._register(data[2],data[3])
					
				elif data[1] == "identify" :
					self._identify(data[2],data[3])
					
				else :
					self.transport.write('unknown subcommand %s to nick\n' % (data[1]))
					self.transport.write('ENDMSG\n')
						 
			
		
		
		elif command == 'recv' :
			now = datetime.datetime.now()
			display_message('%s : File recieved - %s' % (self.nick,data[1]))
			log_message('%s : File recieved - %s' % (self.nick,data[1]),self.factory.log)
			
			if self.sync == 1 :
				no_of_files = len(self.file_outbox)
				
				if no_of_files != 0 :
					file = self.file_outbox.pop()
					
					
					
					self.transport.write('HASH %s %s\n' % (file, self.factory.files[file][2]))
					self.setRawMode()
			
					for bytes in read_bytes_from_file(os.path.join(self.factory.files_path, file)):
						self.transport.write(bytes)
			
					self.transport.write('\r\n')	
					self.setLineMode()
					
					
				
					
					#self.sendFile(file)
					
					
				else :
					display_message('terminating sync with %s(%s) : %s ' % (self.nick,self.ip,now.strftime("%Y-%m-%d %H:%M")))
					log_message(' sync with %s(%s) : %s ' % (self.nick,self.ip,now.strftime("%Y-%m-%d %H:%M")),self.factory.log)
					#self.transport.write('Terminating sync\n')
					self.setLineMode()
					self.transport.write('Sync complete\n')
					self.transport.write('ENDMSG\n')
					#self.transport.write('ENDMSG\n')
					self.sync = 0
					
				
		
		elif command == 'search':
			
			self.factory.search_request = 1
			self.factory.responses = 0 
			self.factory.requester = self
			for user in self.factory.onlineClients :
				if user.nick != self.nick :
					user.transport.write('SEARCH-REQUEST %s\n'%(data[1]))
				else :
					user.transport.write('ENDMSG\n')
					
                    
		elif command == 'sresponse':
			
			
			if self.factory.search_request == 1 :
				self.factory.responses+=1
				found = data[1]
				print data
				if found == 'true' :
					tupple = (self.nick,self.ip)
					self.factory.search_dump.append(tupple)
				if self.factory.responses >= len(self.factory.onlineClients) - 1:
					self.factory.requester.setLineMode()
					
					if len(self.factory.search_dump) == 0 :
						self.factory.requester.transport.write('File not found \n')
						self.factory.requester.transport.write('ENDMSG\n')
					else :
						self.factory.requester.transport.write('File found in following clients \n')
						for user in self.factory.search_dump : 
							self.factory.requester.transport.write('%s - %s\n'%(user[0],user[1]))
						self.factory.requester.transport.write('ENDMSG\n')
                            
					self.factory.search_request = 0
					self.factory.requester = None
                        
                
		
		
		elif command == 'help':
			self.transport.write('Available commands:\n\n')
			
			for key, value in COMMANDS.iteritems():
				self.transport.write('%s - %s\n' % (value[0], value[1]))
			
			self.transport.write('ENDMSG\n')				
		elif command == 'quit':
			self.transport.loseConnection()
			
		
			



	def rawDataReceived(self, data):
		filename = self.file_data[0]
		file_path = os.path.join(self.factory.files_path, filename)
		
		display_message('%s : Receiving file chunk (%d KB)' % (self.nick,len(data)))
		log_message('%s : Receiving file chunk (%d KB)' % (self.nick,len(data)),self.factory.log)
		
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
				self.transport.write('File was successfully transfered and saved\n')
				self.transport.write('ENDMSG\n')
				
				display_message('%s : File %s has been successfully transfered' % (self.nick,filename))
				log_message('%s : File %s has been successfully transfered' % (self.nick,filename),self.factory.log)
			else:
				os.unlink(file_path)
				self.transport.write('File was successfully transfered but not saved, due to invalid MD5 hash\n')
				self.transport.write('ENDMSG\n')
			
				display_message('%s : File %s has been successfully transfered, but deleted due to invalid MD5 hash' % (self.nick,filename))
				log_message('%s File %s has been successfully transfered, but deleted due to invalid MD5 hash' % (self.nick,filename),self.factory.log)
		else:
			self.file_handler.write(data)
		
	def _send_list_of_files(self):
		files = self._get_file_list()
		self.factory.files = files
		
		self.transport.write('Files (%d): \n\n' % len(files))	
		for key, value in files.iteritems():
			self.transport.write('- %s (%d.2 KB)\n' % (key, (value[1] / 1024.0)))
			
		self.transport.write('ENDMSG\n')
		
	def _send_online_clients(self):
		
		self.transport.write('--List of Online clients--\n')
		for x in self.factory.onlineClients:
			self.transport.write(str(x.nick)+'\n')
			
		self.transport.write('ENDMSG\n')
			
	def _get_file_list(self):
		""" Returns a list of the files in the specified directory as a dictionary:
		
		dict['file name'] = (file path, file size, file md5 hash)
		"""
		
		file_list = {}
		for filename in os.listdir(self.factory.files_path):
			file_path = os.path.join(self.factory.files_path, filename)

			if os.path.isdir(file_path):
				continue
			
			file_size = os.path.getsize(file_path)
			md5_hash = get_file_md5_hash(file_path)

			file_list[filename] = (file_path, file_size, md5_hash)

		return file_list
			
	
	def _register(self,nick,passw):
		if nick in self.factory.users.keys() :
			self.transport.write('NICK UNAVAILABLE\n')
			self.transport.write('ENDMSG\n')
		else :
			self.nick = nick
			m   = hashlib.md5()
			m.update(passw)
			passw = m.hexdigest() 
			self.factory.users[nick] = passw
			
			self.transport.write('Nick %s is succesfully registered\n'%(nick))
			self.transport.write('ENDMSG\n')
			
		
	def _identify(self,nick,passw):
		m   = hashlib.md5()
		m.update(passw)
		passw = m.hexdigest()
		
		if nick in self.factory.users.keys() :
			if(self.factory.users[nick] == passw) :
				self.authenticated = True
				self._updateNick(nick)
				self.nick = nick
				self.transport.write('You are now identified as %s\n'%(nick))
				self.transport.write('ENDMSG\n')
			
			else:
				self.transport.write('Indentification failure : Incorrect password %s\n'%(nick))
				self.transport.write('ENDMSG\n')
                
		else :
			self.transport.write('Indentification failure : Incorrect nick %s\n'%(nick))
			self.transport.write('ENDMSG\n')
            
			
	def _updateNick(self,nick):
		for client in self.factory.onlineClients :
			if client == self:
				client.nick = nick
		
		
	
	
	def sendFile(self,file) :
	
		self.transport.write('HASH %s %s\n' % (file, self.factory.files[file][2]))
	
		self.setRawMode()
		for bytes in read_bytes_from_file(os.path.join(self.factory.files_path, file)):
			self.transport.write(bytes)
		self.transport.write('\r\n')	
		self.setLineMode()
	
	def _cleanAndSplitInput(self, input):
		input = input.strip()
		input = input.split(' ')
		
		return input

class TransponderFactory(protocol.ServerFactory):
	
	protocol = Transponder
	
	def __init__(self, files_path):
		print 'Server Initialized'
		self.files_path = files_path
		self.onlineClients = []
		self.users = {}
		self.files = None
		self.search_dump = []
		self.search_request = 0
		self.responses = 0
		self.requester = None
		
	def startFactory(self):
		try:
			self.userdb = open("user.db","rb") 
			self.users = json.load(self.userdb)  
			self.userdb.close()   
		except IOError:  
			self.userdb = None
			self.users = {}
		now = datetime.datetime.now()
		if(not os.path.isdir('./logs')) :
			os.makedirs('./logs')
		
		self.log = open('logs/serverlog-%s.log'%(now.strftime("%Y-%m-%d %H:%M")),'wb')     
             
            
			
	def stopFactory(self) :
		self.userdb = open("user.db","wb")
		json.dump(self.users,self.userdb)
		self.userdb.close()	
		self.log.close()
		display_message('Bye Bye! \n')
			
def initiate():
	ser = pinger.Server(10999,'root')
    
	ser.pingClients()
	
    		
	
if __name__ == '__main__':
	parser = optparse.OptionParser()
	parser.add_option('-p', '--port', action = 'store', type = 'int', dest = 'port', default = 11000, help = 'server listening port')
	parser.add_option('--path', action = 'store', type = 'string', default = "./transfers",dest = 'path', help = 'directory where the incoming files are saved')
	(options, args) = parser.parse_args()
	
	
	
	if(not os.path.isdir(options.path)) :
		os.makedirs(options.path)
   
    display_message(' --- PYSHARE --- \n version - 1.1')
	display_message('copyright (c) psych0der')  
	display_message('Listening on port %d, serving files from directory: %s' % (options.port, options.path))
	
    
	thread.start_new_thread(initiate,())
    
	reactor.listenTCP(options.port, TransponderFactory(options.path))
	reactor.run()
	
	
	
	
	
	
    