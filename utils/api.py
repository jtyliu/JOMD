# from utils.submission import Submission
# from utils.problem import Problem
from bs4 import BeautifulSoup
from utils.constants import SITE_URL, API_TOKEN
import urllib.parse
import functools
import aiohttp
import asyncio
import time
import html
import math
import json
from datetime import datetime
from utils.db import session
from utils.db import (Problem, Contest,
                      Participation,
                      User, Submission,
                      Organization,
                      Language, Judge)
from operator import itemgetter
from contextlib import asynccontextmanager
import typing
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


__all__ = [
    'API',
    'ObjectNotFound',
    'ParseJudge',
    'ParseLanguage',
    'ParseOrganization',
    'ParseSubmission',
    'ParseUser',
    'ParseParticipation',
    'ParseContest',
    'ParseProblem',
]


# Credit to Danny Mor https://medium.com/analytics-vidhya/async-python-client-rate-limiter-911d7982526b
class RateLimiter:
    def __init__(self,
                 rate_limit: int,
                 concurrency_limit: int) -> None:
        if not rate_limit or rate_limit < 1:
            raise ValueError('rate limit must be non zero positive number')
        if not concurrency_limit or concurrency_limit < 1:
            raise ValueError('concurrent limit must be non zero positive number')

        self.rate_limit = rate_limit
        self.tokens_queue = asyncio.Queue(rate_limit)
        self.tokens_consumer_task = asyncio.create_task(self.consume_tokens())
        self.semaphore = asyncio.Semaphore(concurrency_limit)

    async def add_token(self) -> None:
        await self.tokens_queue.put(1)
        return None

    async def consume_tokens(self):
        try:
            consumption_rate = 1 / self.rate_limit
            last_consumption_time = 0

            while True:
                if self.tokens_queue.empty():
                    await asyncio.sleep(consumption_rate)
                    continue

                current_consumption_time = time.monotonic()
                total_tokens = self.tokens_queue.qsize()
                tokens_to_consume = self.get_tokens_amount_to_consume(
                    consumption_rate,
                    current_consumption_time,
                    last_consumption_time,
                    total_tokens
                )

                for i in range(0, tokens_to_consume):
                    self.tokens_queue.get_nowait()

                last_consumption_time = time.monotonic()

                await asyncio.sleep(consumption_rate)
        except asyncio.CancelledError:
            # you can ignore the error here and deal with closing this task later but this is not advised
            raise
        except Exception:
            # do something with the error and re-raise
            raise

    @staticmethod
    def get_tokens_amount_to_consume(consumption_rate, current_consumption_time, last_consumption_time, total_tokens):
        time_from_last_consumption = current_consumption_time - last_consumption_time
        calculated_tokens_to_consume = math.floor(time_from_last_consumption / consumption_rate)
        tokens_to_consume = min(total_tokens, calculated_tokens_to_consume)
        return tokens_to_consume

    @asynccontextmanager
    async def throttle(self):
        await self.semaphore.acquire()
        await self.add_token()
        try:
            yield
        finally:
            self.semaphore.release()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # log error here and safely close the class
            pass

        await self.close()

    async def close(self) -> None:
        if self.tokens_consumer_task and not self.tokens_consumer_task.cancelled():
            try:
                self.tokens_consumer_task.cancel()
                await self.tokens_consumer_task
            except asyncio.CancelledError:
                # we ignore this exception but it is good to log and signal the task was cancelled
                pass
            except Exception:
                # log here and deal with the exception
                raise


rate_limiter = None
_session = None


async def _query_api(url, resp_obj, *, object_hook=None):
    global _session, rate_limiter

    if object_hook is not None:
        json_loads = functools.partial(json.loads, object_hook=object_hook)
    else:
        json_loads = json.loads()

    if rate_limiter is None:
        # Allow at most 3 concurrent requests tokens are emptied at 1 per second
        rate_limiter = RateLimiter(rate_limit=1, concurrency_limit=3)

    async with rate_limiter.throttle():
        start = time.time()
        logger.info('Calling %s', url)
        if _session is None:
            if API_TOKEN is None:
                _session = aiohttp.ClientSession()
            else:
                _session = aiohttp.ClientSession(headers={'Authorization': 'Bearer ' + API_TOKEN})
        async with _session.get(url) as resp:
            if resp_obj == 'text':
                resp = await resp.text()
            if resp_obj == 'json':
                resp = await resp.json(loads=json_loads)
            # if 'error' in resp:  ApiError would interfere with some other stuff,
            # might just change to error trapping
            #     raise ApiError
        logger.info('Parsed data, returning... Time: %s', time.time() - start)
    return resp


