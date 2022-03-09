import os
import datetime
import pytz

API_TOKEN = os.environ.get("JOMD_TOKEN", None)
# Has no use, URI located at db.py
DB_DIR = 'utils/db/JOMD.db'
SITE_URL = 'https://dmoj.ca/'
DEBUG = False
ADMIN_ROLES = ['Admin']
# Time zone
# why does it not work??? asdlsadkl
TZ = pytz.timezone("America/New_York")

SHORTHANDS = {
    "adhoc": ["Ad Hoc"],
    "math": ["Advanced Math", "Intermediate Math", "Simple Math"],
    "bf": ["Brute Force"],
    "ctf": ["Capture the Flag"],
    "ds": ["Data Structures"],
    "d&c": ["Divide and Conquer"],
    "dp": ["Dynamic Programming"],
    "geo": ["Geometry"],
    "gt": ["Graph Theory"],
    "greedy": ["Greedy Algorithms"],
    "regex": ["Regular Expressions"],
    "string": ["String Algorithms"],
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

# Credit to cheran-senthil/TLE for color hexes
GRAPH_RANK_COLOURS = {
    (0, 1000): "#CCCCCC",
    (1000, 1300): "#77FF77",
    (1300, 1600): "#AAAAFF",
    (1600, 1900): "#FF88FF",
    (1900, 2400): "#FFCC88",
    (2400, 3000): "#FF7777",
    (3000, 1e9): "#AA0000",
}

RANKS = [
    "Unrated",
    "Newbie",
    "Amateur",
    "Expert",
    "Candidate Master",
    "Master",
    "Grandmaster",
    "Target",
]

RATING_TO_RANKS = {
    (-1e9, 1000): "Newbie",
    (1000, 1300): "Amateur",
    (1300, 1600): "Expert",
    (1600, 1900): "Candidate Master",
    (1900, 2400): "Master",
    (2400, 3000): "Grandmaster",
    (3000, 1e9): "Target",
}
