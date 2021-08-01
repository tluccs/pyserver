import socket
from threading import Thread
import atexit
import time
import pickle
import functools
#always flush output by default, useful in testing
print = functools.partial(print, flush=True)

#Server class that connects via sockets to multiple parties, using 1 thread per client + 1 thread for server/recieving
#Generic interface to be inherited by other applications, typically overwrite parse_msg function
#HOW IT WORKS:
# server thread listens for connections , creates thread for each one
# Client threads listen to clients and call parse_message function on any data received
# overwrite parse_message as necessary
# If you (server) wants to send a message,
#  use broadcast(msg) to send to all 
#  or send_to(tid, msg) to send to single thread/client
# Optionally run end before exiting. This should be taken care of by atexit handler though
class GenericServer:
    def __init__(self, max_connections, host, port, debug=False):
        self.max_connections = max_connections
        self.host = host
        self.port = port
        self.debug = debug
        #This should be good for most (all?) applications
        self.max_data_size = 2048
        #array for each client thread
        self.threads = []
        #boolean array for each client thread (running/not running)
        self.thread_status = []
        #array for each socket connection
        self.connections = []
        self.running = True
        self.dprint("In server class")
        self.server_socket = socket.socket()
        atexit.register(self.close_connection, self.server_socket)
        self.server_thread = Thread(target=self.thread_for_server)
        #save time of last message sent, can be used to debug / check progress of server
        self.last_send = time.time()

    #start server
    def run(self):
        self.server_thread.start()
        
    #fcn to handle creating client threads
    def thread_for_server(self):
        self.dprint("run...")
        try:
            self.server_socket.bind((self.host, self.port))
        except socket.error as e:
            self.dprint("Error in binding: ", str(e))
            exit()

        self.dprint("Established socket, waiting for connection...")
        self.server_socket.listen(self.max_connections)
        tid = 0
        while self.running:
            self.dprint("waiting for accept..")
            try:
                client, addr = self.server_socket.accept()
            except Exception as e:
                self.dprint("Error in accept. Server possibly ended?")
                self.dprint("exception: ", e)
                continue
            self.dprint("SERVER CONNECT TO ", client)
            client_thread = Thread(target=self.thread_for_client, args=(client, tid), daemon=True)
            self.threads.append(client_thread)
            self.thread_status.append(True)
            self.connections.append(client)
            tid +=1 
            client_thread.start()
            
    #fcn to handle reading messages in thread
    def thread_for_client(self, connection, tid):
        self.dprint("initialised child thread")
        atexit.register(self.close_connection, connection)
        
        #Parse messages in loop
        while self.thread_status[tid]:
            try:
                data = connection.recv(self.max_data_size)
            except:
                self.dprint("connection dropped.")
                exit()
            self.dprint("RECV: ", data.decode('utf-8'))
            
            self.parse_message(data, tid)

        self.close_connection(connection)

    #fcn to send data to all clients
    def broadcast_message(self, msg, **kwargs):
        for tid in range(len(self.connections)):
            self.send_message(msg, tid, **kwargs)

    #fcn to send data to specified client
    def send_message(self, msg, tid, **kwargs):
        connection = self.connections[tid]
        connection.sendall(self.encode(msg, **kwargs))
        self.last_send = time.time()

    #fcn to close all connections, can be called multiple times without error
    def end(self):
        self.dprint("end server:")
        self.running = False
        for connection in self.connections:
            self.close_connection(connection)
        self.close_connection(self.server_socket)
        self.dprint("done.")

    #fcn to print if debug is on
    def dprint(self, *print_args):
        if self.debug:
            print(*print_args)

    #exit handler fcn, can be called multiple times on same connection without error
    def close_connection(self, connection):
        self.dprint("Closing connection")
        connection.close()


    #encode object to be sent. This can (should be overridden)
    def encode(self, obj, **kwargs):
        return str.encode(obj)

    #fcn to apply logic of server. (including decode) Example below
    def parse_message(self, data, tid):
        #remember to decode data here!
        pass


#inherit from this to allow sending objects, and defining a generic header to allow more functionality
# How to send objs? Sends a pickled dict { key: value,... } where self.__dict__[key] = value
class GenericHeader:
    #sets header. Tells decode function what to do for diff codes.
    def set_header(self, header_size=None, codes=None, fcns=None):
        #without any special codes given, only has object send functionality
        object_recv_code = 0
        self.codes = [object_recv_code]
        if codes is not None:
            self.codes += codes
            
        object_recv_fcn = self.set_state
        self.fcns = [object_recv_fcn]
        if fcns is not None:
            self.fcns += fcns
            
        if header_size is not None:
            self.header_size = header_size
        else:
            self.header_size = 1 + len(codes)//256 #256 = 1B

    def encode(self, obj, header=None, pickle=False, **kwargs):
        if header is  None:
            #Ideally, this won't happen. In case it does, give it an invalid code
            header = len(self.codes) 
        header = header.to_bytes(self.header_size, "big")
        data = obj
        if pickle:
            data = self.obj_to_bytestring(data)
        else:
            data = str.encode(data)
        return header + data
        

    def decode(self, msg):
        header = int.from_bytes(msg[:self.header_size], "big")
        data = msg[self.header_size:]
        for code, fcn in zip(self.header_codes, self.header_fcns):
            if header == code:
                fcn(data)
                break
        else:
            #was not a special message. assume that data is a string /not pickled.
            return header, data.decode('utf-8')

    def set_state(self, data):
        state = self.bytestring_to_obj(data)
        for key in state:
            self.__dict__[key] = state[key]
        
    #fcn to change object to byte str
    def obj_to_bytestring(self, obj):
        return pickle.dumps(obj)

    #fcn to convert byte str to object
    def bytestring_to_obj(self, bytestring):
        return pickle.loads(bytestring)




#here is an example of a parse_message function, and an example main below
class ExampleServer(GenericServer):
    def __init__(self, max_connections, host, port, debug=True):
        super().__init__(max_connections, host, port, debug)

    def parse_message(self, msg, tid):
        #sample / test function
        header, msg = self.decode(msg)
    
        #broadcast
        if "bc" in header:
            self.broadcast_message("C{} sends bc message `{}`".format(tid, msg))
            self.dprint("broadcast from ", tid)
            return
        elif "0" in header:
            recv_tid = int(header[1])
            self.send_message("C{} sends single message `{}` to C{}".format(tid, msg, recv_tid), recv_tid)
            self.dprint("sent msg from/to ", tid, recv_tid)
        elif "ab" in header:
            self.dprint("Aborting server")
            self.end()
        else:
            self.dprint("sending msg back to client")
            self.send_message("you sent a message, you are C{}".format(tid), tid)

    def decode(self, msg):
        header = msg[:2].decode('utf-8')
        #given header, know how you should decode msg.
        msg = msg[2:].decode('utf-8')
        return header, msg


#main, script to test using ExampleServer
def main():
    host = '127.0.0.1'
    port = 1020
    print("creating server thread")
    serv = ExampleServer(5, host, port, debug=True)
    serv.run()
    i = 0
    period = 10
    while True:
        print("Sleep... ({})".format(i))
        time.sleep(period)
        i += 1
        #check if any progress made within last n sec
        dt = time.time() - serv.last_send
        #check if one period has gone by without any messages sent
        if dt > period:
            print("server made no progress. Ending server...")
            break

    print("end.")
    serv.end()
    
if __name__ == "__main__":
    main()