class ParseProblem:

    config = {
        'code': str,
        'name': str,
        'authors': [str],  # TODO: [User]?
        'types': [str],
        'group': str,
        'time_limit': float,
        'memory_limit': int,
        'language_resource_limits': [{
            'language': str,
            'time_limit': float,
            'memory_limit': int,
        }],
        'points': float,
        'partial': bool,
        'short_circuit': bool,
        'languages': [Language],
        'is_organization_private': bool,
        'organizations': [Organization],
        'is_public': bool,
    }

    @staticmethod
    async def init(obj):
        # Language, Organization
        languages = session.query(Language.key, Language).all()
        languages = {k: v for k, v in languages}
        if any(lang_key not in languages for lang_key in obj.languages):
            api = API()
            await api.get_languages()
            for lang in api.data.objects:
                if lang.key not in languages:
                    languages[lang.key] = Language(lang)
                    session.add(languages[lang.key])
            session.commit()
        obj.languages = [languages[lang_key] for lang_key in obj.languages]

        organizations = session.query(Organization.id, Organization).all()
        organizations = {k: v for k, v in organizations}
        if any(org_id not in organizations for org_id in obj.organizations):
            api = API()
            await api.get_organizations()
            for org in api.data.objects:
                if org.id not in organizations:
                    organizations[org.id] = Organization(org)
                    session.add(organizations[org.id])
            session.commit()
        obj.organizations = [organizations[org_id] for org_id in obj.organizations]

    @staticmethod
    async def inits(objs):
        await asyncio.gather(*[ParseProblem.init(obj) for obj in objs])


class ParseContest:

    config = {
        'key': str,
        'name': str,
        'start_time': datetime,
        'end_time': datetime,
        'time_limit': float,
        'is_rated': bool,
        'rate_all': bool,
        'has_rating': bool,
        'rating_floor': int,
        'rating_ceiling': int,
        'hidden_scoreboard': bool,
        'scoreboard_visibility': str,
        'is_organization_private': bool,
        'organizations': [Organization],
        'is_private': bool,
        'tags': [str],
        'format': {
            'name': str,
            'config': {
                'cumtime': bool,
                'first_ac_bonus': int,
                'time_bonus': int,
            },
        },
        'problems': [  # TODO: Change to [Problem]
            {
                'points': int,
                'partial': bool,
                'is_pretested': bool,
                'max_submissions': int,
                'label': str,  # TODO: move the label outside of 'problems' so it's a list of Problem type
                'name': str,
                'code': str,
            }
        ],
        'label': [str],  # TODO: Perhaps an alternative to the above?
        'rankings': [  # TODO: change to list of Participation objects
            {
                'user': User,
                'start_time': datetime,
                'end_time': datetime,
                'score': float,
                'cumulative_time': int,
                'tiebreaker': float,
                'old_rating': int,
                'new_rating': int,
                'is_disqualified': bool,
                'solutions': [
                    {
                        'points': float,
                        'time': float,
                    }
                ]
            },
        ],
    }

    @staticmethod
    async def async_init(obj):
        # Move label outside of problems
        obj.label = [problem.label for problem in obj.problems]

        # TODO: Replace rankings (THIS IS NOT RIGHT)
        # NOTE: virtual_participation_number attribute is automatically 0
        obj.rankings = [Participation(ranking) for ranking in obj.rankings]

        organizations = session.query(Organization.id, Organization).all()
        organizations = {k: v for k, v in organizations}
        if any(org_id not in organizations for org_id in obj.organizations):
            api = API()
            await api.get_organizations()
            for org in api.data.objects:
                if org.id not in organizations:
                    organizations[org.id] = Organization(org)
                    session.add(organizations[org.id])
            session.commit()
        obj.organizations = [organizations[org_id] for org_id in obj.organizations]

        problems = session.query(Problem.code, Problem).all()
        problems = {k: v for k, v in problems}
        if any(problem_code not in problems for problem_code in obj.problems):
            for problem in obj.problems:
                code = problem.code
                if code not in problems:
                    api = API()
                    await api.get_problem(code)
                    # TODO: pass in global dict to remove the below query
                    if session.query(Problem).filter(Problem.code == code).count():
                        continue
                    problems[code] = Problem(api.data.objects)
                    session.add(problems[code])
            session.commit()
        obj.problems = [problems[problem.code] for problem in obj.problems]

    @staticmethod
    async def inits(objs):
        await asyncio.gather(*[ParseContest.init(obj) for obj in objs])


