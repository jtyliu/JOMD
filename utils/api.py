# from utils.submission import Submission
# from utils.problem import Problem
from bs4 import BeautifulSoup
from utils.constants import SITE_URL, DEBUG_API
import urllib.parse
import functools
import aiohttp
import asyncio
import time
from datetime import datetime
from utils.db import session
from utils.db import (Problem as Problem_DB, Contest as Contest_DB,
                          Participation as Participation_DB,
                          User as User_DB, Submission as Submission_DB,
                          Organization as Organization_DB,
                          Language as Language_DB, Judge as Judge_DB)


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
    if DEBUG_API:
        print("Calling", url)
    global _session
    if _session is None:
        _session = aiohttp.ClientSession()
    async with _session.get(url) as resp:
        if resp_obj == 'text':
            resp = await resp.text()
        if resp_obj == 'json':
            resp = await resp.json()
        # if 'error' in resp:  ApiError would interfere with some other stuff,
        # might just change to error trapping
        #     raise ApiError
        return resp


class Problem:
    def __init__(self, data):
        self.code = data["code"]
        self.name = data["name"]
        self.types = data["types"]
        self.group = data["group"]
        self.points = data["points"]
        self.partial = data["partial"]
        self.authors = data.get("authors")
        self.time_limit = data.get("time_limit")
        self.memory_limit = data.get("memory_limit")
        self.language_resource_limits = data.get("language_resource_limits")
        self.short_circuit = data.get("short_circuit")
        self._languages = data.get("languages") or []
        self.languages = []
        self.is_organization_private = data.get("is_organization_private")
        self._organizations = data.get("organizations") or []
        self.organizations = []

        self.is_public = data.get("is_public")

    async def async_init(self):
        for language_key in self._languages:
            language_q = session.query(Language_DB).\
                filter(Language_DB.key == language_key)
            if language_q.count() == 0:
                api = API()
                await api.get_languages()
                for language in api.data.objects:
                    if language.key == language_key:
                        session.add(Language_DB(language))
                        session.commit()
                        break
            self.languages.append(language_q.first())

        for organization_id in self._organizations:
            organization_q = session.query(Organization_DB).\
                filter(Organization_DB.id == organization_id)
            if organization_q.count() == 0:
                api = API()
                await api.get_organizations()
                for organization in api.data.objects:
                    if organization.id == organization_id:
                        session.add(Organization_DB(organization))
                        session.commit()
                        break
            self.organizations.append(organization_q.first())


class Contest:

    def __init__(self, data):
        self.key = data["key"]
        self.name = data["name"]
        self.start_time = datetime.fromisoformat(data["start_time"])
        self.end_time = datetime.fromisoformat(data["end_time"])
        self.time_limit = data["time_limit"]
        self.tags = data["tags"]
        self.is_rated = data.get("is_rated")
        self.rate_all = data.get("rate_all")
        self.has_rating = data.get("has_rating")
        self.rating_floor = data.get("rating_floor")
        self.rating_ceiling = data.get("rating_ceiling")
        self.hidden_scoreboard = data.get("hidden_scoreboard")
        self.is_organization_private = data.get("is_organization_private")
        self._organizations = data.get("organizations") or []
        self.organizations = []
        self.is_private = data.get("is_private")
        self.format = data.get("format")
        self.rankings = data.get("rankings")
        self._problems = data.get("problems") or []
        self.problems = []
    
    async def async_init(self):
        for organization_id in self._organizations:
            organization_q = session.query(Organization_DB).\
                filter(Organization_DB.id == organization_id)
            if organization_q.count() == 0:
                api = API()
                await api.get_organizations()
                for organization in api.data.objects:
                    if organization.id == organization_id:
                        session.add(Organization_DB(organization))
                        session.commit()
                        break
            self.organizations.append(organization_q.first())

        # perhaps I should check if it's the general or detailed version
        for problem_dict in self._problems:
            problem_code = problem_dict["code"]
            problem = session.query(Problem_DB).\
                filter(Problem_DB.code == problem_code)
            try:
                if problem.count() == 0:
                    api = API()
                    await api.get_problem(problem_code)
                    session.add(Problem_DB(api.data.object))
                    session.commit()
                self.problems.append(problem.first())
            except ObjectNotFound:
                pass


