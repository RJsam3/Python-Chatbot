import socket
from collections import namedtuple
import config
from chat4j_queries import BotQueries
from time import sleep
import ssl
import json
from log import bot_function_logger, command_logger
from viewer import Viewer
from streamer import Streamer
import os
import asyncio
import game
import random

#Chat message namedTuple used in the parse message functionality. Makes it easy to identify what parts of the message are needed for chat commands.
Message = namedtuple('Message', 'prefix user channel irc_command irc_args text text_command text_args', )
            
#This function removes the command prefix from a string.
def remove_prefix(string, prefix):
    if not string.startswith(prefix):
        return string
    else:
        return string[len(prefix):]




#The main bot class. Most functionality happens with this class.
class Bot:
    #Sets necessary variables for various bot and command functions.
    def __init__(self):
        self.bot_logger = bot_function_logger
        self.command_logger = command_logger
        self.bot_logger.info("Bot initializing...")
        self.irc_server = 'irc.chat.twitch.tv'
        self.irc_port = 6697
        self.oauth_token = config.OAUTH_TOKEN
        self.username = config.USERNAME
        self.channels = [config.CHANNEL]
        self.streamer = Streamer(self.channels[0])
        self.users = []
        self.channel_viewers = []
        self.viewer_object_list = []
        self.viewer_features_dictionary = {}
        self.queue = []
        self.custom_commands = {
            'help': self.command_help,
            'optout':  self.remove_user,
            'querycommands': self.list_query_commands,
            'query_add_streamer': self.set_add_user,
            'query_set_friend': self.set_friendship,
            'query_get_friends': self.get_friends,
            'query_get_stats': self.get_stats,
            'query_get_genres': self.get_genres,
            'query_like_genre': self.set_likes_genre,
            'query_get_liked_genres': self.get_liked_genres,
            'query_get_viewers': self.get_viewers,
            'query_suggest_genre': self.suggest_genres,
            'query_countleader': self.get_query_count_leader,
            'add_command': self.add_command,
            'edit_command': self.edit_command,
            'delete_command': self.delete_command,
            'new_prefix': self.set_command_prefix,
            'gamble': self.gamble,
            'joke': self.read_random_joke,
            'addjoke': self.add_joke,
            '8ball': self.eight_ball,
            'addpoints': self.add_points,
            'removepoints': self.remove_points,
            'donate': self.donate_points,

        }
        self.bot_logger.info('Initialized.')
    
    #Ensures the streamer has the required schema in a .JSON file with their twitch name.
    def ensure_state_schema(self):
        self.bot_logger.info('Ensuring schema is set.')
        is_dirty = False
        if self.streamer.state_schema == {}:
            self.bot_logger.info('Schema ensured.')
            return is_dirty
        for key in self.streamer.state_schema:
            if key not in self.streamer.state:
                self.bot_logger.warning(f'{key} not in state. Setting is_dirty to true.')
                is_dirty = True
                self.streamer.state[key] = self.streamer.state_schema[key]
        if is_dirty == True:
            self.bot_logger.warning('Schema is not set or improperly set.')
        self.bot_logger.debug(f'{is_dirty}')
        return is_dirty

    #Reads the .JSON file for the streamer. Creates it if it does not exist.
    def read_state(self):
        if not os.path.exists(self.streamer.state_filename):
            with open(self.streamer.state_filename, 'w') as file:
                file.write('{}')
        with open(self.streamer.state_filename, 'r') as file:
            self.streamer.state = json.load(file)
        self.bot_logger.debug(f'{self.streamer.state}')
        is_dirty = self.ensure_state_schema()
        if is_dirty == True:
            self.bot_logger.warning('Schema improperly set. Overwriting.')
            self.write_state()
        
    #Rewrites the streamers .JSON file if it does not match the set schema.
    def write_state(self):
        with open(self.streamer.state_filename, 'w') as file:
            json.dump(self.streamer.state, file)
            self.bot_logger.info('Schema updated.')

    #If the parsed message is a template command, this function attempts to send the appropriate response.
    def handle_template_command(self, message, text_command, template):
        try:
            text = template.format(**{'message': message})
            self.send_privmsg(message.channel, text)
            self.command_logger.info(f'Sent template command response: {text} Channel: {message.channel}')
        except Exception as e:
            if message.text_args == []:
                self.send_privmsg(message.channel, f'{message.text_command} requires at least one argument. Please try again.')
            else:
                self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax or ask Nivecgos for help..')
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')

    #The main message handling function, handles JOIN, PING, PART, and PRIVMSG messages.
    async def handle_message(self, received_msg):
        #Handles empty messages. This happens a lot.
        if len(received_msg) == 0:
            self.bot_logger.warning('Received empty message.')
            return
        message = self.parse_message(received_msg)
        self.bot_logger.info(f'Received message: {received_msg}')
        self.bot_logger.debug(f'Named Tuple: {message}')

        #Handles PING messages. Response with a PONG message.
        if message.irc_command == 'PING':
            self.send_command('PONG :tmi.twitch.tv')
            self.bot_logger.info('Received PING. Replied PONG.')
        
        #Handles JOIN messages whenever they appear. These do not appear often enough for this feature to be fully functional, and is essentially turned off after 1k viewers.
        if message.irc_command == 'JOIN':
            self.bot_logger.info('JOIN message received.')
            self.bot_logger.debug(f'Viewer List: {self.channel_viewers}')
            #The bot ignores JOIN messages from the streamer.
            if message.user == message.channel:
                self.bot_logger.debug(f'{message.user} is the streamer. Ignoring.')
                return

            #The bot ignores JOIN messages from itself.
            elif message.user == self.username:
                self.bot_logger.debug(f'{message.user} is me. Ignoring.')
                return

            #The bot checks to see if the viewer is already in its database, and adds them if not. It then notifies them and tells them how to opt out.
            if message.user not in self.users:
                self.bot_logger.info(f'{message.user} is new. Adding to database.')
                self.create_user_views(message)
                self.bot_logger.debug(f'Runninng create_user_views with argument: {message}')
                self.create_views(message)
                self.bot_logger.debug(f'Runninng create_views with argument: {message}')
                self.users.append(message.user)
                self.bot_logger.debug(f'{message.user} appended to user list.')
                self.send_privmsg(message.channel, f"Welcome to the stream, {message.user}! I am a bot that is currently in testing. If you would like help with my features, please use {self.command_prefix}help. If you would like to opt out of testing features that require me to remember your username, please use the command {self.command_prefix}optout")
                self.bot_logger.info(f'Join for {message.user} processed.')

            #The bot checks if they are listed as a viewer for this channel, and creates the relationship and adds them to its list if they are not.
            if message.user not in self.channel_viewers:
                self.bot_logger.debug(f'Runninng create_user_views with argument: {message}')
                self.create_views(message)
                self.channel_viewers.append(message.user)
                self.bot_logger.debug(f'{message.user} appended to viewer list.')

            #If all of the above conditions are false, the viewer is not new, and the bot welcomes them to the chat.
            else:
                self.bot_logger.info(f'{message.user} is in user and viewer list.')
                self.send_privmsg(message.channel, f"Welcome back, {message.user}! I'm so glad to see you again!")
                self.bot_logger.info(f'Welcome back sent to: {message.user}')

            #The bot then checks if the viewer is in the dictionary of Viewer object indexes. 
            #If not, it creates a Viewer object, adds it to the list of Viewer objects, and assigns their username as a key with the value being their index in the list of objects.
            if message.user not in self.viewer_features_dictionary.keys():
                self.bot_logger.info(f'Creating viewer object for {message.user}.')
                viewer = Viewer(message.user, message.channel)
                self.viewer_object_list.append(viewer)
                viewer_dictionary_count = len(self.viewer_object_list) - 1
                self.viewer_features_dictionary[self.viewer_object_list[viewer_dictionary_count].username] = viewer_dictionary_count

            #If the viewer is already in the dictionary, it sets their status as online.
            else:
                self.bot_logger.info(f'{message.user} already has a viewer object.')
                self.viewer_object_list[self.viewer_features_dictionary[message.user]].update_is_online()

        #Handles PART messages when they appear. These do not appear often enough for this feature to be fully functional, and is essentially turned off after 1k viewers.
        if message.irc_command == 'PART':
            self.bot_logger.info(f'PART message received from: {message.user}')
            self.viewer_object_list[self.viewer_features_dictionary[message.user]].update_is_online()
            self.send_privmsg(message.channel, f'{message.user} has died. F.')
        
        #Handles PRIVMSG messages when they appear. This is the most common message type.
        if message.irc_command == 'PRIVMSG':
            self.bot_logger.info(f'Received PRIVMSG from: {message.user}')

            #If the text_command portion of the message is a custom command, call the apropriate custom command function.
            if message.text_command in self.custom_commands:
                self.bot_logger.info('Custom command received.')

                #If the custom command is a query command, increase query count before running the command.
                if message.text_command.startswith('query_'):
                    self.bot_logger.info('Query command recognized.')
                    self.QueryDriver.Run_increase_query_count(message.user)
                    self.bot_logger.info('Query command processed.')
                self.custom_commands[message.text_command](message)
                self.bot_logger.info('Custom command processed.')
            
            #if the command is a template command, call the handle template command function.
            elif message.text_command in self.streamer.state['template_commands']:
                self.bot_logger.info('Template command recognized.')
                self.handle_template_command(message, message.text_command, self.streamer.state['template_commands'][message.text_command])
                self.bot_logger.info('Template Command processed.')
        
    #Removes unneeded twitch info from the chat message.
    def get_user_from_prefix(self, prefix):
        domain = prefix.split('!')[0]
        if domain.endswith('.tmi.twitch.tv'):
            return domain.replace('.tmi.twitch.tv', '')
        if '.tmi.twitch.tv' not in domain:
            return domain

    #Parses a message into the Message namedTuple.
    def parse_message(self, received_msg):
        parts = received_msg.split(' ')
        prefix = None
        user = None
        channel = None
        text = None
        text_command = None
        text_args = None
        irc_command = None
        irc_args = None
        if parts[0].startswith(':'):
            prefix = remove_prefix(parts[0], ':')
            user = self.get_user_from_prefix(prefix)
            parts = parts[1:]
        text_start = next(
            (idx for idx, part in enumerate(parts) if part.startswith(':')),
            None
        )
        if text_start is not None:
            text_parts = parts[text_start:]
            text_parts[0] = text_parts[0][1:]
            text = ' '.join(text_parts)
            if text_parts[0].startswith(self.streamer.command_prefix):
                text_command = remove_prefix(text_parts[0], self.streamer.command_prefix)
                text_args = text_parts[1:]
            parts = parts[:text_start]
        irc_command = parts[0]
        irc_args = parts[1:]
        hash_start = next(
            (idx for idx, part in enumerate(irc_args) if part.startswith('#')),
            None
        )
        if hash_start is not None:
            channel = irc_args[hash_start][1:]
        message = Message(
            prefix=prefix,
            user=user,
            channel=channel,
            text=text,
            text_command=text_command,
            text_args=text_args,
            irc_command=irc_command,
            irc_args=irc_args,
        )
        return message

    #The main loop for chat messages. assigns each message to a task and handles the tasks conncurrently if htere are tasks in the list.
    async def loop_for_messages(self):
        tasks = []
        while True:
            received_msgs = self.irc.recv(2048).decode()
            #for received_msg in received_msgs.split('\r\n'):
                #self.handle_message(received_msg)
            for msg in received_msgs.split('\r\n'):
                tasks.append(self.handle_message(msg))
            if len(tasks) != 0:
                await asyncio.gather(*tasks)
                tasks = []
            else: 
                pass
    
    #Connects to the twitch chat.
    def connect(self):
        self.bot_logger.info('Connnecting to chat(s)')
        self.irc = ssl.wrap_socket(socket.socket())
        self.irc.connect((self.irc_server, self.irc_port))
        self.send_command(f'CAP REQ :twitch.tv/membership')
        self.send_command(f'PASS {self.oauth_token}')
        self.send_command(f'NICK {self.username}')
        self.users=self.get_all_user()
        self.viewers=self.get_channel_viewers()
        for channel in self.channels:
            self.send_command(f'JOIN #{channel}')
            self.send_privmsg(channel, 'Hello, I am a bot. My creator has set me loose upon the world for testing purposes. You may access my commands with "$querycommands"')
        self.bot_logger.info(f'Joined chats for {self.channels}')
        asyncio.run(self.loop_for_messages())

    #Sends a command to the chat and prints it to the console.
    def send_command(self, command):
        if 'PASS' not in command:
            print(f'<{command}')
        self.irc.send((command + '\r\n').encode())

    #Sends a PRIVMSG to the chat.
    def send_privmsg(self, channel, text):
        self.send_command(f'PRIVMSG #{channel} :{text}')
        if channel != 'nivecgos':
                sleep(3)

    #Sets the Neo4j Driver.
    def init_driver(self):
        self.bot_logger.info('Innitializing QueryDriver')
        try:
            self.QueryDriver = BotQueries()
            self.bot_logger.info('QueryDriver initialized.')
        except Exception as e:
            self.bot_logger.critical('Failed tto initialize Query Driver.')
            self.bot_logger.error(e)
    
    #Sets up the streamer's template commands if they do not have a .JSON.
    def init_state(self):
        self.read_state()

    #Gets the list of all known viewers from the database.
    def get_channel_viewers(self):
        self.channel_viewers = self.QueryDriver.Run_get_viewers(self.channels[0])
        print(self.channel_viewers)

    #Hard coded commands that are NOT Query Commands

    #The help command. Heavily bloated.
    def command_help(self, message):
        self.command_logger.info(f'Command received from: {message.user}. Command: {message.text_command}')
        #The help dictionnary, contains help for all custom commands.
        command_help = {
            'optout': 'Tells me not to remember you. This will remove your ability to use database commands. You will need to do this once per stream (pending persistent list)',
            'querycommands': 'Enter this command to get a list of all commands. This command does not increase Query Count.',
            'query_add_streamer': 'This command adds a node with your twitch username, and sets your Created on date as today, and your Query Count to 1. If you already have a node, this command does nothing.',
            'query_set_friend': f'This command tells me thatt you are friends with another user. Its syntax is {self.streamer.command_prefix}query_set_friend <friend username>. If your friend does not have a node, it will fail. Unless the command fails, it increases your Query Count by 1 if it succeeds.',
            'query_get_friends': 'This command pulls a list of all your current friends. It will increase your Query Count by 1.',
            'query_get_stats': f'This command gets your Created on date your current Query Count, and your current {self.streamer.get_points_name()}. It will increase your Query Count by 1 before showing. It has an optionaal argument that allows you to choose which user you  would like to see stats for.',
            'query_get_genres': 'This command gets all video game genres I currently know about. It increaases your Query Count by 1.',
            'query_like_genre': f'This command tells me that you like a genre. The syntax is {self.streamer.command_prefix}query_like_genre <Genre Name>. You must capitalize the first letter of the genre, or the command will fail. This command will increase your Query Count by 1.',
            'query_get_liked_genres': "This command pulls a list of all Genres that I know you like. Optionally, you can specify a viewer, if I know who they are, who's liked genres you wish to see. This command will increase your Query Countt by 1.",
            'query_get_viewers': 'This command can only be run by the streamer. It pulls a list  of all registered viewers.',
            'query_suggest_genre': 'This command can only be run by the streamer. It suggests a genre that the streamer should play based on the amount of of their viewers that like said genre.',
            'query_countleader': 'This command pulls the current query leader for the channel.',
            'add_command': f'This command can only be used by the streamer. It adds a new template command. The syntax is {self.streamer.command_prefix}add_command <command name> <command_contents>. Please ask Nivecgos for help if you would like parameters in your command.',
            'edit_command': f'This command can only be used by the streamer. It changes a template command, or adds one if no such command exists. The syntax is {self.streamer.command_prefix}edit_command <command name> <command_contents>. Please ask Nivecgos for help if you would like parameters in your command.',
            'delete_command': f'This command can only be used by the streamer. It deletes a template command. The syntax is {self.streamer.command_prefix}delete_command <command name>. It can only delete template commands.',
            'new_prefix': f'This command can only be used by the streamer. It changes the command prefix. The default command prefix  is "$". The syntax is {self.streamer.command_prefix}new_prefix <new prefix>.  The prefix must be a single character.  There is no character restriction. This  setting is not saved in the event I break or lose connection for any reason.',
            'gamble': f"This command cannot be used by the streamer. Gambles the number of points given by the argument.  Max number of points won is 2 times tthe amount put in. Syntax: {self.streamer.command_prefix}gamble <point number>",
            '8ball': f"This command takes a question, and responds with a prediction, just like a magic 8 ball! Syntax: {self.streamer.get_command_prefix()}8ball <question>",
            'joke': f'This command tells me to send a random joke in the chat. Syntax: {self.streamer.get_command_prefix()}joke',
            'addjoke': f'This command can only be used by the streamer. It adds a joke to the list of jokes. Syntax: {self.streamer.get_command_prefix()}addjoke <joke>',
            'addpoints': f'This command can only be used by the streamer.  It adds a given amount of {self.streamer.get_points_name()} to a viewer. Syntax: {self.streamer.get_command_prefix()}addpoints <viewer> <{self.streamer.get_points_name()} amount>',
            'removepoints': f'This command can only be used by the streamer. it removes points from a viewer. Syntax: {self.streamer.get_command_prefix()}removepoints <viewer> <{self.streamer.get_points_name()} amount>',
            'donate': f'This command takes {self.streamer.get_points_name()} from one viewer, and gives them to another. It cannot be used to give more {self.streamer.get_points_name()} than you have. All {self.streamer.get_points_name()} given with this command should be considered gone for good. Syntax: {self.streamer.get_command_prefix()}donate <viewer> <{self.streamer.get_points_name()} amount>'
        }
        #If the user does not ask for a command, sends a  general help message.
        if message.text_args == []:
            self.send_privmsg(message.channel, f'Hello, {message.user}. I am a bot developed by Nivecgos that is currently in testing. You may type {self.streamer.command_prefix}querycommands for a list of custom made queries. You may type {self.streamer.command_prefix}help <command name> if you need help with a query command.')
            self.command_logger.info('Help response sent.')
            self.command_logger.debug('No argument given')

        #If the correct amount of arguments is given, send the help for that command.
        elif len(message.text_args) == 1:
            command_to_help = message.text_args[0]

            #If the command is not in help, tell the user.
            if command_to_help not in command_help:
                self.send_privmsg(message.channel, f'This command does not exist. If this command is a template command, please be aware that I do not currently provide help for template commands.')
                self.command_logger.critical(f'{command_to_help} not in help dictionary. Response sent.')

            #if the command is in help, send the help message.
            elif command_to_help in command_help:

                #If command can only be used by the streamer, do not send command help.
                if command_to_help.startswith('This command can only be used by the streamer.') and message.user != message.channel:
                    self.send_privmsg(message.channel, f'Sorry, {message.user}, but you cannot use this command, so telling you how to use it does not make sense. If you would like to see how this command works, please ask Nivvecgos to run me in your channel, or consult the documentation.')
                    return
                self.send_privmsg(message.channel, command_help[command_to_help])
                self.command_logger.info(f'Sent command help for {command_to_help}')

        #If there are too many arguments, tell the user.
        elif len(message.text_args) > 1:
            self.send_privmsg(message.channel, "I can only explain one command at a time. Please try again with just one command.")
            self.command_logger.error(f'Length of text_args is greater than one. Response sent.')

    #Sets a new command prefix for the streamer.
    def set_command_prefix(self, message):
        self.command_logger.info(f'Command received from: {message.user}. Command: {message.text_command}')

        #If user is not the streamer, do not set the new prefix.
        if message.user != self.streamer.username:
            self.send_privmsg(message.channel, f"I'm sorry, {message.user}, but you must be {self.streamer.get_username()} to use this command.")
            self.command_logger.warning(f'{message.user} tried to change command prefix.')
            return
        
        #If the number of arguments is incorrect, do not set the new prefix.
        elif message.text_args == [] or len(message.text_args) > 1:
            self.send_privmsg(message.channel, "This command requires one single-character argument")
            self.command_logger.warning(f'text_args length is greater than 1. args: {message.text_args}')

        ##If above are false, set the new prefix.
        else:
            self.streamer.set_command_prefix(message.text_args[0])
            self.send_privmsg(message.channel, f'I have set your new command prefix to "{self.streamer.command_prefix}"')
            self.command_logger.info(f'Command prefix changed to {self.streamer.get_command_prefix()}.')
            

    #Adds a new template command to the streamer.JSON
    def add_command(self, message, force=False):
        self.command_logger.info(f'Command received from: {message.user}. Command: {message.text_command}')

        #If user is not the streamer, do nnot add the command.
        if message.user != self.streamer.username:
            self.send_privmsg(message.channel, f"I'm sorry, {message.user}, but you must be {message.channel} to use this command.")
            self.command_logger.warning(f'{message.user} tried to add a command.')
            return

        #If there are not enough arguments, the command cannot be set.
        if len(message.text_args) < 2:
            self.send_privmsg(message.channel, f'This command requires 2 arguments: The command Name, and the command Template')
            self.command_logger.error(f'Text_args length less than 2. Text_args: {message.text_args}')
            return


        #If this command is called to replace or edit a custom command, tell the user.
        if message.text_args[1] in self.custom_commands:
            self.send_privmsg(message.channel, "You cannot add a command that shares a name with a non-template command.")
            self.command_logger.warning(f'{message.text_args[1]} is already a custom command.')
        command_name = remove_prefix(message.text_args[0], self.streamer.command_prefix)
        self.command_logger.debug(f'Command Name set: {command_name}')
        template = ' '.join(message.text_args[1:])
        self.command_logger.debug(f'Template set: {template}')

        #If command is called to edit or replace a template command, tell the user to use the correct command.
        if command_name in self.state['template_commands'] and force is not True:
            self.send_privmsg(message.channel, f"This command already exists. Use {self.streamer.command_prefix}edit_command if you would like to change it.")
            self.command_logger.warning(f'{command_name} is already a template command.')
        self.streamer.state['template_commands'][command_name] = template
        self.write_state()
        self.command_logger.info(f'{command_name} added to template commands.')
        self.send_privmsg(message.channel, f'{command_name} added.')

    #Edits an existing template command.
    def edit_command(self, message):
        self.command_logger.info(f'Command received from: {message.user}. Command: {message.text_command}')
        
        #If the user is not the streamer, do not change the command.
        if message.user != message.channel:
            self.send_privmsg(message.channel, f"I'm sorry, {message.user}, but you must be  {message.channel} to use this command.")
            self.command_logger.warning(f'{message.user} tried to edit a command.')
            return
        self.add_command(message, force=True)

    #Deletes a template command from the streamer.JSON.
    def delete_command(self, message):
        self.command_logger.info(f'Command received from: {message.user}. Command: {message.text_command}')

        #If the user is not the streamer, do not delete the command.
        if message.user != message.channel:
            self.send_privmsg(message.channel, f"I'm sorry, {message.user}, but you must be  {message.channel} to use this command.")
            self.command_logger.warning(f'{message.user} tried to delete a command.')
            return
        
        #If there are no arguments, tell the user.
        if len(message.text_args) < 1:
            self.send_privmsg(message.channel, "This command requires one argument")
            self.command_logger.error(f'Text_args length is 0.')
            return
        command_names = [remove_prefix(command, self.streamer.command_prefix) for command in message.text_args]
        self.command_logger.debug(f'Commands to remove: {command_names}')

        #If any arguments given are not a valid template command, tell the user.
        if not all([command_name in self.streamer.state['template_commands'] for command_name in command_names]):
            self.send_privmsg('One of the commands does not exist.')
            self.command_logger.warning('One of the  ')
            return

        #Delete the commands if all arguments given are template commands.
        for command_name in command_names:
            del self.streamer.state['template_commands'][command_name]
            self.command_logger.info(f'Deleted {command_name}.')
        self.write_state()

        self.send_privmsg(message.channel, f'Commands deleted: {command_names}')

   
    #NEO4J QUERY COMMANDS. THESE COMMANDS REQUIRE A NEO$J DATABASE TO BE CONNECTED.

    #Removes a user from the database.
    def remove_user(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            query = self.QueryDriver.Run_remove_user(message.user)
            #If the query fails, raise  an error.
            if query == False:
                raise ValueError('Run function returned false.')
            self.send_privmsg(message.channel, f'Okay, {message.user}, I will not remember you. I will still use your username for template commands, as those do not require memory.')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Lists all query commands in the chat
    def list_query_commands(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        commands_string = []
        try:
            for command in self.custom_commands.keys():
                commands_string.append(command)
            self.command_logger.debug(commands_string)
            self.send_privmsg(message.channel, "The custom commands are: " + f', {self.streamer.command_prefix}'.join(commands_string))
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #lists all users stored in the database into the chat
    def get_all_user(self):
        self.command_logger.info(f'Getting users...')
        try:
            users = self.QueryDriver.Run_all_user()
            #If the query fails, raise an error.
            if users == False:
                raise ValueError('Run function returned false.')
            self.command_logger.info('Users retrieved.')
            return users
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info('Failed to retrieve users.')

    #adds the user who sent the command to the database. Should be used by the streamer during intial bot set up.
    def set_add_user(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        #If the user is not the streamer, do not run the query.
        if  message.channel != message.user:
            self.send_privmsg(message.channel, "Sorry, but you cannot run this command unless you are the streamer.")
            self.command_logger.warning(f'{message.user} tried to create a node.')
        try:
            self.send_privmsg(message.channel, f"Okay, {message.user}, I will remember you.")
            query = self.QueryDriver.Run_add_user(message.user)
            #If the query fails, raise an error.
            if query == False:
                raise ValueError('Run Function returned false.')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #adds a friendship between the user who sent the argument, and the specified user.
    def set_friendship(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        #If no friend is specified, tell the user.
        if message.text_args == []:
            self.send_privmsg(message.channel,"Please include the username of the person you wish to be friends with.")
            self.command_logger.warning('Text_args list is empty.')
            return
        else:
            try:
                #If the user has a valid Viewer object, create the friendship.
                if message.user in self.viewer_features_dictionary.keys:
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
                    new_friend = message.text_args[0]
                    self.command_logger.debug(f'New Friend: {new_friend}')
                    query = viewer.update_friends_list(new_friend)
                    #If the query fails, raise an error.
                    if query == False:
                        raise ValueError('Viewer Function returned false.')
                #If the user is the streamer, create the friendship.
                elif message.user == message.channel:
                    streamer = self.streamer
                    new_friend = message.text_args[0]
                    self.command_logger.debug(f'New Friend: {new_friend}')
                    query = streamer.update_friends_list(self.streamer.username, new_friend)
                    #If the query fails, raise an error.
                    if query == False:
                        raise ValueError('Streamer Function returned false.')
                self.send_privmsg(message.channel, f'Your friendship with {new_friend} will be remembered.')
            except Exception as e:
                self.command_logger.error(e)
                self.command_logger.info(f'{message.text_command} from {message.user} failed.')
                self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #gets all of the nodes that a user has an :IS_FRIENDS relationship for.
    def get_friends(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user has a valid viewer oject, get their friends list.
            if message.user in self.viewer_features_dictionary.keys():
                viewer = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
                friends = viewer.get_friends_list()
                #If the method fails, raise an error.
                if friends == False:
                    raise ValueError('Viewer function returned false')
                friends_string = ', '.join(friends)
                self.command_logger.debug(f'Friends string: {friends_string}')
            #If the user is the streamer, use the method in the Streamer class instead.
            elif message.user  == message.channel:
                streamer = self.streamer
                friends = streamer.get_friends_list()
                #If the method fails, raise an error.
                if friends == False:
                    raise ValueError('Streamer Function returned false.')
                friends_string = ', '.join(friends)
            self.send_privmsg(message.channel, f'Your friends are: {friends_string}')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Gets the stats for the sending user if no argument user is specified
    def get_stats(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user specifies a target, get the target's stats.
            if message.text_args:
                #if the target has a valid Viewer Object, get their stats.
                if message.text_args[0] in self.viewer_features_dictionary.keys():
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.text_args[0]]]
                    stats = viewer.get_stats()
                    #If the method fails, raise an error.
                    if stats == False:
                        raise ValueError('Viewer function returned false.')
                    self.send_privmsg(message.channel, f"{viewer.username}'s stats are:")
                    self.command_logger.info(f"{viewer.username}'s stats are {stats}")
                    #Send a message for each stat with the stat name and value.
                    for stat, value in stats.items():
                        self.send_privmsg(message.channel, f'{stat}: {value}')
                #If the target does not have a Viewer Object, raise an error.
                else:
                    raise ValueError('Viewer object does not exist. Please check syntax or spelling.')
            
            #If no target is specified, get the user's stats.
            else:
                #If the user has a Viewer object, get their stats.
                if message.user in self.viewer_features_dictionary.keys():
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
                    stats = viewer.get_stats()
                    #If the method fails, raise an error.
                    if stats == False:
                        raise ValueError('Viewer function returned false.')
                    self.command_logger.info(f"{viewer.username}'s stats are {stats}")
                    self.send_privmsg(message.channel, f"{viewer.username}, your stats are:")
                    for stat, value in stats.items():
                        self.send_privmsg(message.channel, f'{stat}: {value}')
                #If the user is the streamer, use the Streamer class method instead.
                elif message.user == message.channel:
                    streamer = self.streamer
                    stats = streamer.get_stats()
                    #If the method fails, raise an error.
                    if stats == False:
                        raise ValueError('Streamer function returned false')
                    self.command_logger.info(f"{streamer.username}'s stats are {stats}")
                    self.send_privmsg(message.channel, f"{streamer.username}, your stats are:")
                    #Send a message for each stat with the stat name and value.
                    for stat, value in stats.items():
                        self.send_privmsg(message.channel, f'{stat}: {value}')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Gets all genres and sends them to the chat.
    def get_genres(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        self.send_privmsg(message.channel, "Okay, I am getting the current Genres.")
        try:
            genres = self.QueryDriver.Run_get_genres()
            #If the query fails, raise an error.
            if genres == False:
                raise ValueError('Run function returned false.')
            genre_string = ', '.join(genres)
            self.command_logger.debug(genre_string)
            self.send_privmsg(message.channel, genre_string)
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Sets a :LIKES_GENRE relationship between the user running the command and the specified genre
    def set_likes_genre(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        #If there is not genre specified, tell the user.
        if message.text_args == []:
            self.send_privmsg(message.channel, f"You must specify a genre from the list of genres. You can see a list of genres I know by using the {self.command_prefix}query_get_genres command.")
            self.command_logger.warning('Text args list lenngth is 0.')
        #If the genre is specifed, set the :LIKES relationship to that genre.
        else:
            try:
                #If the user has a Viewer object, set the :LIKES_GENRE relationship to that genre.
                if message.user in self.viewer_features_dictionary.keys():
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
                    genre = message.text_args[0]
                    query = viewer.update_liked_genres(genre)
                    #If the method fails, raise an error.
                    if query == False:
                        raise ValueError('Viewer function returned false.')
                #If the user is the streamer, use the Streamer class method.
                elif message.user == message.channel:
                    streamer = self.streamer
                    genre = message.text_args[0]
                    query = streamer.update_liked_genres(genre)
                    #If the method fails, raise an error.
                    if query == False:
                        raise ValueError('Streamer function returned false.')
                self.send_privmsg(message.channel, f'I will remember that you like {genre}, {message.user}.')
            except Exception as e:
                self.command_logger.error(e)
                self.command_logger.info(f'{message.text_command} from {message.user} failed.')
                self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Gets all genres the specified user has a :LIKES_GENRE relationship to.
    def get_liked_genres(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If no target is specified, get the user's liked genres.
            if message.text_args == []:
                #If the target has a Viewer object, get the user's liked genres.
                if message.user in self.viewer_features_dictionary.keys():
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
                    liked_genres = viewer.get_liked_genres()
                    #If the method fails, raise an error.
                    if liked_genres ==  False:
                        raise ValueError('Viewer function returned false.')
                #If the user is the streamer, use the Streamer class method.
                elif message.user == message.channel:
                    streamer = self.streamer
                    liked_genres = streamer.get_liked_genres()
                    #If the method fails, raise an error.
                    if liked_genres ==  False:
                        raise ValueError('Viewer function returned false.')
                genre_string = ', '.join(liked_genres)
                self.command_logger.debug(genre_string)
                self.send_privmsg(message.channel, f"You like the following genres: {genre_string}")
            #If a target is specified, get their likd genres.
            elif len(message.text_args) >= 1:
                #If the target has a Viewer object, get their liked genres.
                if message.text_args[0] in self.viewer_features_dictionary.keys():
                    viewer = self.viewer_object_list[self.viewer_features_dictionary[message.text_args[0]]]
                    liked_genres = viewer.get_liked_genres()
                    #If the method fails, raise an error.
                    if liked_genres == False:
                        raise ValueError('Run function returned false.')
                #If the target is the streamer, use the Streamer class method.
                elif message.text_args[1] == message.channel:
                    streamer = self.streamer
                    liked_genres = streamer.get_liked_genres()
                    #If the method fails, raise an error.
                    if liked_genres == False:
                        raise ValueError('Run function returned false.')
                genre_string = ', '.join(liked_genres)
                self.command_logger.debug(genre_string)
                self.send_privmsg(message.channel, f"{message.text_args[0]} likes the following genres: {genre_string}")
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Creates a Person node for the specified user with a :VIEWS relationship to the specified channel.
    def create_user_views(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        channel = message.channel
        username = message.user
        try:
            query = self.QueryDriver.Run_create_user_views(username, channel)
            #If the query fails, raise an error.
            if query == False:
                raise ValueError('Run function returned false.')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Creates a :VIEWS  relationship between two person nodes.
    def create_views(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        channel = message.channel
        username = message.user
        try:
            query = self.QueryDriver.Run_create_views(username, channel)
            #If the query fails, raise an error.
            if query == False:
                raise ValueError('Run  function returned false.')
            #If the message is not a JOIN message, acknowledge the user.
            if message.irc_command != 'JOIN':
                self.send_privmsg(message.channel, f'Okay,  {message.user}, I will remember that you watch {message.channel}.')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Runs a read only query that returns a llist of all viewers for the specified user if the user is the streamer.
    def get_viewers(self, message=None):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user is not the streamer, do not get the viewer list.
            if message.channel != message.user:
                self.send_privmsg(message.channel, f'Sorry, {message.user}, but you must be the streamer to run this command.')
                self.command_logger.warning(f'{message.user} tried to get the viewer list.')
                return
            #If the command was not sent, but the function is called, get the viewers for the channel.
            elif message == None:
                viewers = self.QueryDriver.Run_get_viewers(self.channels[0])
                return viewers
            #If the above are false, get the viewer list.
            else:
                viewers = ', '.join(self.QueryDriver.Run_get_viewers(message.channel))
                #If the query fails, return false.
                if viewers == False:
                    raise ValueError('Run function returned false.')
                self.command_logger.debug(f'{viewers}')
                self.send_privmsg(message.channel, viewers)
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    
    #Runs a read only query that retrieves the genre that most of the streamer's viewers have a :LIKES_GENRE relationship to.
    def suggest_genres(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        #If the user is not the streamer, do not get the suggested genre.
        if message.channel != message.user:
            self.send_privmsg(message.channel, f'Sorry, {message.user},  but only the streamer can run with this command.')
            self.command_logger.warning(f'{message.user} tried to get genre suggestions.')
            return
        channel = message.channel
        try:
            genres = self.QueryDriver.Run_get_viewer_liked_genres(channel)
            #If the query fails, raise an error.
            if genres ==  False:
                raise ValueError('Run function returned false.')
            self.command_logger.debug(f'{genres}')
            best_genre = []
            #Find the best genre as returned from the query and post it
            for genre, amount in genres.items():
                #If there is not a current best genre, set the best genre to the current genre.
                if best_genre == []:
                    best_genre = [genre, amount]
                #If the above is false, do not set best genre yet.
                else:
                    #If the current genre is better than the current best genre, set the best genre to the current genre.
                    if genres[genre] > best_genre[1]:
                        best_genre = [genre, amount]
                    #If the current genre  is the best genre, pass.
                    elif genres[genre] == best_genre:
                        pass
            self.command_logger.debug(f'{best_genre}')
            self.send_privmsg(message.channel, f'Based on the genres your viewers enjoy, I think you should play games from the {best_genre[0]} genre.')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Gets the query_count leader for the channel.
    def get_query_count_leader(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        channel = message.channel
        try:
            count_leader = self.QueryDriver.Run_get_query_count_leader(channel)
            #If the  query fails, raise an error.
            if count_leader == False:
                raise ValueError('Run function returned false.')
            #Get the count leader values that were returnend from the query and post them in the chat.
            for key, value in count_leader.items():
                count_name=key
                count_number=value
            self.command_logger.debug(f'{count_leader}')
            self.send_privmsg(message.channel, f"The Query Leader is {count_name} with {count_number} queries!")
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Adds points to a registered viewer.
    def add_points(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user is not the streamer, do not add points.
            if message.user != self.streamer.get_username():
                self.send_privmsg(f'Sorry, {message.user}, only the streamer can run this command. Please try the "donate" command instead.')
                self.command_logger.warning(f'{message.user} tried to add points.')
                return
            viewer = self.viewer_object_list[self.viewer_features_dictionary[message.text_args[0]]]
            viewer.update_stat('points', 'add', int(message.text_args[1]))
            self.send_privmsg(f'Gave {message.text_args[1]} {self.streamer.get_points_name()} to {viewer.username}.')
            self.command_logger.info(f'{message.text_args[1]} points given to {viewer.username}')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')
    
    #Removes points from a user
    def remove_points(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user is not the streamer, do not remove points.
            if message.user != self.streamer.get_username():
                self.send_privmsg(message.channel, f'Sorry, {message.user}, only the streamer can run this command.')
                self.command_logger.warning(f'{message.user} tried to remove someones points.')
                return
            viewer =  self.viewer_object_list[self.viewer_features_dictionary[message.text_args[0]]]
            viewer.update_stat('points', 'subtract', int(message.text_args[1]))
            self.send_privmsg(f'Removed {message.text_args[1]} {self.streamer.get_points_name()} from {viewer.username}.')
            self.command_logger.info(f'{message.text_args[1]} points taken from {viewer.username}')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #Donates points from the user to the target.
    def donate_points(self, message):
        self.command_logger.info(f'Query Command received from: {message.user}. Command: {message.text_command}')
        try:
            #If the user is the streamer, do not donate points.
            if message.user == self.streamer.get_username:
                self.send_privmsg(message.channel, f'Sorry, {message.user}, but you cannot donatte points in your own chat. Please try "addpoints" instead.')
                self.command_logger.warning('The streamer tried to donate points in their own chat.')
                return
            viewer1 = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
            viewer2 = self.viewer_object_list[self.viewer_features_dictionary[message.text_args[0]]]
            points = message.text_args[1]
            #If the user does not have enough points, do not donate the points.
            if viewer1.get_stats()['points'] < points:
                self.send_privmsg(message.channel, f'Sorry, {message.user}, but you do not have enough {self.streamer.get_points_name()}, and I am not a liscensed {self.streamer.get_points_name()} lender.')
                self.command_logger.warning(f'{message.user} tried to give more points than they have.')
                return
            viewer1.update_stat('points', 'subtract', int(points))
            viewer2.update_stat('points', 'add', int(points))
            self.send_privmsg(message.channel, f'{viewer1.get_username()} donate {points} {self.streamer.get_points_name()} to {viewer2.get_username()}. How kind!')
        except Exception as e:
            self.command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    



    #Game commands
    #Gambles an amount of points.
    def gamble(self, message):
        try:
            #If the user is the streamer, the streamer loses.
            if message.user ==  self.streamer.get_username():
                self.send_privmsg(message.channel, f'{self.streamer.username} has rolled 0. They lost all their {self.streamer.points_name}. Laugh at them.')
                self.command_logger.info('Command user was the sttreamer. Bullying.')
                return
            player = self.viewer_object_list[self.viewer_features_dictionary[message.user]]
            points = message.text_args[0]
            gambling = game.Gamble(player, points)
            winnings_number = gambling.gamble()
            #If the method fails, raise an error.
            if winnings_number == False:
                raise ValueError('Run function returned false.')
            player.update_stat('points', 'add', winnings_number[0])
            self.send_privmsg(message.channel, f"{player.name} rolled {winnings_number[1]}. They won {winnings_number[0]} {self.streamer.points_name}. {player.name} now has {player.get_stats()['points']} {self.streamer.points_name}.") 
            self.command_logger('Game command run successfully.')
        except Exception as e:
            command_logger.error(e)
            self.command_logger.info(f'{message.text_command} from {message.user} failed.')
            self.send_privmsg(message.channel, f'{message.text_command} failed. Please check syntax and try again.')

    #8ball game. Sends a random response from the list of responses in the 8ball.txt file.
    def eight_ball(self, message):
        file_lines = []
        with open('Chatbot\Other\Random_Texts\8ball.txt', 'r') as file:
            for line in file:
                file_lines.append(line)
        number = random.randint(0,len(file_lines))
        answer = file_lines[number]
        self.send_privmsg(message.channel, f'@{message.user} {answer}')

    #Reads a random joke from the jokes.txt file
    def read_random_joke(self, message):
        file_lines = []
        with open('Chatbot\Other\Random_Texts\jokes.txt', 'r') as file:
            for line in file:
                file_lines.append(line)
        number = random.randint(0,len(file_lines))
        answer = file_lines[number]
        self.send_privmsg(message.channel, f"""{answer}""")

    #Adds a joke to the jokes.txt file
    def add_joke(self, message):
        #If the user is not the streamer, do not add the joke.
        if message.user != self.streamer.get_username():
            self.send_privmsg(f'Sorry, {message.user}, only the streamer can use this command.')
            return
        with open('Chatbot\Other\Random_Texts\jokes.txt', 'a', encoding='UTF-8') as file:
            file.write(' '.join(message.text_args) + '\n')
        self.send_privmsg(message.channel, f'Added joke: {message.text_args}')


    

#function to start the bot.
def main():
    bot = Bot()
    bot.init_state()
    bot.init_driver()
    bot.connect()
    
#Start the bot.
if __name__ == '__main__':
    main()