class ParseParticipation:

    config = {
        "user": User,
        "contest": Contest,
        "start_time": datetime,
        "end_time": datetime,
        "score": float,
        "cumulative_time": int,
        "tiebreaker": float,
        "old_rating": int,
        "new_rating": int,
        "is_disqualified": bool,
        "solutions": [{
            'points': float,
            'time': float,
        }],
        "virtual_participation_number": int,
    }

    @staticmethod
    async def init(obj):
        user = session.query(User).filter(User.username == obj.user)
        if user.count() == 0:
            api = API()
            await api.get_user(obj.user)
            # NOTE: Possible chance of db error
            session.add(User(api.data.object))
            session.commit()
        obj.user = user.first()

        contest = session.query(Contest).filter(Contest.key == obj.contest)
        if contest.count() == 0:
            api = API()
            await api.get_contest(obj.contest)
            # NOTE: Possible chance of db error
            session.add(Contest(api.data.object))
            session.commit()
        obj.contest = contest.first()

    @staticmethod
    async def inits(objs):
        await asyncio.gather(*[ParseParticipation.init(obj) for obj in objs])


class ParseUser:

    config = {
        "id": int,
        "username": str,
        "points": float,
        "performance_points": float,
        "problem_count": int,
        "solved_problems": [Problem],  # Hybrid attribute TODO: Remove from cfg
        "rank": str,
        "rating": int,
        "volatility": int,
        "organizations": [Organization],
        "contests": [Participation],  # NOTE: There is a very limited amount of info here,
                                      # perhaps take advantage of the `user` filter in /participations
                                      # also it's kinda counterintuative for contests to be a list of
                                      # participation object
                                      # Hybrid attribute TODO: remove from cfg
        "volatilities": [int],
    }

    @staticmethod
    async def init(obj):
        # problem, organization, contest
        problems = session.query(Problem.code, Problem).all()
        problems = {k: v for k, v in problems}
        for code in obj.solved_problems:
            api = API()
            if code not in problems:
                await api.get_problem(code)
                problems[code] = Problem(api.data.object)
                session.add(problems[code])
        session.commit()
        obj.solved_problems = [problems[code] for code in obj.solved_problems]

        organizations = session.query(Organization.id, Organization).all()
        organizations = {k: v for k, v in organizations}
        if any(org_id not in organizations for org_id in obj.organizations):
            api = API()
            await api.get_organizations()
            for org in api.data.objects:
                if org.id not in organizations:
                    organizations[org.id] = Organization(org)
                    session.add(organizations[org.id])
            session.commit()
        obj.organizations = [organizations[org_id] for org_id in obj.organizations]

        # TODO: rewrite/remove entirely
        # for contest in self._contests:
        #     if contest['rating']:
        #         self.max_rating = max(self.max_rating or 0, contest['rating'])

        contests = session.query(Contest.key, Contest).all()
        contests = {k: v for k, v in contests}
        for key in obj.contests:
            api = API()
            if key not in contests:
                await api.get_contest(key)
                contests[key] = Contest(api.data.object)
                session.add(contests[key])
        session.commit()
        obj.contests = [contests[key] for key in obj.contests]

    @staticmethod
    async def inits(objs):
        await asyncio.gather(*[ParseProblem.init(obj) for obj in objs])


class ParseSubmission:

    config = {
        "id": int,
        "problem": Problem,
        "user": User,
        "date": datetime,
        "time": float,
        "memory": float,
        "points": float,
        "language": Language,
        "status": str,
        "result": str,
        "case_points": float,
        "case_total": float,
        "cases": [{
            "type": str,
            "case_id": int,
            "status": str,
            "time": float,
            "memory": float,
            "points": float,
            "total": float,
        }],
    }

    @staticmethod
    async def init(obj, *, problems=None, users=None, languages=None, lock={}):
        if problems is None:
            problems = session.query(Problem.code, Problem).all()
            problems = {k: v for k, v in problems}
        if users is None:
            users = session.query(User.username, User).all()
            users = {k: v for k, v in users}
        if languages is None:
            languages = session.query(Language.key, Language).all()
            languages = {k: v for k, v in languages}

        if obj.problem not in problems and obj.problem not in lock:
            lock[obj.problem] = asyncio.Lock()
            async with lock[obj.problem]:
                api = API()
                await api.get_problem(obj.problem)
                problem = Problem(api.data.object)
                session.add(problem)
                problems[obj.problem] = problem
        if obj.problem in problems:
            obj.problem = problems[obj.problem]

        if obj.user not in users and obj.user not in lock:
            lock[obj.user] = asyncio.Lock()
            async with lock[obj.user]:
                api = API()
                await api.get_user(obj.user)
                user = User(api.data.object)
                session.add(user)
                users[obj.user] = user
        if obj.user in users:
            obj.user = users[obj.user]

        if obj.language not in languages and 'language' not in lock:
            lock['language'] = asyncio.Lock()
            async with lock['language']:
                api = API()
                await api.get_languages()
                for language in api.data.objects:
                    if language.key not in languages:
                        lang = Language(language)
                        session.add(lang)
                        languages[language.key] = lang
        if obj.language in languages:
            obj.language = languages[obj.language]

        if obj.problem is None:
            async with lock[obj._problem]:
                obj.problem = problems[obj._problem]

        if obj.user is None:
            async with lock[obj._user]:
                obj.user = users[obj._user]

        if obj.language is None:
            async with lock['language']:
                obj.language = languages[obj.language]

    @staticmethod
    async def inits(objs):
        problems = session.query(Problem.code, Problem).all()
        problems = {k: v for k, v in problems}
        users = session.query(User.username, User).all()
        users = {k: v for k, v in users}
        languages = session.query(Language.key, Language).all()
        languages = {k: v for k, v in languages}
        tasks = []
        lock = {}
        for obj in objs:
            tasks.append(
                ParseSubmission.init(
                    obj,
                    problems=problems,
                    users=users,
                    languages=languages,
                    lock=lock
                )
            )
        await asyncio.gather(*tasks)


