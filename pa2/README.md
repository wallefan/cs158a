# config.txt
Create a file named config.txt in this directory.  It must contain two lines, and may have up to three.

The first line must be the IP address and port, separated by a comma, it should bind to, to listen.

The second line must be the IP address and port, separated by a comma, it should try to connect to.

The third line, if present must be the UUID it will use during the leader election process.  If the third line is not present, it will use a randomly generated UUID.

# Running
Once the program starts, it will bind to the server interface and start listening, then prompt you to press Enter when it should connect to the client.

If it tries to connect to the client and fails, it will prompt you to press Enter again.

For aid in debugging, if a client connects *during* this process, a message will be displayed.

If you made a typo in the client address, you can paste another client address before pressing Enter and it will attempt to connect to that instead, while leaving the server open.

Once the client connection is established, it will wait for its server to receive a connection, if it hasn't already, and then the leader election process will begin.  

If a malicious node in the network attempts to notify other nodes that it is the leader, when the program has already seen a higher UUID pass by, it will notify the user and will NOT pass the leader election message on.  

# Execution example

```
$ echo "127.0.0.1,12345" > config.txt
$ echo "127.0.0.2,12345" >> config.txt
$ python3 myleprocess.py
Type new address, or press Enter when the client is ready:
Trying connection to 127.0.0.2:12345... success.
Waiting for connection on server (127.0.0.1:12345)... got one from ('127.0.0.1', 55006)
received Message(uuid=UUID('80fb435e-0369-4ad4-8e5a-e3ccec58a7f3'), flag=0)
less -- ignoring
received Message(uuid=UUID('83f909dc-924e-4f08-b812-8a2ad28e30c6'), flag=0)
equal -- we have been elected! notifying downstream
Process complete -- the leader is: 83f909dc-924e-4f08-b812-8a2ad28e30c6
I'm the leader!  Woohoo!
$ 
```
