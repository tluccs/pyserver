import random


#card fcns, they take in object of type UnoGame and update it
def plus_2(uno_game):
    print("+2!")
    #uno_game.player_draw(uno_game.next_player(), 2) drawing handled in player_draw
    uno_game.stack.append(2)

def turn_reverse(uno_game):
    print("no u")
    uno_game.turn_dir *= -1

def turn_skip(uno_game):
    print("skippd")
    uno_game.turn = uno_game.next_player() #gets updated again after this

def change_color(uno_game):
    print("color change!")
    uno_game.current_card.set_card(color=uno_game.chosen_color)

def plus_4(uno_game):
    print("+4!")
    uno_game.stack.append(4)
    change_color(uno_game)

def no_eff(uno_game):
    pass


#Basic uno game
class UnoGame():
    def __init__(self, num_players):
        self.deck = UnoDeck()
        self.num_players = num_players
        self.player_hands = [[]]*self.num_players
        self.current_card = None
        #whose turn
        self.turn = 0
        #ccw vs cw
        self.turn_dir = 1
        #record chain of ++
        self.stack = []
        #records user's choice of color for +4 / color change
        self.chosen_color = ''
        self.winner = None
        self.colors = ['red', 'yellow', 'green', 'blue']

    def start(self):
        for i in range(self.num_players):
            hand = self.deck.draw(6)
            self.player_hands[i] = hand
        self.current_card = self.deck.draw_one()
        while self.current_card.color not in self.colors: #if black card, just draw another
            self.deck.discard(self.current_card)
            self.current_card =  self.deck.draw_one()

    def play_card(self, index, other_info=''):
        #does not check if valid
        #if other_info is a color, set chosen_color and then check
        if other_info in self.colors:
            self.chosen_color = other_info
        player = self.turn
        if not (0 <= index < len(self.player_hands[player])) or other_info == 'draw':
            self.player_draw(player)
            #reset stack once someone draws
            self.stack = []
        else:
            self.deck.discard(self.current_card)
            self.current_card = self.player_hands[player].pop(index)
            #check gameover
            if self.check_winner(player):
                return
            self.current_card.eff(self)
        self.turn = self.next_player()
        return

    def valid_move(self, index, player=None, other_info=''):
        if player is None:
            player = self.turn
        #if someone has won, no move is valid
        if self.winner is not None:
            return False
        #if other_info is a color, set chosen_color and then check
        if other_info in self.colors:
            self.chosen_color = other_info
        #if index is invalid, treat as drawing card
        if not (0 <= index < len(self.player_hands[player])) or other_info == 'draw':
            return True
        card = self.player_hands[player][index]
        #nothing on stack, can play normally
        if len(self.stack) == 0:
            return (card.color in self.current_card.color) or (card.number == self.current_card.number) or (card.eff.__name__ != "no_eff" and card.eff.__name__ == self.current_card.eff.__name__)
        #else, must play +x card, since draw case handled above
        if 'plus' in card.eff.__name__:
            prev_plus = self.stack[-1]
            curr_plus =  int(card.eff.__name__[-1])
            #if +2, you can play +2 or +4, but if +4, you must play +4
            return curr_plus >= prev_plus
        #If not a plus card, invalid
        return False

    def requires_color(self, index):
        #check if playing card would require user to pick color
        return 0 <= index < len(self.player_hands[self.turn]) and self.player_hands[self.turn][index].color == ''

    def check_winner(self, player):
        if len(self.player_hands[player]) == 0:
            self.winner = player
            print(player, " has won!")
            return True
        return False

    def next_player(self):
        return (self.turn + self.turn_dir) % self.num_players
        
    def player_draw(self, player):
        if len(self.stack) == 0:
            n = 1 
        else:
            n = sum(self.stack)
        self.player_hands[player] += self.deck.draw(n)
 
    #returns a dict based on player knowledge
    def get_player_state(self, player_id):
        ret_dict = {}
        ret_dict['turn'] = self.turn
        ret_dict['current_card'] = self.current_card
        ret_dict['stack'] = self.stack
        ret_dict['turn_dir'] = self.turn_dir
        ret_dict['winner'] = self.winner
        ret_dict['num_players'] = self.num_players
        #ret_dict['player_hands'] = self.player_hands Not common knowledge!
        player_hands = []
        for i in range(self.num_players):
            if i == player_id:
                player_hands.append(self.player_hands[i])
            else:
                player_hands.append([UnoCard()]*len(self.player_hands[i]))
        ret_dict['player_hands'] = player_hands
        ret_dict['player_id'] = player_id # in case someone joins, this lets us assign tid=player_id in server
        return ret_dict

    def __str__(self):
        ret = ""
        for i in range(self.num_players):
            hand = [str(ind) + ':' + str(self.player_hands[i][ind]) for ind in range(len(self.player_hands[i]))]
            ret += "player {}: ".format(i) + str(hand) + "\n"
        ret += "stack: " + str(self.stack) + "\n"
        ret += "current card: " + str(self.current_card) + ". Turn: {}".format(self.turn) 
        return ret