class Participation:

    def __init__(self, data):
        self.id = data["user"] + "&" + data["contest"] + "&" \
                  + str(data["virtual_participation_number"])
        self._user = data["user"]
        self.user = None
        self._contest = data["contest"]
        self.contest = None
        self.score = data["score"]
        self.cumulative_time = data["cumulative_time"]
        self.tiebreaker = data["tiebreaker"]
        self.is_disqualified = data["is_disqualified"]
        self.virtual_participation_number = data["virtual_participation_number"]

    async def async_init(self):
        user = session.query(User_DB).\
            filter(User_DB.username == self._user)
        
        if user.count() == 0:
            api = API()
            await api.get_user(self._user)
            session.add(api.data.object)
            session.commit()
        self.user = user.first()

        contest = session.query(Contest_DB).\
            filter(Contest_DB.key == self._contest)
        
        if contest.count() == 0:
            api = API()
            await api.get_contest(self._contest)
            session.add(api.data.object)
            session.commit()
        self.contest = contest.first()


class User:
    def __init__(self, data):
        self.id = data["id"]
        self.username = data["username"]
        self.points = data["points"]
        self.performance_points = data["performance_points"]
        self.problem_count = data["problem_count"]
        self.rank = data["problem_count"]
        self.rating = data["rating"]
        self.volatility = data["volatility"]
        self._solved_problems = data.get("solved_problems") or []
        self.solved_problems = []
        self._organizations = data.get("organizations") or []
        self.organizations = []
        self._contests = data.get("contests") or []
        self.contests = []

    async def async_init(self):
        for problem_code in self._solved_problems:
            problem_q = session.query(Problem_DB).\
                filter(Problem_DB.code == problem_code)
            try:
                if problem_q.count() == 0:
                    api = API()
                    await api.get_problem(problem_code)
                    session.add(Problem_DB(api.data.object))
                    session.commit()
                self.solved_problems.append(problem_q.first())
            except ObjectNotFound:
                pass

        for organization_id in self._organizations:
            organization_q = session.query(Organization_DB).\
                filter(Organization_DB.id == organization_id)
            if organization_q.count() == 0:
                api = API()
                await api.get_organizations()
                for organization in api.data.objects:
                    if organization.id == organization_id:
                        session.add(Organization_DB(organization))
                        session.commit()
                        break
            self.organizations.append(organization_q.first())
        
        for contest_dict in self._contests:
            contest_key = contest_dict["key"]
            contest_q = session.query(Contest_DB).\
                filter(Contest_DB.key == contest_key)
            try:
                if contest_q.count() == 0:
                    api = API()
                    await api.get_contest(contest_key)
                    session.add(Contest_DB(api.data.object))
                    session.commit()
                self.contests.append(contest_q.first())
            except ObjectNotFound:
                pass


class Submission:
    def __init__(self, data):
        self.id = data["id"]
        self._problem = data["problem"]
        # self.problem = []
        self._user = data["user"]
        # self.user = []
        self.date = datetime.fromisoformat(data["date"])
        self._language = data["language"]
        # self.language = []
        self.time = data["time"]
        self.memory = data["memory"]
        self.points = data["points"]
        self.result = data["result"]
        self.status = data.get("status")
        self.case_points = data.get("case_points")
        self.case_total = data.get("case_total")
        self.cases = data.get("cases")

    async def async_init(self):
        problem_q = session.query(Problem_DB).\
            filter(Problem_DB.code == self._problem)
        if problem_q.count() == 0:
            api = API()
            await api.get_problem(self._problem)
            session.add(Problem_DB(api.data.object))
            session.commit()
        self.problem = problem_q.first()

        user_q = session.query(User_DB).\
            filter(User_DB.username == self._user)
        if user_q.count() == 0:
            api = API()
            await api.get_user(self._user)
            session.add(User_DB(api.data.object))
            session.commit()
        self.user = user_q.first()

        language_q = session.query(Language_DB).\
            filter(Language_DB.key == self._language)
        if language_q.count() == 0:
            api = API()
            await api.get_languages()
            for language in api.data.objects:
                if language.key == self._language:
                    session.add(Language_DB(language))
                    session.commit()
                    break
        self.language = language_q.first()


class Organization:
    def __init__(self, data):
        self.id = data["id"]
        self.slug = data["slug"]
        self.short_name = data["short_name"]
        self.is_open = data["is_open"]
        self.member_count = data["member_count"]

    async def async_init(self):
        pass


class Language:
    def __init__(self, data):
        self.id = data["id"]
        self.key = data["key"]
        self.short_name = data["short_name"]
        self.common_name = data["common_name"]
        self.ace_mode_name = data["ace_mode_name"]
        self.pygments_name = data["pygments_name"]
        self.code_template = data["code_template"]

    async def async_init(self):
        pass


class Judge:
    def __init__(self, data):
        self.name = data["name"]
        self.start_time = datetime.fromisoformat(data["start_time"])
        self.ping = data["ping"]
        self.load = data["load"]
        self.languages = data["languages"]

    async def async_init(self):
        pass


class ObjectNotFound(Exception):
    def __init__(self, data):
        self.code = data["code"]
        self.message = data["message"]
        super().__init__(self.message)


