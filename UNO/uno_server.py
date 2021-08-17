#python uno_server.py
import os
import sys
sys.path.append('../')
#print(sys.path)
from pyserver.GenericServer import *
from UNO import uno

#UnoServer:
#   Clients will have the client version of unogame class- 
#       contains num cards each player has, current card, clients cards, and the stack
#   Validity check will be at client (for user) and server (for security/anti cheat)
#       So when a client makes a move, they 1. play it on their copy of the game and 2. send it to server
#       server will then broadcast an update + play the move on its copy of the game
#       Necesarily, when a client receives a broadcasted message they must update their copy of the game
class UnoServer(GenericHeader, GenericServer):
    def __init__(self, max_connections, host, port, debug=False):
        super().__init__(max_connections, host, port, debug=debug)
        self.uno_game = uno.UnoGame(max_connections)
        init_player_code = 1 #when player first connects to server, they use header=init_player_code
        #code 2 used in client
        player_move_code = 3 #when player makes a move, use header=player_move_code
        codes = [init_player_code, player_move_code]
        fcns = [self.send_state, self.update_state]
        self.set_header(codes=codes, fcns=fcns)
        
    #works with header code and can be called in other functions too
    def send_state(self, data=None, tid=None):
        if tid is None:
            self.dprint("Note: got tid=None in send_state")
            return
        #if data is None, that means we call to send a state update to clients
        if data is not None:
            self.dprint("received message from user", data.decode('utf-8'), "With tid=", tid, "Sending state.")
        state = self.uno_game.get_player_state(tid)
        #0 is for self. vars, this is self.uno_game var so use header=2, handled in client
        self.send_message(state, tid, header=2, pickle=True) 

    #Note this is diff from send_state; which occurs when client connects w server + sends only to that client
    # This is for client playing a move + updating and sending to all clients
    def update_state(self, data, tid=None):
        #check if all players connected. If not, alert client
        if len(self.thread_status) != self.max_connections:
            self.send_message("Not all clients connected yet, please wait", tid, header=123) #any invalid header
            return

        if tid is None:
            self.dprint("Note: got tid=None in update_state")
            return
        elif tid != self.uno_game.turn:
            self.dprint("Note: user {} tried to move on turn {}".format(tid, self.uno_game.turn))
            #in this case, sync up state in case client has bad version
            self.send_state(tid=tid)
            return

        #player made this move (color + index) so check if valid and play game.
        update = self.bytestring_to_obj(data)
        index = update['index']
        if 'chosen_color' in update:
            chosen_color = update['chosen_color']
        else:
            chosen_color = ''

        if self.uno_game.valid_move(index, player=tid, other_info=chosen_color):
            self.uno_game.play_card(index, other_info=chosen_color)
        else:
            self.send_message("Your move {} is invalid".format(index), tid, header=123) #any invalid header
            #in this case, sync up state in case client has bad version
            self.send_state(tid=tid)
            return

        #Now to broadcast the update to everyone
        for tid in range(len(self.connections)):
            self.send_state(tid=tid)

    #current player will send move, we play it on server, and send everyone an update
    def parse_message(self, data, tid):
        decoded, header, msg = self.decode(data, tid=tid)
        if not decoded:
            self.dprint("Unable to decode msg: {}|{}".format(header, msg))
        

def main():
    host = '127.0.0.1'
    port = 1019
    num_players = 1 #the above vars should be cmd line args
    print("creating server thread")
    serv = UnoServer(num_players, host, port, debug=True)
    serv.run()
    i = 0
    period = 3
    timeout = 20
    serv.uno_game.start()
    serv.last_send = time.time() #hacky way to get timeout to work rn
    while serv.uno_game.winner is None:
        print("Sleep... ({})".format(i))
        time.sleep(period)
        i += 1
        #check if any progress made within last n sec
        dt = time.time() - serv.last_send
        #check if one period has gone by without any messages sent. Acts as a fail-safe
        if dt > timeout:
            print("server made no progress. Ending server...")
            break

    if serv.uno_game.winner is not None:
        print("Winner! Ending.")
    else:
        print("no winner, just ending...")
    serv.end()
    
if __name__ == "__main__":
    main()