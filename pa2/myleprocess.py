import socket,uuid,json,select
from dataclasses import dataclass

@dataclass
class Message:
    uuid:uuid.UUID
    flag:int

    def to_json(self):
        return json.dumps({'uuid':str(self.uuid), 'flag':self.flag})
    @classmethod
    def from_json(cls, data:str):
        data = json.loads(data)
        return cls(uuid.UUID(data['uuid']), data['flag'])


def parse_address(line):
    (address, port) = line.strip().split(',')
    port=int(port)
    return (address, port)

def main():
    with open('config.txt') as f:
        listen_address = parse_address(f.readline())
        connect_address = parse_address(f.readline())
        # sneaky little bonus feature -- optional third config line sets a vanity UUID
        optional_preset_uuid = f.readline().strip()
    if optional_preset_uuid:
        my_uuid = uuid.UUID(optional_preset_uuid)
    else:
        my_uuid = uuid.uuid4()

    server = socket.socket(socket.AF_INET6 if ':' in listen_address[0] else socket.AF_INET, socket.SOCK_STREAM)
    server.bind(listen_address)
    server.listen(1)

    upstream = None
    
    # This loop allows to repeatedly retry the connection to the client,
    # or even change the client's IP address,
    # without restarting the script, which would shut down the server
    # and cause the client that connected to *us* to need to be restarted as well.
    # This loop will be broken out of once the downstream socket is connected.
    while True:
        # Check if we've connected the upstream socket yet.  If not, try to
        # connect it.
        if upstream is None:
            # Instead of using a second thread to accept the server connection, I 
            # used a nonblocking select.
            #
            # Each time through the loop, this if statement will check whether a 
            # client is waiting to connect.  If there is one, it will call
            # server.accept(), which will complete immediately. If there isn't one,
            # it will do nothing.
            #
            # Background, for classmates unaware:
            # select() takes three lists of sockets.  It will ask the operating
            # system about the current status of those sockets, and then it will
            # not return until at least one of these is true:
            #  1. any of the sockets in the first list have data waiting to be recv()'d,
            #     or, if they're server sockets, have a client waiting to be accept()ed
            #  2. any of the sockets in the second list have space in their buffer
            #     and are ready to be send()'ed to
            #  3. any of the sockets in the third list have some sort of error condition
            #     like the connection being closed that the program can react to
            #  4. the timeout specified in the fourth parameter is expired
            # then it returns a tuple of three more lists, each of which is a subset of
            # the corresponding list it was passed, containing only the sockets that are
            # ready.
            #
            # This if statement sets the timeout to 0 seconds, so select() will return
            # immediately. It then checks if the first list returned by select() isn't
            # empty. Since only one socket was passed, we know that if it's not empty,
            # it contains that socket, which means a client is waiting to connect on 
            # that socket, and if we call accept(), it won't block.
            if select.select([server], [], [],0)[0]:
                (upstream, upstream_addr) = server.accept()
                print('Upstream connection established:', upstream_addr)
        # Input validation loop for entering a new client address.
        # Instead of just pressing enter, the user can type a new IP address for the
        # downstream client before pressing enter, with the same format as config.txt.
        # The program will then attempt to connect to that address, still leaving
        # the server connection, if any, open.

        # I don't want the program to crash if the user makes a typo when entering a new
        # address, since again, that would close the server connection, which we want to
        # avoid.  Instead, I have yet another infinite loop.  If the user types nothing,
        # we break out of the loop immediately.  Else, we try to parse it.  If the parse
        # succeeds, break out of the loop, else back to the top and prompt the user again.
        # I use this scheme in a lot of my Python programs.
        while True:
            val = input('Type new address, or press Enter when the client is ready:')
            if val:
                try:
                    connect_address = parse_address(val)
                    break
                except:
                    print('Bad input')
            else:
                break
        # Alright, we've got the address that we need to connect to.  Now let's connect to it.
        try:
            print('Trying connection to %s:%d... ' % connect_address, end='', flush=True)
            # socket.create_connection() automates the process of creating a socket and calling
            # connect() on it.  It also autodetermines whether the address is IPv4 or IPv6.
            downstream = socket.create_connection(connect_address,timeout=1)
            print('success.')
            # When the connection succeeds, break out of the loop, and proceed to the leader
            # selection code.
            break
        except Exception as e:
            # The connection failed.  Notify the user what went wrong, then back to the top
            # of the loop to try again.
            print('failed:', e)
    
    # In the likely event that the upstream connection wasn't accepted during the loop
    # (after all, it only checks once every time the user presses Enter),
    # block on accept() before we continue.
    # Yes, we're calling accept() after connect().  It doesn't actually matter.
    if upstream is None:
        print('Waiting for connection on server (%s:%d)... ' % listen_address, end='', flush=True)
        (upstream, upstream_addr) = server.accept()
        print('got one from', upstream_addr)

    message = Message(uuid = my_uuid, flag = 0)
    downstream.sendall(message.to_json().encode('ascii'))

    highest_uuid_seen = my_uuid
    while True:
        # the JSON messages are fixed length
        # so if we read exactly 59 bytes we will get exactly one message.
        data = upstream.recv(59) 
        message = Message.from_json(data.decode('ascii'))
        print('received', message)

        if message.flag == 1:
            print('a leader has been elected:', str(message.uuid))
            leader = message.uuid
            # make sure none of my classmates try anything funny!
            if leader < highest_uuid_seen:
                print('THE LEADER IS ILLEGITIMATE!!!!!!!!!!!!!!!')
                print('The leader claims their UUID %s is the highest in the whole circle, but we have seen the higher UUID %s pass by us!' % (leader, highest_uuid_seen))
            else:
                # no need to reencode the packet -- we already have the bytes we deserialized from JSON,
                # just send those.
                downstream.sendall(data)
                break
        if message.uuid > my_uuid:
            print('greater -- sending the message on')
            downstream.sendall(data)
            if message.uuid > highest_uuid_seen:
                highest_uuid_seen = message.uuid
        elif message.uuid == my_uuid:
            print('equal -- we have been elected! notifying downstream')
            leader = my_uuid
            message = Message(my_uuid, 1)
            downstream.sendall(message.to_json().encode('ascii'))
            break
        else:
            print('less -- ignoring')

    print('Process complete -- the leader is:', leader)
    if leader == my_uuid:
        print("I'm the leader!  Woohoo!")

if __name__=='__main__':
    main()


