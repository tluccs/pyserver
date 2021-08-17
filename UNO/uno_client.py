#python uno_client.py
#python uno_server.py
import os
import sys
sys.path.append('../')
from pyserver.GenericServer import *
from pyserver.GenericClient import *
from UNO import uno


class UnoClient(GenericHeader, GenericClient):
    def __init__(self, host, port, debug=False):
        super().__init__(host, port, debug=debug)
        self.uno_game = uno.UnoPlayerView()
        #init_player_code = 1 #when player first connects to server, they use header=init_player_code
        recv_state_update_code = 2 #client receives msg with uno state
        #player_move_code = 3 #when player makes a move, use header=player_move_code
        codes = [recv_state_update_code]
        fcns = [self.update_client_state]
        self.set_header(codes=codes, fcns=fcns)
        self.last_uno_update = 0 #only for uno updates
        self.last_receive = 0 #for any msgs received

        
    def update_client_state(self, data):
        #Server sends us the new state
        new_state = self.bytestring_to_obj(data)
        self.uno_game.set_state(new_state)
        self.last_uno_update = time.time()
        #self.dprint("received state update from server:", new_state)

    #current player will send move, we play it on server, and send everyone an update
    def parse_message(self, data):
        decoded, header, msg = self.decode(data)
        if not decoded:
            self.dprint("Unable to decode msg: {}|{}".format(header, msg))
        self.last_receive = time.time()

    #send init_player_code
    def init_uno(self):
        self.send_message("Init message", header=1, pickle=False)

    def send_move(self, index, chosen_color=''):
        move_dict = {'index': index, 'chosen_color': chosen_color}
        self.send_message(move_dict, header=3, pickle=True)        

    def my_turn(self):
        return self.uno_game.turn == self.uno_game.player_id
        
    def uno_updated(self):
        return self.last_uno_update >= self.last_send

    def client_updated(self):
        return self.last_receive >= self.last_send

def main():
    host = '127.0.0.1'
    port = 1019
    client = UnoClient(host, port, debug=True)    
    client.run()    
    print("Client initiated!")
    #initialise state
    client.init_uno()
    while client.last_uno_update is None:
        time.sleep(0.1)
    print("Uno game init!")
    
    #play until winner
    color = ''
    while client.uno_game.winner is None:
        if client.client_updated():
            #print("client_updated!") #could be 1. your move was invalid or 2. your next move
            if client.my_turn():
                invalid_move = True
                while invalid_move:
                    #prompt user for move + send when applicable.
                    print(client.uno_game)
                    ind = int(input("index?"))
                    if client.uno_game.requires_color(ind):
                        color = input("color ('red', 'blue', 'green', 'yellow')?")
                    if client.uno_game.valid_move(ind, other_info=color):
                        #client.uno_game.play_card(ind)
                        print("Sending move: ", ind, color)
                        client.send_move(ind, color)
                        ind = 0
                        color = ''
                        invalid_move = False
                    else:
                        print("invalid move. try again")
            else:
                print(".",end="")    
            
        time.sleep(0.1)

    print("{} has won!".format(client.uno_game.winner))
    client.end()
    
if __name__ == "__main__":
    main()