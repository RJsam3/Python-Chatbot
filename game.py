from viewer import Viewer
from streamer import Streamer
from log import game_logger
import random

#base class for multiplayer games
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
    def __init__(self, player, points):
        self.logger = game_logger
        self.logger.info('Initializing gambling game.')
        self.points = points
        try:
            if isinstance(player, Viewer):
                self.player = player
                self.logger.debug(f'Player is {self.player}.')
            else:
                raise TypeError('Player must be an instance of the viewer object.')
        except Exception as e:
            self.logger.critical(e)
            self.logger.info('Gambling Game failed to initialize.')
            return False

    def bot_roll(self):
        numbers = list(range(0, 101))
        random_number = random.choice(numbers)
        return random_number
        
    def player_roll(self):
        numbers = list(range(0, 101))
        random_number = random.choice(numbers)
        return random_number

    def determine_winnings(self, number, player_number, points):
        if number == player_number:
            points *= 2
        elif (number-player_number) <= 25:
            points *=1.50
        elif (number-player_number) <= 50:
            points *= 1.25
        elif (number-player_number) > 50:
            points = 0
        return points

    def gamble(self):
        number = self.bot_roll()
        player_number = self.player_roll()
        winnings = self.determine_winnings(number, player_number, self.points)
        return winnings, player_number