import os
import datetime
import pytz

# Has no use, URI located at db.py
DB_DIR = 'utils/db/JOMD.db'
SITE_URL = 'https://dmoj.ca/'
DEBUG_DB = False
DEBUG_API = True
# Time zone
# why does it not work??? asdlsadkl
TZ = pytz.timezone('America/New_York')

SHORTHANDS = {
	'adhoc': ['Ad Hoc'],
	'math': ['Advanced Math', 'Intermediate Math', 'Simple Math'],
	'bf': ['Brute Force'],
	'ctf': ['Capture the Flag'],
	'ds': ['Data Structures'],
	'd&c': ['Divide and Conquer'],
	'dp': ['Dynamic Programming'],
	'geo': ['Geometry'],
	'gt': ['Graph Theory'],
    'greedy': ['Greedy Algorithms'],
	'regex': ['Regular Expressions'],
	'string': ['String Algorithms'],
}

POINT_VALUES = [1, 3, 5, 7, 10, 12, 15, 17, 20, 25, 30, 35, 40, 50]
RATING_TO_POINT = {
    800: 3,
    1000: 5,
    1200: 7,
    1600: 10,
    1800: 12,
    2000: 15,
    2200: 17,
    2400: 20,
    2600: 25,
    3000: 30,
}