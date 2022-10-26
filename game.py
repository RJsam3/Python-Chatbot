from viewer import Viewer
from streamer import Streamer
from log import game_logger
import random

#base class for multiplayer games.
class Game:
    def __init__(self, *viewers):
        self.logger = game_logger
        self.logger.info('Non-singleplayer game initializing.')
        try:
            self.player_list = [*viewers]
            self.logger.info(f'Players are: {self.player_list}')
            for player in self.player_list:
                if isinstance(player, Streamer):
                    self.streamer_playing == True
                    self.streamer = player
                    self.player_list.pop(self.player_list.index(player))
                    self.logger.info("Streamer is playing.")
        except Exception as e:
            self.logger.critical(e)
            self.logger.info('Game failed to initialize')
            return False

#class for the gambling game.
class Gamble():
    #Start the game.
    def __init__(self, player, points):
        self.logger = game_logger
        self.logger.info('Initializing gambling game.')
        self.points = points
        try:
            #If the player is a Viewer, create the game.
            if isinstance(player, Viewer):
                self.player = player
                self.logger.debug(f'Player is {self.player}.')
            else:
                raise TypeError('Player must be an instance of the viewer object.')
        except Exception as e:
            self.logger.critical(e)
            self.logger.info('Gambling Game failed to initialize.')
            return False

    #Gets a random number for the bot.
    def bot_roll(self):
        numbers = list(range(0, 101))
        random_number = random.choice(numbers)
        return random_number
        
    #Gets a random number for the player.
    def player_roll(self):
        numbers = list(range(0, 101))
        random_number = random.choice(numbers)
        return random_number

    #Determines the winner.
    def determine_winnings(self, number, player_number, points):
        #If the player number matches the bot number, the player wins double.
        if number == player_number:
            points *= 2
        #If the difference between the player number and the bot number is 25 or less, the player wins 1.50 times the amount they gambled.
        elif (number-player_number) <= 25:
            points *=1.50
        #If the difference between the player number and the bot number is 50 or less, the player wins 1.25 times the amount they gambled.
        elif (number-player_number) <= 50:
            points *= 1.25
        #If the difference between the player number and the bot number is greater than 50, the player loses all of their points.
        elif (number-player_number) > 50:
            points = 0
        return points

    #Function for the entire gamblinng game.
    def gamble(self):
        number = self.bot_roll()
        player_number = self.player_roll()
        winnings = self.determine_winnings(number, player_number, self.points)
        return winnings, player_number