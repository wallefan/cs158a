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
        optional_preset_uuid = f.readline().strip()
    if optional_preset_uuid:
        my_uuid = uuid.UUID(optional_preset_uuid)
    else:
        my_uuid = uuid.uuid4()

    server = socket.socket(socket.AF_INET6 if ':' in listen_address[0] else socket.AF_INET, socket.SOCK_STREAM)
    server.bind(listen_address)
    server.listen(1)

    upstream = None
    
    # server will be listening throughout this process.
    while True:
        if server and select.select([server], [], [],0)[0]:
            (upstream, upstream_addr) = server.accept()
            print('Upstream connection established:', upstream_addr)
            server = None
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
        try:
            print('Trying connection to %s:%d... ' % connect_address, end='', flush=True)
            downstream = socket.create_connection(connect_address)
            print('success.')
            break
        except Exception as e:
            print('...failed.', e)
    
    if upstream is None:
        print('Waiting for connection on server (%s:%d)... ' % listen_address, end='', flush=True)
        (upstream, upstream_addr) = server.accept()
        print('got one from', upstream_addr)

    message = Message(uuid = my_uuid, flag = 0)
    downstream.sendall(message.to_json().encode('ascii'))
    while True:
        data = upstream.recv(59) # the JSON messages are fixed length
        message = Message.from_json(data.decode('ascii'))
        print('received', message)

        if message.flag & 1:
            print('a node has been elected:', str(message.uuid))
            leader = message.uuid
            downstream.sendall(data)
            break
        if message.uuid > my_uuid:
            print('greater -- sending the message on')
            downstream.sendall(data)
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


