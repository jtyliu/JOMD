from discord import utils
from discord.ext import commands
from discord.ext.commands.errors import MemberNotFound
from utils.api import API
from sqlalchemy import or_, func
from utils.models import *
from typing import List
from sqlalchemy.sql import functions
import asyncio
from operator import attrgetter, itemgetter
import logging
logger = logging.getLogger(__name__)


class Query:
    '''
    Every object returned from this should be a DB object, not class object
    '''

    def parse(self, key, val):
        cond = True
        if val is not None:
            if isinstance(val, str):
                cond = key == val
            elif isinstance(val, list):
                cond = key.in_(val)
            elif isinstance(val, functions.Function):
                cond = key == val
            elif isinstance(val, bool):
                cond = key == val
        return cond

    async def get_pfp(self, username: str) -> str:
        return await API().get_pfp(username)

    async def get_user_description(self, username: str) -> str:
        return await API().get_user_description(username)

    async def get_languages(self, common_name: str = None) -> List[Language]:

        q = session.query(Language).\
            filter(self.parse(Language.common_name, common_name))
        if q.count():
            return q.all()
        a = API()
        await a.get_languages(common_name=common_name)
        languages = list(map(Language, a.data.objects))
        for language in languages:
            session.add(language)
        session.commit()
        return languages

    async def get_problems(self, partial: bool = None, group: str = None, _type: str = None,
                           organization: str = None, search: str = None, cached: bool = False) -> List[Problem]:

        q = session.query(Problem).\
            filter(self.parse(Problem.partial, partial)).\
            filter(self.parse(Problem.group, group)).\
            filter(self.parse(Problem.types, _type)).\
            filter(self.parse(Problem.organizations, organization))
        if cached:
            return q.all()

        a = API()
        if search is not None:
            # Can't bother to implement something with db
            # maybe future me can do this
            await a.get_problems(partial=partial, group=group, _type=_type,
                                 organization=organization, search=search)
            return list(map(Problem, a.data.objects))

        page = 1
        await a.get_problems(partial=partial, group=group, _type=_type,
                             organization=organization, search=search,
                             page=page)

        if a.data.total_objects == q.count():
            return q.all()

        for problem in a.data.objects:
            qq = session.query(Problem).\
                filter(Problem.code == problem.code)
            if qq.count() == 0:
                session.add(Problem(problem))

        while a.data.has_more:
            page += 1
            await a.get_problems(partial=partial, group=group, _type=_type,
                                 organization=organization, search=search,
                                 page=page)

            for problem in a.data.objects:
                qq = session.query(Problem).\
                    filter(Problem.code == problem.code)
                if qq.count() == 0:
                    session.add(Problem(problem))
        session.commit()
        return q.all()

    async def get_problem(self, code: str, cached: bool = True) -> Problem:
        q = session.query(Problem).\
            filter(Problem.code == code)
        if q.count() and cached:
            # has_rating check if it has a detailed row
            if q.first().short_circuit is not None:
                return q.first()

        a = API()
        await a.get_problem(code)
        q = session.query(Problem).\
            filter(Problem.code == a.data.object.code)
        if q.count():
            session.delete(q.scalar())
        session.add(Problem(a.data.object))
        session.commit()
        return q.first()

    async def get_judges(self) -> List[Judge]:
        # If this ever has more than 1 page, I'll eat a rock
        a = API()
        await a.get_judges()
        return list(map(Judge, a.data.objects))

    async def get_contests(self, tag: str = None,
                           organization: str = None) -> List[Contest]:
        a = API()

        page = 1
        await a.get_contests(tag=tag, organization=organization, page=page)

        q = session.query(Contest).\
            filter(self.parse(Contest.tags, tag)).\
            filter(self.parse(Contest.organizations, organization))

        if a.data.total_objects == q.count():
            return q.all()

        for contest in a.data.objects:
            qq = session.query(Contest).\
                filter(Contest.key == contest.key)
            if qq.count() == 0:
                session.add(Contest(contest))

        while a.data.has_more:
            page += 1
            await a.get_contests(tag=tag, organization=organization, page=page)

            for contest in a.data.objects:
                qq = session.query(Contest).\
                    filter(Contest.key == contest.key)
                if qq.count() == 0:
                    session.add(Contest(contest))
        session.commit()
        return q.all()

    async def get_contest(self, key: str, cached: bool = True) -> Contest:
        q = session.query(Contest).\
            filter(Contest.key == key)
        if q.count() and cached:
            # is_rated checks if it has detailed rows
            if q.first().has_rating is not None:
                return q.first()
        a = API()
        await a.get_contest(key)
        # Requery the key to prevent path traversal from killing db
        q = session.query(Contest).\
            filter(Contest.key == a.data.object.key)
        if q.count():
            session.delete(q.scalar())
        session.add(Contest(a.data.object))
        session.commit()
        return q.first()

    async def get_users(self, organization: str = None) -> List[User]:
        a = API()

        page = 1
        await a.get_users(organization=organization, page=page)

        q = session.query(User).\
            filter(self.parse(User.organizations, organization))

        if a.data.total_objects == q.count():
            return q.all()

        for user in a.data.objects:
            qq = session.query(User).\
                filter(User.id == user.id)
            if qq.count() == 0:
                session.add(User(user))

        while a.data.has_more:
            page += 1
            await a.get_users(organization=organization, page=page)

            for user in a.data.objects:
                qq = session.query(User).\
                    filter(User.id == user.id)
                if qq.count() == 0:
                    session.add(User(user))
        session.commit()
        return q.all()

    async def get_user(self, username: str) -> User:
        a = API()
        await a.get_user(username)
        q = session.query(User).\
            filter(User.username == a.data.object.username)
        if q.count():
            session.delete(q.scalar())

        session.add(User(a.data.object))
        session.commit()
        return q.first()

    async def get_participations(
        self, contest: str = None, user: str = None, is_disqualified: bool = None,
        virtual_participation_number: int = None
    ) -> List[Participation]:
        a = API()

        page = 1
        await a.get_participations(
            contest=contest, user=user, is_disqualified=is_disqualified,
            virtual_participation_number=virtual_participation_number,
            page=page
        )

        # why the hell are these names so long?
        cond_contest = self.parse(Contest.key, contest)
        if not cond_contest:
            cond_contest = Participation.contest.any(cond_contest)

        cond_user = self.parse(func.lower(User.username), func.lower(user))
        if not cond_user:
            cond_user = Participation.user.has(cond_user)

        q = session.query(Participation).\
            filter(cond_contest).\
            filter(cond_user).\
            filter(self.parse(Participation.is_disqualified,
                              is_disqualified)).\
            filter(self.parse(Participation.virtual_participation_number,
                              virtual_participation_number))

        if a.data.total_objects == q.count():
            return q.all()

        for participation in q.all():
            session.delete(participation)
        session.commit()

        total_pages = a.data.total_pages
        for participation in a.data.objects:
            session.add(Participation(participation))

        apis = []
        to_gather = []

        for _ in range(2, total_pages + 1):
            page += 1
            api = API()
            to_await = await a.get_participations(
                contest=contest, user=user, is_disqualified=is_disqualified,
                virtual_participation_number=virtual_participation_number,
                page=page
            )
            apis.append(api)
            to_gather.append(to_await)
        await asyncio.gather(*to_gather)
        for api in apis:
            total_pages = api.data.total_pages
            for participation in api.data.objects:
                session.add(Participation(participation))
        session.commit()
        return q.all()

    async def get_submissions(self, user: str = None, problem: str = None, language: str = None,
                              result: str = None) -> List[Submission]:
        # This function is the only one which might take a while to run and
        # has data that is added reguarly. asyncio.gather can apply to all
        # functions but this one is the only one which really needs it
        a = API()
        page = 1
        import time
        start = time.time()
        await a.get_submissions(user=user, problem=problem, language=language,
                                result=result, page=page)

        logger.info("Got submissions for %s, time elasped %s", user, time.time() - start)
        start = time.time()
        q = session.query(Submission)

        cond_user = self.parse(func.lower(User.username), func.lower(user))
        if not cond_user:
            q = q.join(Submission.user).filter(cond_user)

        cond_problem = self.parse(Problem.code, problem)
        if not cond_problem:
            q = q.join(Submission.problem).filter(cond_problem)

        cond_lang = self.parse(Language.key, language)
        if not cond_lang:
            q = q.join(Submission.language).filter(cond_lang)

        q = q.filter(self.parse(Submission.result, result))

        if a.data.total_objects == q.count():
            return q.all()
        submission_ids = list(map(attrgetter('id'), a.data.objects))
        qq = session.query(Submission.id).\
            filter(Submission.id.in_(submission_ids)).all()
        qq = list(map(itemgetter(0), qq))
        for submission in a.data.objects:
            if submission.id not in qq:
                session.add(Submission(submission))
        total_pages = a.data.total_pages

        apis = []
        tasks = []

        for _ in range(2, total_pages + 1):
            page += 1
            api = API()
            to_await = api.get_submissions(user=user, problem=problem,
                                           language=language, result=result,
                                           page=page)
            apis.append(api)
            tasks.append(to_await)
        await asyncio.gather(*tasks)
        for api in apis:
            if api.data.objects is None:
                continue
            submission_ids = list(map(attrgetter('id'), api.data.objects))
            qq = session.query(Submission.id).\
                filter(Submission.id.in_(submission_ids)).all()
            qq = list(map(itemgetter(0), qq))
            for submission in api.data.objects:
                if submission.id not in qq:
                    session.add(Submission(submission))
        session.commit()
        return q.all()

    async def get_submission(self, id: int) -> Submission:
        # Can't use this till i figure out whether or not to use api token
        raise NotImplementedError
        # pass

    async def get_latest_submissions(self, user: str, num: int) -> List[Submission]:
        a = API()
        ret = await a.get_latest_submission(user, num)
        return ret

    async def get_placement(self, username: str) -> int:
        a = API()
        return await a.get_placement(username)

    def get_handle(self, id: int, guild_id: int) -> str:
        q = session.query(Handle).\
            filter(Handle.id == id).\
            filter(Handle.guild_id == guild_id)
        if q.count():
            return q.first().handle

    def get_handle_user(self, handle: str, guild_id: int) -> int:
        q = session.query(Handle).\
            filter(Handle.handle == handle).\
            filter(Handle.guild_id == guild_id)
        if q.count():
            return q.first().id

    def get_random_problem(self, low: int = 1, high: int = 10) -> Problem:
        q = session.query(Problem)\
            .filter(Problem.points.between(low, high))\
            .order_by(func.random()).limit(1)
        if q.count():
            return q.first()

    def get_unsolved_problems(self, username: str, types: List[str] = [], low: int = 1, high: int = 50) -> Problem:
        # Does not find problems if you first
        # +update_problems
        # +gimme
        # This is cause calling the /problems api does not return is_organization_private
        # The original goal of is_organization_private filter is to prevent leaking problems
        sub_q = session.query(Submission, func.max(Submission.points))\
            .join(Submission.user)\
            .filter(User.username == username)\
            .group_by(Submission.problem_id).subquery()
        q = session.query(Problem)\
            .outerjoin(sub_q, Problem.code == sub_q.c.problem_id)\
            .filter(func.ifnull(sub_q.c.points, 0) < Problem.points)\
            .filter(Problem.points.between(low, high))\
            .filter(Problem.is_organization_private == 0)\
            .filter(Problem.is_public == 1)
        if types:
            conds = [Problem.types == _type for _type in types]
            q = q.filter(or_(*conds))
        return q.all()

    def get_attempted_problems(self, username: str, types: List[str], low: int = 1, high: int = 50) -> List[int]:
        sub_q = session.query(Problem.code)\
            .filter(Problem.points.between(low, high))\
            .filter(Problem.is_organization_private == 0)\
            .filter(Problem.is_public == 1)\
            .filter(or_(*[Problem.types == _type for _type in types])).subquery()
        q = session.query(func.max(Submission.points))\
            .join(sub_q, Submission.problem_id == sub_q.c.code)\
            .join(Submission.user)\
            .filter(User.username == username)\
            .filter(func.ifnull(Submission.points, 0) != 0)\
            .group_by(Submission.problem_id)
        return [point for (point,) in q.all()]

    def get_member_named(self, guild, name):
        result = None
        members = guild.members
        if len(name) > 5 and name[-5] == '#':
            # The 5 length is checking to see if #0000 is in the string,
            # as a#0000 has a length of 6, the minimum for a potential
            # discriminator lookup.
            potential_discriminator = name[-4:]

            # do the actual lookup and return if found
            # if it isn't found then we'll do a full name lookup below.
            result = utils.get(members, name=name[:-5], discriminator=potential_discriminator)
            if result is not None:
                return result

        name = name.casefold()

        def pred(m):
            return m.nick and m.nick.casefold() == name or m.name.casefold() == name

        return utils.find(pred, members)

    async def parseUser(self, ctx, arg):
        try:
            return await commands.MemberConverter().convert(ctx, arg)
        except MemberNotFound:
            return self.get_member_named(ctx.guild, arg)
            return None
