## Overview

A chatbot for Twitch written in Python, created to gain experience utilizing Neo4j's Python Driver.

## Features

+ Templated commands that can be set both in the twitch chat and off stream, and can have almost as many arguments as the twitch chat character limit.
+ The streamer can customize which prefix they prefer for their stream.
+ Help for all non-templated commands.
+ 8ball and joke reading.
+ A gambling minigame that uses points generated by the bot that the streamer can give out or take away, or donated by other users.
+ Logging functionality in case something goes wrong.
+ Integration with a Neo4j database for a set of query commands.


## Requiremennts

Requires Python 3, the Python 3 Neo4j Driver, and access to a Neo4j database.

### Setup

1. Create a file named 'config.py' in the Chatbot folder.
2. In the file, add the following:
    + OATH_TOKEN = (This should be the oath token for the account the bot will be using. This can be your account, but if so any messages you send will interfere with the bot's rate limit.)
    + USERNAME = (This should be thte usernname of the account the bot will be using.)
    + CHANNEL = (This should be the Twitch channel you want the bot to join. Please do not make it join a channel that is not your own without the channel owner's permission.)
    + DB = (This should be the url/address to the database. for local databases, use the bolt protocol.)
    + DB_USER = (This should be the username for the Neo4j database.)
    + DB_PASS = (This should be the password for the username for the Neo4j databes.)
3. When the bot joins the chat, have the streamer use the query_add_streamer command. The prefix will default to '!'
4. Optional: If something fails to generate after these steps, restart the bot. This will remake the streamer and viewer objects.
