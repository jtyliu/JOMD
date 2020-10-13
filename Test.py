import os
import dotenv
import json
import requests
import re
import time
import html
import asyncio
from bs4 import BeautifulSoup
import math
from db.db import JOMDdb
import random


db = JOMDdb()

a = ['Data Structures','Dynamic Programming','Graph Theory','String Algorithms',['Advanced Math','Geometry','Intermediate Math','Simple Math'],'Ad Hoc','Greedy Algorithms']

for i in a:
    if type(i)==type(''):
        tmp = db.get_problem_type(i)
        print(len(tmp),i)
    else:
        tmp = db.get_problem_types(i)
        print(len(tmp),i)