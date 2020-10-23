import requests
import time
import asyncio
from bs4 import BeautifulSoup
from utils.submission import Submission
from utils.problem import Problem
import functools
import aiohttp


class ApiError(Exception):
    pass

def rate_limit(func):
    ratelimit = 87
    queue = []
    @functools.wraps(func)
    async def wrapper_rate_limit(*args, **kwargs):
        # Is this enough? 
        # Any race condition?
        now = time.time()
        while len(queue) > 0 and now - queue[0] > 60:
            queue.pop(0)

        if len(queue) == ratelimit:
            waittime = 60 - now + queue[0]
            queue.pop(0)
            await asyncio.sleep(waittime)
            now = time.time()
        queue.append(now)
        return await func(*args, **kwargs)
    return wrapper_rate_limit

_session = None

@rate_limit
async def _query_api(url, resp_obj):
    global _session
    if _session is None:
        _session = aiohttp.ClientSession()
    async with _session.get(url) as resp:
        if resp_obj == 'text':
            resp = await resp.text()
        if resp_obj == 'json':
            resp = await resp.json()
        # if 'error' in resp:  ApiError would interfere with some other stuff, might just change to error trapping
        #     raise ApiError
        return resp


class user_api:
    @staticmethod
    async def get_user(username):
        resp = await _query_api(f'https://dmoj.ca/api/v2/user/{username}', 'json')
        if 'error' in resp:
            return None
        return resp['data']['object']

    @staticmethod
    async def get_pfp(username):
        resp = await _query_api(f'https://dmoj.ca/user/{username}', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        pfp = soup.find('div', class_='user-gravatar').find('img')['src']
        return pfp

    @staticmethod
    async def get_placement(username):
        resp = await _query_api(f'https://dmoj.ca/user/{username}', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        rank_str = soup.find('div', class_='user-sidebar')\
                       .findChildren(recursive=False)[3].text
        rank = int(rank_str.split('#')[-1])
        return rank

class submission_api:
    @staticmethod
    async def get_submission_total(username):
        resp = await _query_api(f'https://dmoj.ca/api/v2/'
                                f'submissions?user={username}', 'json')
        if 'error' in resp:
            return None
        return resp['data']['total_objects']

    @staticmethod
    async def get_submissions_page(username, page):
        resp = await _query_api(f'https://dmoj.ca/api/v2/'
                                f'submissions?user={username}&page={page}', 'json')
        if 'error' in resp:
            return None
        return list(map(Submission.loads, resp['data']['objects']))

    @staticmethod
    async def get_submission(submission_id):
        resp = await _query_api(f'https://dmoj.ca/api/v2/'
                                f'submission/{submission_id}', 'json')
        if 'error' in resp:
            return None
        return Submission.loads(resp['data']['object'])

    @staticmethod
    async def get_latest_submission(username, num):
        def parse_submission(soup):
            submission_id = soup['id']
            result = soup.find(class_='sub-result')['class'][-1]
            try:
                score = soup.find(class_='sub-result')\
                            .find(class_='score').text.split('/')
                score_num, score_denom = map(int, score)
                points = score_num/score_denom,
            except ValueError:
                score_num, score_denom = 0, 0
                points = 0
            lang = soup.find(class_='language').text
            problem = soup.find(class_='name')\
                            .find('a')['href'].split('/')[-1]
            name = soup.find(class_='name').find('a').text
            date = soup.find(class_='time-with-rel')['title']
            try:
                time = float(soup.find('div', class_='time')['title'][:-1])
            except ValueError:
                time = None
            except KeyError:
                time = None
            memory = soup.find('div', class_='memory').text
            res = {
                "id": submission_id,
                "problem": problem,
                "user": username,
                "date": date,
                "language": lang,
                "time": time,
                "memory": memory,
                "points": points,
                "result": result,
                "score_num": score_num,
                "score_denom": score_denom,
                "problem_name": name,
            }
            return Submission.loads(res)
        resp = await _query_api(f'https://dmoj.ca/'
                                f'submissions/user/{username}/', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        matches = list(map(parse_submission,
                           soup.find_all('div', class_='submission-row')
                           ))
        return matches[:num]

class problem_api:
    @staticmethod
    async def get_problem(problem_code):
        resp = await _query_api(f'https://dmoj.ca/'
                                f'api/v2/problem/{problem_code}', 'json')
        if 'error' in resp:
            return None
        return Problem.loads(resp['data']['object'])

    @staticmethod
    async def get_problems(page=1):
        resp = await _query_api(f'https://dmoj.ca/api/v2/'
                                f'problems?page={page}', 'json')
        if 'error' in resp:
            return None
        return list(map(Problem.loads, resp['data']['object']))

    @staticmethod
    async def get_problem_option(id):
        resp = await _query_api(f'https://dmoj.ca/problems/?show_types=1', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        options = soup.find('select', id=id).find_all('option')
        def get_options(options):
            options_avaliable = []
            for option in options:
                if option['value'].isdigit():
                    options_avaliable.append(option.text.strip())
        options = get_options(options)
        return options

async def close():
    await _session.close()
