from neo4j import GraphDatabase
from  log import query_logger
import config

#This class handles all queries to the databse. It is divided between functions that have the queries, and functions that create trannsactions for query functions.
class BotQueries:
    def __init__(self):
        self.driver = GraphDatabase.driver(config.DB, auth=(config.DB_USER, config.DB_PASS))
        try:
            self.driver.verify_connectivity()
            query_logger.info("Bot Queries Driver Initialized.")
        except Exception as e:
            query_logger.critical(e)


    #Query functions,to be used by the run functions. They define the transaction used for the run function.
    #Remove a user's node and all relationships.
    def Query_remove_user(self, tx, username):
        query = ("""MATCH (p:Person) DETACH DELETE p""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, username=username)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False

    #Adds a user to the database. 
    def Query_add_user(self, tx, username):
        query = ("MERGE (p:Person {username: $username}) SET p.created_on = date(), p.query_count= 1")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, username=username)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False

    #Adds a friendship between two users.
    def Query_add_friendship(self, tx, username1, username2):
        query = ("""MATCH (p1:Person)
            WHERE p1.username = $p1name
            MATCH (p2:Person)
            WHERE p2.username = $p2name
            MERGE (p1)-[r:IS_FRIENDS {start_date: date()}]->(p2)""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, p1name=username1, p2name=username2)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Arguements used: 1. {username1} 2. {username2}')
            return False

    #Gets all users that the sending user is friends with.
    def Query_get_friends(self, tx, username):
        friends_list=[]
        query = ("MATCH (n:Person {username: $username})-[:IS_FRIENDS]-(f:Person) RETURN f")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query, username=username)
            #For each record in results, get the username value from that record.
            for record in results:
                node = record["f"]
                name = node["username"]
                #If the name is in friends list already, pass.
                if name in friends_list:
                    pass
                #If the above is false, add the name to the list.
                else:
                    friends_list.append(name)
            query_logger.info(friends_list)
            return friends_list
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False

    #Gets all users currently in the database. (This specifically grabs all nodes with the :Person label)
    def Query_all_user(self, tx):
        users=[]
        query=("MATCH (p:Person) RETURN p ORDER BY p.name")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query)
            #For each record in results, get the username value from that record.
            for record in results:
                node = record['p']
                username = node['username']
                users.append(username)
            query_logger.info(users)
            return users
        except Exception as e:
            query_logger.error(e)
            query_logger.debug('No arguments used.')
            return False

    #Gets the personal statistics of the user who sent the command.
    def Query_get_stats(self, tx, username, streamer):
        stats = {}
        try:
            #If the streamer is not the user, get the stats for the user.
            if streamer != username:
                query_logger.info(f'{username} is not the streamer.')
                query = ('''MATCH (p:Person)-[r:VIEWS]->(p2:Person) WHERE p.username = $username AND p2.username=$streamer RETURN p.created_on AS created, p.query_count AS count, r.points AS points''')
                results = tx.run(query, username=username, streamer=streamer)
                #For each record in results, get the created, count, and points values from that record.
                for record in results:
                    stats['created_on'] = str(record['created'])
                    stats['query_count'] = record['count']
                    stats['points'] = record['points']
                query_logger.info(stats)
                return stats
            #If the streamer is the user, get the stats for the streamer.
            elif streamer == username:
                query_logger.info('{username} is the streamer.')
                query =  ('MATCH (p:Person) WHERE p.username = $username RETURN p.created_on AS created, p.query_count as count')
                query_logger.info(f'Running query: {query}')
                results = tx.run(query, username=username)
                #For each record in results, get the created, and count values from that record.
                for record in results:
                    stats['created_on'] = str(record['created'])
                    stats['query_count'] = record['count']
                query_logger.info(stats)
                return stats
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False

    #Increase the user's query_count property by 1.
    def Query_increase_query_count(self, tx, username):
        query = ("""MATCH (p:Person {username: $username}) SET p.query_count = p.query_count + 1""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, username=username)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False
    
    #Gets all genres.
    def Query_get_genres(self, tx):
        genres = []
        query = ("MATCH  (g:Genre) RETURN g")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query)
            #For each record in results, get the genre value from that record.
            for record in results:
                node=record['g']
                genre = node['genre']
                genres.append(genre)
            query_logger.info(genres)
            return genres
        except Exception as e:
            query_logger.error(e)
            query_logger.debug('No arguments used.')
            return False
            
    #Sets a :LIKES_GENRE relationship from the user to the genre.
    def Query_set_likes_genre(self, tx, username, genre):
        query = ("""MATCH (p:Person)
            WHERE p.username = $pname
            MATCH (g:Genre)
            WHERE g.genre = $genre
            MERGE (p)-[r:LIKES_GENRE {start_date: date()}]->(g)""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, pname=username, genre=genre)
        except Exception as e:
            query_logger.error(e)
            query_logger.info(f'Arguments used: 1. {username} 2. {genre}')
            return False

    #Gets all genres the sending user has a :LIKES_GENRE relationship to.
    def Query_get_liked_genres(self, tx, username):
        liked_genres = []
        query = ("""MATCH (p:Person)-[:LIKES_GENRE]->(g) WHERE p.username = $username RETURN g""")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query, username=username)
            #For each record in results, get the genre value from that record and add it to tthe liked genres list.
            for record in results:
                node = record['g']
                genre = node['genre']
                liked_genres.append(genre)
            query_logger.info(liked_genres)
            return liked_genres
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False
            
    #Creates a person node, and a :VIEWS relationship between it and another person node.
    def Query_create_user_views(self, tx, username1,  username2):
        query = ("""MERGE (p:Person {username: $username1})
                    WITH p 
                    MATCH (s:Person {username: $username2})
                    MERGE (p)-[r:VIEWS {created_on: date()}]->(s)
                    SET p.created_on = date()
                    SET p.query_count = 1
                    set r.points = 100""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, username1=username1, username2=username2)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Arguements used: 1. {username1} 2. {username2}')
            return False

    #Creates a :VIEWS relationship between two existing person nodes.
    def Query_create_views(self, tx, username1, username2):
        query = ("""MATCH (p:Person {username: $username1})
                    MATCH (s:Person {username: $username2})
                    MERGE (p)-[r:VIEWS {created_on: date()}]->(s)
                    SET r.points = 100""")
        query_logger.info(f'Running query: {query}')
        try:
            tx.run(query, username1=username1,  username2=username2)
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Arguements used: 1. {username1} 2. {username2}')
            return False

    #Gets all person nodes that have a :VIEWS relationship to the specified person node.
    def Query_viewers(self, tx, username):
        viewers =  []
        query  = ("""MATCH (p:Person {username: $username})<-[:VIEWS]-(v:Person) RETURN v AS viewer""")
        query_logger.info(f'Running query: {query}')
        try:
            results =  tx.run(query, username=username)
            #For each record in results, get the username value from that record.
            for record in results:
                node = record['viewer']
                viewer = node['username']
                viewers.append(viewer)
            query_logger.info(viewers)
            return viewers
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False

    #Gets a dictionary where the keys are Genres and the values are the amount of viewers of the specified user who like that genre.
    def Query_get_viewer_liked_genres(self, tx, username):
        genre_suggest_dict = {}
        query = ("""MATCH path = ((g:Genre)<-[:LIKES_GENRE]-(p:Person)-[:VIEWS]->(s:Person {username: $username}))
                    RETURN g.genre AS genre, count(path) AS pathcount ORDER BY pathcount DESC""")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query, username=username)
            #For each record in results, get the genre and pathcount value from that record. Thenn add them to a dictionnary where genre is tthe key and pathcount is the value.
            for record in results:
                genre_suggest_dict[record['genre']] = record['pathcount']
            query_logger.info(genre_suggest_dict)
            return genre_suggest_dict
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False


    #Gets a dictionary where the keys are usernames who view the specified user, and the values are the query counts.
    def Query_get_query_count_leader(self, tx, username):
        count_leader={}
        query = ("""MATCH (p:Person)-[:VIEWS]->(s:Person {username: $username})
                    RETURN p.username AS username, p.query_count AS queries ORDER BY queries DESC LIMIT 1""")
        query_logger.info(f'Running query: {query}')
        try:
            results = tx.run(query, username=username)
            #For each record in results, get the username and queries values from that record. Then add them to a dictionary with the username as the key and the quieries as the value.
            for record in results:
                count_leader[record['username']] = record['queries']
            query_logger.info(count_leader)
            return count_leader
        except Exception as e:
            query_logger.error(e)
            query_logger.debug(f'Argument used: {username}')
            return False



    #Run functions. These are the functions that execute the query functions in the database.
    #Runs a query that will remove a user's node and relationships from the database.
    def Run_remove_user(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_remove_user, username)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
                return False
            finally:
                session.close()

    #Runs an add node query to create a person node with the username property set to the sending user's username
    def Run_add_user(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_add_user, username)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
                return False
            finally:
                session.close()
            
    #Runs an add IS_FRIENDS relationship query to create a relationship between two users. The relaionship direction is user1->user2
    def Run_add_friendship(self, user1, user2):
        query_logger.info(f'Command Received. Arguments: 1. {user1} 2. {user2}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_add_friendship, user1,  user2)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Arguments used: 1. {user1} 2. {user2}')
            finally:
                session.close()

    #Runs a read only query that will return a list of all users the sending user is friends with
    def Run_get_friends(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                friends = session.execute_read(self.Query_get_friends, username)
                #If query fails, raise an error.
                if friends == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                else: 
                    return friends
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()
            
    #Runs a read only query that will return all users currently in the database. (Specifically all nodes with the Person label)
    def Run_all_user(self):
        query_logger.info(f'Command Received. Argument: None')
        with self.driver.session() as session:
            try:
                users = session.execute_read(self.Query_all_user)
                #If query fails, raise an error.
                if users == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                else: 
                    return users
            except Exception as e:
                query_logger.error(e)
                query_logger.debug('No arguments used.')
            finally:
                session.close()

    #Runs a read only query that will return all user stats for the selected user.
    def Run_get_stats(self, username, streamer):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                stats = session.execute_read(self.Query_get_stats, username, streamer)
                #If query fails, raise an error.
                if stats == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                else: 
                    return stats
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()

    #Runs a query that will increase the query_count property on the specified node by 1.
    def Run_increase_query_count(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_increase_query_count, username)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()

    #Runs a read only query that will get all genres.
    def Run_get_genres(self):
        query_logger.info(f'Command Received. Argument: None')
        with self.driver.session() as session:
            try:
                genres = session.execute_read(self.Query_get_genres)
                #If query fails, raise an error.
                if genres == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                return genres
            except Exception as e:
                query_logger.error(e)
                query_logger.debug('No arguments used.')
            finally:
                session.close()
            
    #Runs a query that will set a :LIKES_GENRE relationship between the specified user and the specified genre.
    def Run_set_likes_genre(self, username, genre):
        query_logger.info(f'Command Received. Arguments: 1. {username} 2. {genre}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_set_likes_genre, username, genre)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Arguments used: 1. {username} 2. {genre}')
            finally:
                session.close()

    #Runs a read only query that will retrieve all genres the specified user has a :LIKES GENRE relationship to.
    def Run_get_liked_genres(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                liked_genres = session.execute_read(self.Query_get_liked_genres, username)
                #If query fails, raise an error.
                if liked_genres == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                return liked_genres
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()
            
    #Runs a query that creates a person node, and creates a views relationship between it and another person node.
    def Run_create_user_views(self, username1, username2):
        query_logger.info(f'Command Received. Arguments: 1. {username1}  2. {username2}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_create_user_views, username1, username2)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Arguments used: 1. {username1} 2. {username2}')  
            finally:   
                session.close()

    #Runs a query that creates a :VIEWS relationship between to person nodes.
    def Run_create_views(self, username1, username2):
        query_logger.info(f'Command Received. Arguments: 1. {username1} 2. {username2}')
        with self.driver.session() as session:
            try:
                query = session.execute_write(self.Query_create_views, username1, username2)
                #If query fails, raise an error.
                if query == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Arguments used: 1. {username1} 2. {username2}')
            finally:
                session.close()

    #Runs a query that returns all Person nodes with a :VIEWS relationship to the specified user.
    def Run_get_viewers(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                viewers = session.execute_read(self.Query_viewers, username)
                #If query fails, raise an error.
                if viewers == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                return viewers
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()
            
    #Runs a read only query that returns a dictionary where the keys are genres and the values are the count of viewers of the specified user who like that genre
    def Run_get_viewer_liked_genres(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                genre_suggest_dict = session.execute_read(self.Query_get_viewer_liked_genres, username)
                #If query fails, raise an error.
                if genre_suggest_dict == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                return genre_suggest_dict
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()

    #Runs a read only query that returns a dict where the keys are viewers of the specified channel, and the values are their query_counts.
    def Run_get_query_count_leader(self, username):
        query_logger.info(f'Command Received. Argument: {username}')
        with self.driver.session() as session:
            try:
                count_leader = session.execute_read(self.Query_get_query_count_leader, username)
                #If query fails, raise an error.
                if count_leader == False:
                    raise ValueError('Failed to execute query. Please check arguments or cypher syntax and try again.')
                return count_leader
            except Exception as e:
                query_logger.error(e)
                query_logger.debug(f'Argument used: {username}')
            finally:
                session.close()
