import socket
import os
from threading import Thread
import atexit
import queue
import signal
import sys
import time

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
# Optionally run end_server before exiting. This should be taken care of by atexit handler though
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
        
        
        #send a WHO message to ask who is playing
        #connection.send(str.encode("WHO?"))

        #Parse messages in loop
        while self.thread_status[tid]:
            try:
                data = connection.recv(self.max_data_size).decode('utf-8')
            except:
                self.dprint("connection dropped.")
                exit()
            self.dprint("SERVER RECV: ", data)
            
            self.parse_message(data, tid)

        self.close_connection(connection)

    #fcn to apply logic of server. Example below
    def parse_message(self, msg, tid):
        pass

    #fcn to send data to all clients
    def broadcast_message(self, msg):
        for tid in range(len(self.connections)):
            self.send_message(msg, tid)

    #fcn to send data to specified client
    def send_message(self, msg, tid):
        connection = self.connections[tid]
        connection.sendall(str.encode(msg))
        self.last_send = time.time()

    #fcn to close all connections, can be called multiple times without error
    def end_server(self):
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


#here is an example of a parse_message function, and an example main below
class ExampleServer(GenericServer):
    def __init__(self, max_connections, host, port, debug=True):
        super().__init__(max_connections, host, port, debug)

    def parse_message(self, msg, tid):
        #sample / test function
        header = msg[:2]
        msg = msg[2:]
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
            self.end_server()
        else:
            self.dprint("sending msg back to client")
            self.send_message("you sent a message, you are C{}".format(tid), tid)


#main, script to test using ExampleServer
def main():
    host = '127.0.0.1'
    port = 1018
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
    serv.end_server()
    
if __name__ == "__main__":
    main()