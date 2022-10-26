import chat4j_queries
from log import viewer_logger

#Class for the Viewer object.
class Viewer:
    #Initialize the Viewer and all required variables.
    def __init__(self, username, streamer):
        self.QueryDriver = chat4j_queries.BotQueries()
        self.logger = viewer_logger
        self.username = str(username)
        self.stats = self.QueryDriver.Run_get_stats(self.username, streamer)
        self.friends_list = self.QueryDriver.Run_get_friends(username)
        self.liked_genres = self.QueryDriver.Run_get_liked_genres(username)
        self.is_online = True

    #getters
    #get the username.
    def get_username(self):
        return self.username
    
    #get the stats.
    def get_stats(self):
        #If the stats query failed, return false.
        if self.stats == False:
            return False
        else:
            return self.stats
    
    #Gets tthe is_online boolean.
    def get_is_online(self):
        return self.is_online

    #Gets the friends list.
    def get_friends_list(self):
        #Return false if the query failed.
        if self.friends_list == False:
            return False
        else:
            return self.friends_list

    #Gets the liked genres.
    def get_liked_genres(self):
        #Return false if the query failed.
        if self.liked_genres == False:
            return False
        else:
            return self.liked_genres

    #updates
    #Update is_online to the opposite value.
    def update_is_online(self):
        if self.is_online == False:
            self.is_online = True
            self.logger.info('is_online changed to True.')

        else:
            self.is_online = False
            self.logger.info('is_online changed to False.')

    #Update tthe given stat to the new value.
    def update_stat(self, stat, operator=None, value=None):
        if stat == 'query_count':
            self.QueryDriver.Run_increase_query_count(self.username)
            self.stats['query_count'] += 1
            self.logger.info('Query_count for {user} updated to {query_count}.'.format(user = self.username, query_count=self.stats['query_count']))
        elif stat == 'created_on':
            self.logger.error('Cannot change created_on date.')
            return False
        elif stat == 'points':
            self.QueryDriver.Run_increase_query_count(self.username)
            if operator == 'add':
                self.stats['points'] += value
                self.logger.info('Points for {user} updated to {points}.'.format(user = self.username, query_count=self.stats['points']))
            elif operator == 'subtract':
                self.stats['points'] -= value
                self.logger.info('Points for {user} updated to {points}.'.format(user = self.username, query_count=self.stats['points']))
            else:
                self.logger.error('Points can only be added or removed.')
                return False

    #Add a user to the friend list.
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

    #Add a genre to the liked genre list.
    def update_liked_genres(self, new_genre):
        if new_genre in self.liked_genres:
            self.logger.warning(f'{new_genre} is already in liked genres. Ignnoring.')
            return False
        else:
            self.QueryDriver.Run_set_likes_genre(self.username, new_genre)
            self.update_stat('query_count')
            self.logger.info(f"{new_genre} added to liked genres for {self.username}")
            self.liked_genres.append(new_genre)