class UnoDeck():
    def __init__(self):
        self.cards = []
        self.discard_pile = []
        self.reset_deck()

    def draw(self, n=1):
        if len(self.cards) < n:
            self.return_discard_to_deck()
        ret = self.cards[:n]
        self.cards = self.cards[n:]
        return ret

    def draw_one(self):
        return self.draw(n=1)[0]

    def shuffle(self):
        random.shuffle(self.cards)

    def reset_deck(self, nums=10):
        colors = ['red', 'blue', 'green', 'yellow']
        #basic cards x1 (40 total)
        for num in range(nums):
            for color in colors:
                self.cards.append(UnoCard(color, num))
        #2x all special for each color
        for color in colors:
            self.cards.append(UnoCard(color, -1, eff=plus_2))
            self.cards.append(UnoCard(color, -1, eff=turn_reverse))
            self.cards.append(UnoCard(color, -1, eff=turn_skip))

            self.cards.append(UnoCard(color, -1, eff=plus_2))
            self.cards.append(UnoCard(color, -1, eff=turn_reverse))
            self.cards.append(UnoCard(color, -1, eff=turn_skip))

        #4x color change and +4
        for i in range(4):
            self.cards.append(UnoCard(color="black", eff=plus_4))
            self.cards.append(UnoCard(color="black", eff=change_color))

        self.shuffle()

    def return_discard_to_deck(self):
        self.deck += self.discard_pile
        self.discard_pile =  []
        self.shuffle()

    def discard(self, card):
        self.discard_pile.append(card)

    def __str__(self):
        return str([str(card) for card in self.cards])

#encode black cards (any color) as '', and numberless as -1
class UnoCard():
    def __init__(self, color='unknown', number=-1, eff=no_eff):
        self.set_card(color, number, eff)

    def set_card(self, color=None, number=None, eff=None):
        if color is not None:
            #encode black cards as '' to make valid check easier
            if color == "black":
                color = ""
            self.color = color
        if number is not None:
            self.number = number
        #on-play effect
        if eff is not None:
            self.eff = eff

    def __str__(self):
        if self.color == 'unknown':
            return "unknown"
        elif self.number >= 0 and len(self.color) > 0:
            return self.color + "_" + str(self.number)
        elif  len(self.color) > 0:
            return self.color + "_" + self.eff.__name__ 
        else:
            return "black_" + self.eff.__name__

#This is what a single player can see (what is public knowledge + player hand)
class UnoPlayerView(UnoGame):
    def __init__(self, num_players=1, player_id=1):
        super().__init__(num_players)
        #you shouldn't know what's in the deck
        self.deck = None 
        self.player_id = player_id

    def play_card(self, index, other_info=''):
        print("You can play by sending msg to server!")

    def valid_move(self, index, player=None, other_info=''):
        if (player is None and self.turn == self.player_id) or player == self.player_id:
            return super().valid_move(index, player, other_info)
        else:
            print("Not your turn / can't check if someone else's move is valid!")
            return False

    def set_state(self, state_dict):
        for name in state_dict:
            self.__dict__[name] = state_dict[name]

    def __str__(self):
        ret = super().__str__()
        ret += '\nYou are player {}'.format(self.player_id)
        return ret 

if __name__ == "__main__":
    #test the uno game rules
    
    game = UnoGame(3)
    game.start()
    
    while game.winner is None:
        print(game)
        ind = int(input("index?"))
        if game.requires_color(ind):
            color = input("color?")
            game.chosen_color = color
        if game.valid_move(ind):
            game.play_card(ind)
        else:
            print("invalid move. try again")