class ParseOrganization:

    config = {
        "id": int,
        "slug": str,
        "short_name": str,
        "is_open": bool,
        "member_count": int,
    }

    @staticmethod
    async def inits(objs):
        pass

    @staticmethod
    async def init(obj):
        pass


class ParseLanguage:

    config = {
        "id": int,
        "key": str,
        "short_name": str,
        "common_name": str,
        "ace_mode_name": str,
        "pygments_name": str,
        "code_template": str,
    }

    @staticmethod
    async def inits(objs):
        pass

    @staticmethod
    async def init(obj):
        pass


class ParseJudge:

    config = {
        "name": str,
        "start_time": datetime,
        "ping": float,
        "load": float,
        "languages": [Language],
    }

    @staticmethod
    async def inits(objs):
        await asyncio.gather(*[ParseJudge.init(obj) for obj in objs])

    @staticmethod
    async def init(obj):
        languages = session.query(Language.key, Language).all()
        languages = {k: v for k, v in languages}
        if any(lang_key not in languages for lang_key in obj.languages):
            api = API()
            await api.get_languages()
            for lang in api.data.objects:
                if lang.key not in languages:
                    languages[lang.key] = Language(lang)
                    session.add(languages[lang.key])
            session.commit()
        obj.languages = [languages[lang_key] for lang_key in obj.languages]


class ObjectNotFound(Exception):
    def __init__(self, data):
        self.code = data.code
        self.message = data.message
        super().__init__(self.message)