class API:

    class Data:
        def __init__(self):
            pass

        def async_map(self, _type, data):
            ret = []
            for obj in self.objects:
                ret.append(obj.async_init())
            return ret

        async def parse(self, data, _type):
            if "object" in data:
                self.object = _type(data["object"])
                self._object = await self.object.async_init()
                self.objects = None
            else:
                self.current_object_count = data["current_object_count"]
                self.objects_per_page = data["objects_per_page"]
                self.page_index = data["page_index"]
                self.has_more = data["has_more"]
                self.total_pages = data["total_pages"]
                self.total_objects = data["total_objects"]

                self.objects = list(map(_type, data["objects"]))
                self._objects = self.async_map(_type, self.objects)
                self._objects = await asyncio.gather(*self._objects)
                self.object = None
            return self

    def __init__(self):
        pass

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

    async def parse(self, data, _type):
        self.api_version = data["api_version"]
        self.method = data["method"]
        self.fetched = data["fetched"]
        if "error" in data:
            raise ObjectNotFound(data["error"])
        else:
            # print((data["data"], _type))
            dat = self.Data()
            self.data = await dat.parse(data["data"], _type)

    async def get_contests(self, tag=None, organization=None, page=None):
        params = {
            "tag": tag,
            "organization": organization,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/contests' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Contest)

    async def get_contest(self, contest_key):
        resp = await _query_api(SITE_URL + 'api/v2/contest/' +
                                contest_key, 'json')
        await self.parse(resp, Contest)

    async def get_participations(self, contest=None, user=None,
                                 is_disqualified=None,
                                 virtual_participation_number=None, page=None):
        params = {
            "contest": contest,
            "user": user,
            "is_disqualified": is_disqualified,
            "virtual_participation_number": virtual_participation_number,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/participations' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Participation)

    async def get_problems(self, partial=None, group=None, _type=None,
                           organization=None, search=None, page=None):
        params = {
            "partial": partial,
            "group": group,
            "type": _type,
            "organization": organization,
            "search": search,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/problems' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Problem)

    async def get_problem(self, code):
        resp = await _query_api(SITE_URL + 'api/v2/problem/' +
                                code, 'json')
        await self.parse(resp, Problem)

    async def get_users(self, organization=None, page=None):
        params = {
            "organization": organization,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/users' +
                                self.url_encode(params), 'json')
        await self.parse(resp, User)

    async def get_user(self, username):
        resp = await _query_api(SITE_URL + 'api/v2/user/' +
                                username, 'json')
        await self.parse(resp, User)

    async def get_submissions(self, user=None, problem=None,
                              language=None, result=None, page=None):
        params = {
            "user": user,
            "problem": problem,
            "language": language,
            "result": result,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/submissions' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Submission)

    async def get_submission(self, submission_id):
        # Should only accept a string, perhaps I should do something
        # if it were an int
        resp = await _query_api(SITE_URL + 'api/v2/submission/' +
                                submission_id, 'json')
        await self.parse(resp, Submission)

    async def get_organizations(self, is_open=None, page=None):
        params = {
            "is_open": is_open,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/organizations' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Organization)

    async def get_languages(self, common_name=None, page=None):
        params = {
            "common_name": common_name,
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/languages' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Language)

    async def get_judges(self, page=None):
        params = {
            "page": page,
        }
        resp = await _query_api(SITE_URL + 'api/v2/judges' +
                                self.url_encode(params), 'json')
        await self.parse(resp, Judge)

    async def get_pfp(self, username):
        resp = await _query_api(SITE_URL + 'user/' + username, 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        pfp = soup.find('div', class_='user-gravatar').find('img')['src']
        return pfp

    async def get_latest_submission(self, user, num):
        # Don't look at me! I'm hideous!
        async def soup_parse(soup):
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

            q = session.query(Language_DB).\
                filter(Language_DB.short_name == lang)
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
            memory = soup.find('div', class_='memory').text
            res = {
                "id": submission_id,
                "problem": problem,
                "user": user,
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
            ret = Submission(res)
            await ret.async_init()
            return ret
        resp = await _query_api(SITE_URL +
                                f'submissions/user/{user}/', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        ret = []
        for sub in soup.find_all('div', class_='submission-row')[:num]:
            ret.append(soup_parse(sub))
        return await asyncio.gather(*ret)
    
    async def get_placement(self, username):
        resp = await _query_api(SITE_URL + f'user/{username}', 'text')
        soup = BeautifulSoup(resp, features="html5lib")
        rank_str = soup.find('div', class_='user-sidebar')\
                       .findChildren(recursive=False)[3].text
        rank = int(rank_str.split('#')[-1])
        return rank