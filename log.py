import sys
import logging
import datetime

date_string =  str(datetime.date.today()).replace('-','_')
#define loggers
bot_function_logger = logging.getLogger('botfunctions')
command_logger =  logging.getLogger('commands')
query_logger = logging.getLogger('queries')
viewer_logger = logging.getLogger('viewer')
streamer_logger = logging.getLogger('streamer')
game_logger = logging.getLogger('games')

#define file handlers
bf_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')
c_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')
q_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')
v_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')
s_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')
g_file_handler = logging.FileHandler(f'Chatbot\logs\{date_string}_Log.log')

#define stream handlers
bf_stream_handler = logging.StreamHandler(sys.stdout)
c_stream_handler = logging.StreamHandler(sys.stdout)
q_stream_handler = logging.StreamHandler(sys.stdout)
v_stream_handler = logging.StreamHandler(sys.stdout)
s_stream_handler = logging.StreamHandler(sys.stdout)
g_stream_handler = logging.StreamHandler(sys.stdout)

#set formatters
formatter = logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(lineno)d\t%(message)s')

#set formatter to handlers
bf_file_handler.setFormatter(formatter)
bf_stream_handler.setFormatter(formatter)
c_file_handler.setFormatter(formatter)
c_stream_handler.setFormatter(formatter)
q_file_handler.setFormatter(formatter)
q_stream_handler.setFormatter(formatter)
v_file_handler.setFormatter(formatter)
v_stream_handler.setFormatter(formatter)
s_file_handler.setFormatter(formatter)
s_stream_handler.setFormatter(formatter)
g_file_handler.setFormatter(formatter)
g_stream_handler.setFormatter(formatter)

#set handlers to loggers
bot_function_logger.addHandler(bf_file_handler)
command_logger.addHandler(c_file_handler)
command_logger.addHandler(c_stream_handler)
query_logger.addHandler(q_file_handler)
viewer_logger.addHandler(v_file_handler)
streamer_logger.addHandler(v_file_handler)
game_logger.addHandler(g_file_handler)

#set logging levels
bot_function_logger.setLevel(10)
command_logger.setLevel(10)
query_logger.setLevel(10)
viewer_logger.setLevel(10)
streamer_logger.setLevel(10)
game_logger.setLevel(10)