class API:

    def __init__(self):
        pass

    @classmethod
    def from_dict(cls, j):
        obj = cls()
        for k, v in j.items():
            try:
                j[k] = datetime.fromisoformat(v)
            except Exception:
                pass
        obj.__dict__.update(j)
        return obj

    def url_encode(self, params):
        # Should cast to string just in case
        query_args = []
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, list):
                for vv in v:
                    query_args.append((k, str(vv)))
            else:
                query_args.append((k, str(v)))
        return '?' + urllib.parse.urlencode(query_args)

    async def parse(self, parse_obj):
        if hasattr(self, 'error'):
            raise ObjectNotFound(self.error)
        if hasattr(self.data, 'object'):
            await parse_obj.init(self.data.object)
            self.data.object.config = parse_obj.config
        else:
            await parse_obj.inits(self.data.objects)
            for obj in self.data.objects:
                obj.config = parse_obj.config


    async def get_contests(self, tag: str = None, organization: str = None, page: int = None) -> None:
        params = {
            'tag': tag,
            'organization': organization,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/contests' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseContest)

    async def get_contest(self, contest_key: str) -> None:
        await _query_api(SITE_URL + 'api/v2/contest/' +
                         contest_key, 'json', self.from_dict)
        await self.parse(ParseContest)

    async def get_participations(self, contest: str = None, user: str = None,
                                 is_disqualified: bool = None,
                                 virtual_participation_number: int = None, page: int = None) -> None:
        params = {
            'contest': contest,
            'user': user,
            'is_disqualified': is_disqualified,
            'virtual_participation_number': virtual_participation_number,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/participations' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseParticipation)

    async def get_problems(self, partial: bool = None, group: str = None, _type: str = None,
                           organization: str = None, search: str = None, page: int = None) -> None:
        params = {
            'partial': partial,
            'group': group,
            'type': _type,
            'organization': organization,
            'search': search,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/problems' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseProblem)

    async def get_problem(self, code: str) -> None:
        await _query_api(SITE_URL + 'api/v2/problem/' +
                         code, 'json', self.from_dict)
        await self.parse(ParseProblem)

    async def get_users(self, organization: str = None, page: int = None) -> None:
        params = {
            'organization': organization,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/users' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseUser)

    async def get_user(self, username: str) -> None:
        await _query_api(SITE_URL + 'api/v2/user/' +
                         username, 'json', self.from_dict)
        await self.parse(ParseUser)

    async def get_submissions(self, user: str = None, problem: str = None,
                              language: str = None, result: str = None, page: int = None) -> None:
        params = {
            'user': user,
            'problem': problem,
            'language': language,
            'result': result,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/submissions' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseSubmission)

    async def get_submission(self, submission_id: typing.Union[int, str]) -> None:
        # Should only accept a string, perhaps I should do something
        # if it were an int
        await _query_api(SITE_URL + 'api/v2/submission/' +
                         str(submission_id), 'json', self.from_dict)
        await self.parse(ParseSubmission)

    async def get_organizations(self, is_open: bool = None, page: int = None) -> None:
        params = {
            'is_open': is_open,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/organizations' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseOrganization)

    async def get_languages(self, common_name: str = None, page: int = None) -> None:
        params = {
            'common_name': common_name,
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/languages' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseLanguage)

    async def get_judges(self, page: int = None) -> None:
        params = {
            'page': page,
        }
        await _query_api(SITE_URL + 'api/v2/judges' +
                         self.url_encode(params), 'json', self.from_dict)
        await self.parse(ParseJudge)

    async def get_pfp(self, username: str) -> str:
        resp = await _query_api(SITE_URL + 'user/' + username, 'text')
        soup = BeautifulSoup(resp, features='html5lib')
        pfp = soup.find('div', class_='user-gravatar').find('img')['src']
        return pfp

    async def get_user_description(self, username: str) -> str:
        resp = await _query_api(SITE_URL + 'user/' + username, 'text')
        soup = BeautifulSoup(resp, features='html5lib')
        description = str(soup.find('div', class_='content-description'))
        return description

    async def get_latest_submission(self, username: str, num: int) -> Submission:
        # Don't look at me! I'm hideous!
        def soup_parse(soup):
            submission_id = soup['id']
            result = soup.find(class_='sub-result')['class'][-1]
            try:
                score = soup.find(class_='sub-result')\
                            .find(class_='score').text.split('/')
                score_num, score_denom = map(int, score)
                points = score_num / score_denom
            except ValueError:
                score_num, score_denom = 0, 0
                points = 0
            lang = soup.find(class_='language').text

            q = session.query(Language).\
                filter(Language.short_name == lang)
            if q.count():
                lang = q.first().key
            # if not as short_name it'll be key, why? idk

            problem = soup.find(class_='name')\
                          .find('a')['href'].split('/')[-1]
            name = soup.find(class_='name').find('a').text
            date = soup.find(class_='time-with-rel')['data-iso']
            try:
                time = float(soup.find('div', class_='time')['title'][:-1])
            except ValueError:
                time = None
            except KeyError:
                time = None
            size = ''
            memory = soup.find('div', class_='memory').text.split(' ')
            if len(memory) == 2:
                memory, size = memory
                memory = float(memory)
                if size == 'MB':
                    memory *= 1024
                if size == 'GB':
                    memory *= 1024 * 1024
            else:
                # --- case
                memory = 0

            res = {
                'id': submission_id,
                'problem': problem,
                'user': username,
                'date': date,
                'language': lang,
                'time': time,
                'memory': memory,
                'points': points,
                'result': result,
                'score_num': score_num,  # TODO: Replace this
                'score_denom': score_denom,  # TODO: Replace this
                'problem_name': html.unescape(name),
            }
            ret = Submission(res)
            return ret
        resp = await _query_api(SITE_URL +
                                f'submissions/user/{username}/', 'text')
        soup = BeautifulSoup(resp, features='html5lib')
        ret = []
        for sub in soup.find_all('div', class_='submission-row')[:num]:
            ret.append(soup_parse(sub))
        # TODO: Do something about this
        await Submission.async_map(Submission, ret)
        return ret

    async def get_placement(self, username: str) -> int:
        resp = await _query_api(SITE_URL + f'user/{username}', 'text')
        soup = BeautifulSoup(resp, features='html5lib')
        rank_str = soup.find('div', class_='user-sidebar')\
                       .findChildren(recursive=False)[3].text
        rank = int(rank_str.split('#')[-1])
        return rank
