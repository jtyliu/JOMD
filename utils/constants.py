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