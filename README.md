Pyshare
=========

inspired from : https://github.com/Kami/python-twisted-binary-file-transfer-demo

Pyshare is python based local file transfer/syncing app with autoconnect features.
It addresses the most irritating problem of entering servers/peer ip address to initate connection.

* Requires one machine to be reserved as server *
* may require admin password on certain platforms ( for ping utility )*

> It automatically searches hosts on local network running instance of pyshare and connects to them . ('may require admin password')
> uses md5 for transferring keys for authentication purposes
> uses custom handshake to determine if instance of pyshare is running on machine or not

Pyshare supports nickname facility and assigns nick to each host/peer on network and further gives user to finger patticular host using nickname
> nicknames are serialized using json and are loaded after server is started . 
> Thus nicknames are preserved between server initiations.
> finger command gives users nick and other details like os they are running

------

Pyshare maintains log of each activity on network by creating log files on each server start.
> log files are stores in logs folder , that is created if it doesnt exists

Pyshare provides network file search .
> this technique makes file to be searched on whole network and user is oblivious to the process
> if files are found on any host on network , pyshare displays the name along with nick ,of host its stored in .

## Functionality offrerd
* nick name assignment to hosts
* finger ( information retrieval of hosts)
* network file search
* file sending
* file recieving
* file syncing
* listing of files

-------

Pyshare uses sandboxing to restrict file transfers to a particular folder on client/server machine.
> When starting pyshare service , additional argument can be provided to assign a local folder to pyshare for sharing purpose
> if provided as argument , pyshare creates a folder by  argument name if it doesnt exists.
> * By default it is 'ctransfers' for clients and 'transfers' for server

---------
### Command line arguments 
> For server :
* '--path' : path of folder to be used with pyshare
* '--port ' : server port to run on

> for Clints
* '--path' : path pf folder to be used with pyshare

Further pyshare client instances include help option that prints list of available commands 