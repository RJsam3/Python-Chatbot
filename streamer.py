import chat4j_queries
from log import streamer_logger

class Streamer():
    def __init__(self, username):
        self.QueryDriver = chat4j_queries.BotQueries()
        self.logger = streamer_logger
        self.username = str(username)
        self.stats = self.QueryDriver.Run_get_stats(self.username, streamer=self.username)
        self.friends_list = self.QueryDriver.Run_get_friends(username)
        self.liked_genres = self.QueryDriver.Run_get_liked_genres(username)
        self.command_prefix = '$'
        self.points_name = 'points'
        self.state = {'template_commands', 'reminders'}
        self.state_filename = f'Chatbot\states\{self.username}.JSON'
        self.state_schema  = {
            'template_commands': {"boop": "{message.user} boops {message.text_args[0]}'s snoot!", 
            "so": "Check out {message.text_args[0]}'s stream! Here's a link: https://www.twitch.tv/{message.text_args[0]}", 
            "pizza": "{message.user} will be getting a pizza in the mail in a few years.", 
            "headpat": "{message.user} gives {message.text_args[0]} headpats!"},
            'reminders' : {}
        }

    #getters
    def get_username(self):
        return self.username
    
    def get_stats(self):
        if self.stats == False:
            return False
        else:
            return self.stats

    def get_friends_list(self):
        if self.friends_list == False:
            return False
        else:
            return self.friends_list

    def get_liked_genres(self):
        if self.liked_genres == False:
            return False
        else:
            return self.liked_genres
    
    def get_command_prefix(self):
        return self.command_prefix

    def get_points_name(self):
        return self.points_name

    #updates
    def update_stat(self, stat):
        if stat == 'query_count':
            self.QueryDriver.Run_increase_query_count(self.username)
            self.stats['query_count'] += 1
            self.logger.info('Query_count for {user} updated to {query_count}.'.format(user = self.username, query_count=self.stats['query_count']))
        elif stat == 'created_on':
            self.logger.error('Cannot change created_on date.')
            return False

    def update_friends_list(self, new_friend):
        if new_friend in self.friends_list:
            self.logger.warning(f"{new_friend} is already on {self.username}'s friend list. Ignoring")
            return False
        else:
            try:
                query = self.QueryDriver.Run_add_friendship(self.username, new_friend)
                if query == False:
                    raise ValueError('Runn function returned false.')
                self.update_stat('query_count')
                self.logger.info(f"{new_friend} added to friend list for {self.username}")
                self.friends_list.append(new_friend)
            except Exception as e:
                self.logger.error(e)
                self.logger.debug(f'Argument used: {new_friend}')
                return False

    def update_liked_genres(self, new_genre):
        if new_genre in self.liked_genres:
            self.logger.warning(f'{new_genre} is already in liked genres. Ignnoring.')
            return False
        else:
            self.QueryDriver.Run_set_likes_genre(self.username, new_genre)
            self.update_stat('query_count')
            self.logger.info(f"{new_genre} added to liked genres for {self.username}")
            self.liked_genres.append(new_genre)

    def set_command_prefix(self, prefix):
        self.command_prefix = prefix
    
    def set_points_name(self, name):
        self.points_name = name

