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
from utils.models import *
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
        'authors': [User],
        'types': [str],
        'group': str,
        'time_limit': float,
        'memory_limit': int,
        'language_resource_limits': [{
            'language': Language,
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
    async def init(obj, *, languages={}, organizations={}, users={}, lock={}):
        if not languages and hasattr(obj, 'languages'):
            languages_new = session.query(Language.key, Language).all()
            languages.update({k: v for k, v in languages_new})
        if not organizations and hasattr(obj, 'organizations'):
            organizations_new = session.query(Organization.id, Organization).all()
            organizations.update({k: v for k, v in organizations_new})
        if not users and hasattr(obj, 'authors'):
            users_new = session.query(User.username, User).all()
            users.update({k: v for k, v in users_new})

        if hasattr(obj, 'languages'):
            if any(lang_key not in languages for lang_key in obj.languages) and \
                    'language' not in lock:
                lock['language'] = asyncio.Lock()
                async with lock['language']:
                    api = API()
                    await api.get_languages()
                    # languages_new = session.query(Language.key, Language).all()
                    # languages.update({k: v for k, v in languages_new})
                    print(languages)
                    for lang in api.data.objects:
                        if lang.key not in languages:
                            print(lang.key)
                            languages[lang.key] = Language(lang)
                            session.add(languages[lang.key])
                    session.commit()

            if any(lang_key not in languages for lang_key in obj.languages):
                async with lock['language']:
                    obj.languages = [languages[lang_key] for lang_key in obj.languages]
            else:
                obj.languages = [languages[lang_key] for lang_key in obj.languages]

        if hasattr(obj, 'organizations'):
            if any(org_id not in organizations for org_id in obj.organizations) and \
                    'organization' not in lock:
                lock['organization'] = asyncio.Lock()
                async with lock['organization']:
                    api = API()
                    await api.get_organizations()
                    # organizations_new = session.query(Organization.id, Organization).all()
                    # organizations.update({k: v for k, v in organizations_new})
                    for org in api.data.objects:
                        if org.id not in organizations:
                            organizations[org.id] = Organization(org)
                            session.add(organizations[org.id])
                    session.commit()

            if any(org_id not in organizations for org_id in obj.organizations):
                async with lock['organization']:
                    obj.organizations = [organizations[org_id] for org_id in obj.organizations]
            else:
                obj.organizations = [organizations[org_id] for org_id in obj.organizations]

        if hasattr(obj, 'authors'):
            for username in obj.authors:
                if username not in users and username not in lock:
                    lock[username] = asyncio.Lock()
                    async with lock[username]:
                        api = API()
                        await api.get_user(username)
                        # users_new = session.query(User.username, User)\
                        #     .filter(User.username == username).all()
                        # users.update({k: v for k, v in users_new})
                        # if username not in users:
                        users[username] = User(api.data.object)
                        session.add(users[username])
                        session.commit()

            authors = []
            for username in obj.authors:
                if username in lock:
                    async with lock[username]:
                        authors.append(users[username])
                else:
                    authors.append(users[username])
            obj.authors = authors

        if hasattr(obj, 'language_resource_limits'):
            for limit in obj.language_resource_limits:
                if limit.language not in languages:
                    async with lock['organization']:
                        limit.language = languages[limit.language]
                else:
                    limit.language = languages[limit.language]
                limit.config = ParseProblem.config['language_resource_limits'][0]

            obj.language_resource_limits = [ProblemLanguageLimit(limit) for limit in obj.language_resource_limits]

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
        'problems': [
            {
                'is_pretested': bool,
                'max_submissions': int,
                'label': str,
                'problem': Problem,
            }
        ],
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
                ],
                'virtual_participation_number': int,
            },
        ],
    }

    @staticmethod
    async def init(obj, *, organizations={}, problems={}, users={}, lock={}):
        # TODO: Check if attr exists for optimization
        if not organizations:
            organizations_new = session.query(Organization.id, Organization).all()
            organizations.update({k: v for k, v in organizations_new})
        if not problems:
            problems_new = session.query(Problem.code, Problem).all()
            problems.update({k: v for k, v in problems_new})
        if not users:
            users_new = session.query(User.username, User).all()
            users.update({k: v for k, v in users_new})

        if hasattr(obj, 'organizations'):
            if any(org_id not in organizations for org_id in obj.organizations) and \
                    'organization' not in lock:
                lock['organization'] = asyncio.Lock()
                async with lock['organization']:
                    api = API()
                    await api.get_organizations()
                    # organizations_new = session.query(Organization.id, Organization).all()
                    # organizations.update({k: v for k, v in organizations_new})
                    for org in api.data.objects:
                        if org.id not in organizations:
                            organizations[org.id] = Organization(org)
                            session.add(organizations[org.id])
                    session.commit()
            if any(org_id not in organizations for org_id in obj.organizations):
                async with lock['organization']:
                    obj.organizations = [organizations[org_id] for org_id in obj.organizations]
            else:
                obj.organizations = [organizations[org_id] for org_id in obj.organizations]

        if hasattr(obj, 'problems'):
            if all(hasattr(problem, 'code') for problem in obj.problems):
                for problem in obj.problems:
                    code = problem.code
                    if code not in problems and code not in lock:
                        lock[code] = asyncio.Lock()
                        async with lock[code]:
                            api = API()
                            await api.get_problem(code)
                            # problems_new = session.query(Problem.code, Problem)\
                            #     .filter(Problem.code == code).all()
                            # problems.update({k: v for k, v in problems_new})
                            # if code not in problems:
                            problems[code] = Problem(api.data.object)
                            session.add(problems[code])
                            session.commit()

            for problem in obj.problems:
                if problem.code in lock:
                    async with lock[problem.code]:
                        problem.problem = problems[problem.code]
                else:
                    problem.problem = problems[problem.code]

        if hasattr(obj, 'problems'):
            for problem in obj.problems:
                problem.config = ParseContest.config['problems'][0]
            obj.problems = [ContestProblem(problem) for problem in obj.problems]

        if hasattr(obj, 'rankings'):
            # NOTE: Delegate parsing to ParseParticipation? It should work
            tasks = []
            for ranking in obj.rankings:
                ranking.virtual_participation_number = 0
                ranking.config = ParseParticipation.config
                tasks.append(ParseParticipation.init(ranking, users=users))
            await asyncio.gather(*tasks)
            obj.rankings = [Participation(ranking) for ranking in obj.rankings]
            for ranking in obj.rankings:
                session.add(ranking)
            session.commit()

    @staticmethod
    async def inits(objs):
        organizations = session.query(Organization.id, Organization).all()
        organizations = {k: v for k, v in organizations}
        problems = session.query(Problem.code, Problem).all()
        problems = {k: v for k, v in problems}
        users = session.query(User.username, User).all()
        users = {k: v for k, v in users}
        tasks = []
        lock = {}
        for obj in objs:
            tasks.append(
                ParseContest.init(
                    obj,
                    organizations=organizations,
                    problems=problems,
                    users=users,
                    lock=lock,
                )
            )
        await asyncio.gather(*tasks)


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
    async def init(obj, *, contests={}, users={}, lock={}):
        if not contests and hasattr(obj, 'contest'):
            # NOTE: It's prob much better to just load the single contest
            contests_new = session.query(Contest.key, Contest)\
                .filter(Contest.key == obj.contest).all()
            contests.update({k: v for k, v in contests_new})
        if not users and hasattr(obj, 'user'):
            users_new = session.query(User.username, User)\
                .filter(User.username == obj.user).all()
            users.update({k: v for k, v in users_new})

        if hasattr(obj, 'contest'):
            if obj.contest not in contests and obj.contest not in lock:
                lock[obj.contest] = asyncio.Lock()
                async with lock[obj.contest]:
                    api = API()
                    await api.get_contest(obj.contest)
                    # contests_new = session.query(Contest.key, Contest)\
                    #     .filter(Contest.key == obj.contest).all()
                    # contests.update({k: v for k, v in contests_new})
                    # if obj.contest not in contests:
                    contests[obj.contest] = Contest(api.data.object)
                    session.add(contests[obj.contest])
                    session.commit()
            if obj.contest in lock:
                async with lock[obj.contest]:
                    obj.contest = contests[obj.contest]
            else:
                obj.contest = contests[obj.contest]

        if hasattr(obj, 'user'):
            if obj.user not in users and obj.user not in lock:
                lock[obj.user] = asyncio.Lock()
                async with lock[obj.user]:
                    api = API()
                    await api.get_user(obj.user)
                    # users_new = session.query(User.username, User)\
                    #     .filter(User.username == obj.user).all()
                    # users.update({k: v for k, v in users_new})
                    # if obj.user not in users:
                    users[obj.user] = User(api.data.object)
                    session.add(users[obj.user])
                    session.commit()
            if obj.user in lock:
                async with lock[obj.user]:
                    obj.user = users[obj.user]
            else:
                obj.user = users[obj.user]

        solutions = []
        for solution in obj.solutions:
            if solution is None:
                continue
            solution.config = ParseParticipation.config['solutions'][0]
            solutions.append(ParticipationSolution(solution))
        obj.solutions = solutions

    @staticmethod
    async def inits(objs):
        contests = session.query(Contest.key, Contest).all()
        contests = {k: v for k, v in contests}
        users = session.query(User.username, User).all()
        users = {k: v for k, v in users}
        tasks = []
        lock = {}
        for obj in objs:
            tasks.append(
                ParseParticipation.init(
                    obj,
                    contests=contests,
                    users=users,
                    lock=lock,
                )
            )
        await asyncio.gather(*tasks)


