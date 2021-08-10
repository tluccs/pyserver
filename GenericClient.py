import socket
import os
from threading import Thread
import atexit
import time
import functools
from GenericServer import *
#from pyserver.GenericServer import *

#always flush output by default
print = functools.partial(print, flush=True)

#Generic client class, it's similar to GenericServer but now only spawns 1 thread (for receiving)
class GenericClient(GenericServer):
    def __init__(self, host, port, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        #This should be good for most (all?) applications
        self.max_data_size = 2048
        
        self.running = True
        self.dprint("In client class")
        self.client_socket = socket.socket()
        atexit.register(self.close_connection, self.client_socket)
        try:
            self.client_socket.connect((host,port))
        except socket.error as e:
            self.dprint("Error contacting server: ", str(e))
            exit()
        self.receiver_thread = Thread(target=self.thread_for_client)
        #save time of last message sent, can be used to debug / check progress
        self.last_send = time.time()

    #start client
    def run(self):
        self.receiver_thread.start()

    def thread_for_client(self):
        self.dprint("initialised child thread")
        atexit.register(self.close_connection, self.client_socket)
        
        #Parse messages in loop
        while self.running:
            try:
                data = self.client_socket.recv(self.max_data_size)
            except:
                self.dprint("connection dropped.")
                exit()
            self.dprint("RECV: ", data.decode('utf-8'))
            
            self.parse_message(data)

        self.close_connection(self.client_socket)

    #fcn to send data to server
    def send_message(self, msg, **kwargs):
        #self.dprint("msg: ", msg, "kwargs", kwargs)
        self.client_socket.sendall(self.encode(msg, **kwargs))
        self.last_send = time.time()

    #fcn to close connection, can be called multiple times without error
    def end(self):
        self.dprint("end client:")
        self.running = False
        self.close_connection(self.client_socket)
        self.dprint("done.")

#example of how to use client with ExampleClient + main below
class ExampleClient(GenericClient):
    def __init__(self, host, port, debug=True):
        super().__init__(host, port, debug)
        self.tid = None

    def parse_message(self, msg):
        header, msg = self.decode(msg)
        if len(msg) > 0 and msg[0] != ' ':
            self.dprint("Received response '", msg, "'")
            #if prev msg asked for tid
            if self.flag == 'tid':
                self.tid = int(msg[-1])
                self.dprint("my tid is ",self.tid)

        else:
            self.dprint("something went wrong :/ Aborting...")
            self.end()

        #reset flag
        self.flag = ''

    def send_message(self, msg, flag='', wait_before_sending=0):
        time.sleep(wait_before_sending)
        self.flag = flag
        super().send_message(msg)

    def decode(self, msg):
        #we know its just a msg
        return None, msg.decode('utf-8')
        
#example of how to use client with header
class ExampleClientWithHeader(GenericHeader, GenericClient):
    def __init__(self, host, port, debug=True):
        super().__init__(host, port, debug)
        self.tid = None
        self.set_header(codes=[1], fcns=[self.set_tid])

    def set_tid(self, data):
        #recieve header=1 from server
        self.tid = int(data.decode('utf-8')) 
        self.dprint("my tid is ", self.tid)

    def parse_message(self, msg):
        #header returned as int, msg returned as bytestring.decode(utf-8)
        decoded, header, msg = self.decode(msg)
        if decoded:
            return

        self.dprint("got header:msg", header, msg)

    def send_message(self, hdr, msg, wait_before_sending=0):
        time.sleep(wait_before_sending)
        self.dprint("sending message:", msg, "with header: ", hdr)
        super().send_message(msg, header=hdr)
  
#test out the client class
def main():
    #TODO make these cmd line args
    run_example = False
    run_example_with_header = True 
    host = '127.0.0.1'
    port = 1020

    if run_example:
        print("creating client")
        client = ExampleClient(host, port, debug=True)    
        client.run()    
        client.send_message("::testing", "tid")
        time.sleep(1)
        tid = client.tid 
        #tid 0 send to all, tid 1 send to 0, tid 2 send to 1
        if tid == 0 :
            print("t0 send")
            client.send_message("bcThis is C{} broadcasting.", wait_before_sending=1)
        elif tid == 1:
            print("t1 send")
            client.send_message("00This should be C 1->0", wait_before_sending=1)
        elif tid == 2:
            print("t2 send")
            client.send_message("01This should be C 2->1", wait_before_sending=1)

        time.sleep(3)
        #if > 4, theres a mistake somewhere, just abort
        if tid == 0 or tid > 4:
            client.send_message("ab...")

        print("C{} ended.".format(tid))
        client.end()
    elif run_example_with_header:
        print("creating client")
        client = ExampleClientWithHeader(host, port, debug=True)    
        client.run()    
        client.send_message(1, "Sent a tidreq msg")
        time.sleep(1)
        tid = client.tid 
        #tid 0 send to all, tid 1 send to 0, tid 2 send to 1
        #now, bc is 2, sent to x is 3+x
        if tid == 0 :
            print("t0 send")
            client.send_message(2, "This is C{} broadcasting.".format(tid), wait_before_sending=1)
        elif tid == 1:
            print("t1 send")
            client.send_message(3, "This should be C 1->0", wait_before_sending=1)
        elif tid == 2:
            print("t2 send")
            client.send_message(4, "This should be C 2->1", wait_before_sending=1)

        time.sleep(3)
        #if > 4, theres a mistake somewhere, just abort
        if tid == 0 or tid > 4:
            client.send_message(100, "ab...")

        print("C{} ended.".format(tid))
        client.end()

 
if __name__ == "__main__":
    main()