class ParseUser:

    config = {
        "id": int,
        "username": str,
        "points": float,
        "performance_points": float,
        "problem_count": int,
        # "solved_problems": [Problem],  # Hybrid attribute TODO: Remove from cfg
        "rank": str,
        "rating": int,
        "volatility": int,
        "organizations": [Organization],
        # "contests": [Participation],  # NOTE: There is a very limited amount of info here,
        #                               # perhaps take advantage of the `user` filter in /participations
        #                               # also it's kinda counterintuative for contests to be a list of
        #                               # participation object
        #                               # Hybrid attribute TODO: remove from cfg
        # "volatilities": [int],
    }

    @staticmethod
    async def init(obj, *, organizations={}, lock={}):
        if not organizations and hasattr(obj, 'organizations'):
            organizations_new = session.query(Organization.id, Organization).all()
            organizations.update({k: v for k, v in organizations_new})

        if hasattr(obj, 'organizations'):
            if any(org_id not in organizations for org_id in obj.organizations) and \
                    'organization' not in lock:
                lock['organization'] = asyncio.Lock()
                async with lock['organization']:
                    api = API()
                    await api.get_organizations()
                    # organizations_new = session.query(Organization.id, Organization).all()
                    # organizations.update({k: v for k, v in organizations_new})
                    for org in api.data.objects:
                        if org.id not in organizations:
                            print(org.id)
                            organizations[org.id] = Organization(org)
                            session.add(organizations[org.id])
                    session.commit()

            if any(org_id not in organizations for org_id in obj.organizations):
                async with lock['organization']:
                    print(organizations)
                    obj.organizations = [organizations[org_id] for org_id in obj.organizations]
            else:
                obj.organizations = [organizations[org_id] for org_id in obj.organizations]

        if hasattr(obj, 'contests'):
            # obj.volatilities = [contest.volatility for contest in obj.contests]
            del obj.contests
            pass
            # NOTE: This is not fetched from API, so .config needs to be added
            # FIXME: Creates a cycle
            # FIX: Make it a hybridproperty?
            # TODO: Maybe just leave a broken foreign key?
            # NOTE: If so, must delete the row before inserting new/better data
            # for contest in obj.contests:
            #     contest.config = ParseParticipation.config
            #     contest.virtual_participation_number = 0
            #     contest.config['contest_id'] = str
            #     contest.contest_id = contest.key
            # obj.contests = [Participation(contest) for contest in obj.contests]
            # for contest in obj.contests:
            #     session.add(contest)
            # session.commit()

        if hasattr(obj, 'solved_problems'):
            del obj.solved_problems
            pass
            # FIXME: This creates a cycle w/ authors
            # 1. Perhaps we could take advantage of the fact that /problems is called on startup
            # 2. Perhaps remove this entirely and keep authors, add a hybrid property and this will only work if submissions are cached
            # NOTE: Using #2. requires a little note, but is more reliable.


    @staticmethod
    async def inits(objs):
        organizations = session.query(Organization.id, Organization).all()
        organizations = {k: v for k, v in organizations}
        tasks = []
        lock = {}
        for obj in objs:
            tasks.append(
                ParseUser.init(
                    obj,
                    organizations=organizations,
                    lock=lock
                )
            )
        await asyncio.gather(*tasks)


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
    async def init(obj, *, languages={}, problems={}, users={}, lock={}):
        if not languages and hasattr(obj, 'language'):
            languages_new = session.query(Language.key, Language)\
                .filter(Language.key == obj.language).all()
            languages.update({k: v for k, v in languages_new})
        if not problems and hasattr(obj, 'problem'):
            problems_new = session.query(Problem.code, Problem)\
                .filter(Problem.code == obj.problem).all()
            problems.update({k: v for k, v in problems_new})
        if not users and hasattr(obj, 'user'):
            users_new = session.query(User.username, User)\
                .filter(User.username == obj.user).all()
            users.update({k: v for k, v in users_new})

        if hasattr(obj, 'language'):
            if obj.language not in languages and 'language' not in lock:
                lock['language'] = asyncio.Lock()
                async with lock['language']:
                    api = API()
                    await api.get_languages()
                    # languages_new = session.query(Language.key, Language).all()
                    # languages.update({k: v for k, v in languages_new})
                    for language in api.data.objects:
                        if language.key not in languages:
                            lang = Language(language)
                            session.add(lang)
                            languages[language.key] = lang
                    session.commit()
            if 'language' in lock:
                async with lock['language']:
                    obj.language = languages[obj.language]
            else:
                obj.language = languages[obj.language]

        if hasattr(obj, 'problem'):
            if obj.problem not in problems and obj.problem not in lock:
                lock[obj.problem] = asyncio.Lock()
                async with lock[obj.problem]:
                    api = API()
                    await api.get_problem(obj.problem)
                    # problems_new = session.query(Problem.code, Problem)\
                    #     .filter(Problem.code == obj.problem).all()
                    # problems.update({k: v for k, v in problems_new})
                    # if obj.problem not in problems:
                    problem = Problem(api.data.object)
                    session.add(problem)
                    problems[obj.problem] = problem
                    session.commit()
            if obj.problem in lock:
                async with lock[obj.problem]:
                    obj.problem = problems[obj.problem]
            else:
                obj.problem = problems[obj.problem]

        if hasattr(obj, 'user'):
            if obj.user not in users and obj.user not in lock:
                lock[obj.user] = asyncio.Lock()
                async with lock[obj.user]:
                    api = API()
                    await api.get_user(obj.user)
                    # users_new = session.query(User.username, User)\
                    #     .filter(User.username == obj.user).all()
                    # users.update({k: v for k, v in users_new})
                    # if obj.user not in users:
                    user = User(api.data.object)
                    session.add(user)
                    users[obj.user] = user
                    session.commit()
            if obj.user in lock:
                async with lock[obj.user]:
                    obj.user = users[obj.user]
            else:
                obj.user = users[obj.user]

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
                    languages=languages,
                    problems=problems,
                    users=users,
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
    async def init(obj, *, languages={}, lock={}):
        if not languages:
            languages_new = session.query(Language.key, Language).all()
            languages.update({k: v for k, v in languages_new})

        if any(lang_key not in languages for lang_key in obj.languages) and \
                'language' not in lock:
            # NOTE: The way this is designed is to allow one process to go through this
            # and the rest to wait at the `async with lock`
            lock['language'] = asyncio.Lock()
            async with lock['language']:
                api = API()
                await api.get_languages()
                # languages_new = session.query(Language.key, Language).all()
                # languages.update({k: v for k, v in languages_new})
                for lang in api.data.objects:
                    if lang.key not in languages:
                        languages[lang.key] = Language(lang)
                        session.add(languages[lang.key])
                session.commit()

        if any(lang_key not in languages for lang_key in obj.languages):
            async with lock['language']:
                obj.languages = [languages[lang_key] for lang_key in obj.languages]
        else:
            # NOTE: This is just if everything is found inside db already
            obj.languages = [languages[lang_key] for lang_key in obj.languages]

    @staticmethod
    async def inits(objs):
        languages = session.query(Language.key, Language).all()
        languages = {k: v for k, v in languages}
        tasks = []
        lock = {}
        for obj in objs:
            tasks.append(
                ParseJudge.init(
                    obj,
                    languages=languages,
                    lock=lock
                )
            )
        await asyncio.gather(*tasks)


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

    async def parse(self, resp, parse_obj):
        self.__dict__.update(resp.__dict__)

        if hasattr(self, 'error'):
            raise ObjectNotFound(self.error)
        if hasattr(self.data, 'object'):
            await parse_obj.init(self.data.object)
            self.data.object.config = parse_obj.config
            self.data.objects = None
        else:
            await parse_obj.inits(self.data.objects)
            for obj in self.data.objects:
                obj.config = parse_obj.config
            self.data.object = None

    async def get_contests(self, tag: str = None, organization: str = None, page: int = None) -> None:
        params = {
            'tag': tag,
            'organization': organization,
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/contests' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseContest)

    async def get_contest(self, contest_key: str) -> None:
        resp = await _query_api(SITE_URL + 'api/v2/contest/' +
                                contest_key, 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseContest)

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
        resp = await _query_api(SITE_URL + 'api/v2/participations' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseParticipation)

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
        resp = await _query_api(SITE_URL + 'api/v2/problems' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseProblem)

    async def get_problem(self, code: str) -> None:
        resp = await _query_api(SITE_URL + 'api/v2/problem/' +
                                code, 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseProblem)

    async def get_users(self, organization: str = None, page: int = None) -> None:
        params = {
            'organization': organization,
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/users' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseUser)

    async def get_user(self, username: str) -> None:
        resp = await _query_api(SITE_URL + 'api/v2/user/' +
                                username, 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseUser)

    async def get_submissions(self, user: str = None, problem: str = None,
                              language: str = None, result: str = None, page: int = None) -> None:
        params = {
            'user': user,
            'problem': problem,
            'language': language,
            'result': result,
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/submissions' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseSubmission)

    async def get_submission(self, submission_id: typing.Union[int, str]) -> None:
        # Should only accept a string, perhaps I should do something
        # if it were an int
        resp = await _query_api(SITE_URL + 'api/v2/submission/' +
                                str(submission_id), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseSubmission)

    async def get_organizations(self, is_open: bool = None, page: int = None) -> None:
        params = {
            'is_open': is_open,
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/organizations' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseOrganization)

    async def get_languages(self, common_name: str = None, page: int = None) -> None:
        params = {
            'common_name': common_name,
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/languages' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseLanguage)

    async def get_judges(self, page: int = None) -> None:
        params = {
            'page': page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/judges' +
                                self.url_encode(params), 'json', object_hook=self.from_dict)
        await self.parse(resp, ParseJudge)

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
