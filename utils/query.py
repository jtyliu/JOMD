from discord import utils
from discord.ext import commands
from discord.ext.commands.errors import MemberNotFound
from utils.api import API
from sqlalchemy import or_, func
from utils.db import (session, Problem as Problem_DB,
                      Contest as Contest_DB,
                      Participation as Participation_DB,
                      User as User_DB, Submission as Submission_DB,
                      Organization as Organization_DB,
                      Language as Language_DB, Judge as Judge_DB,
                      Handle as Handle_DB, Json)
from typing import List
from sqlalchemy.sql import functions
import asyncio
from operator import itemgetter


class Query:
    """
    Every object returned from this should be a DB object, not class object
    """

    def parse(self, key, val):
        cond = True
        if val is not None:
            try:
                if isinstance(key.property.columns[0].type, Json):
                    if isinstance(val, str):
                        cond = key.contains(val)
                    elif isinstance(val, list):
                        cond = or_(key.contains(v) for v in val)
                    elif isinstance(val, functions.Function):
                        cond = key == val
                    return cond
            except AttributeError:
                # cols which are relationship break this
                pass
            if isinstance(val, str):
                cond = key == val
            elif isinstance(val, list):
                cond = key.in_(val)
            elif isinstance(val, functions.Function):
                cond = key == val
        return cond

    async def get_pfp(self, username) -> str:
        return await API().get_pfp(username)

    async def get_user_description(self, username) -> str:
        return await API().get_user_description(username)

    async def get_languages(self, common_name=None) -> [Language_DB]:

        q = session.query(Language_DB).\
            filter(self.parse(Language_DB.common_name, common_name))
        if q.count():
            return q.all()
        a = API()
        await a.get_languages(common_name=common_name)
        languages = list(map(Language_DB, a.data.objects))
        for language in languages:
            session.add(language)
        session.commit()
        return languages

    async def get_problems(self, partial=None, group=None, _type=None,
                           organization=None, search=None, cached=False) -> List[Problem_DB]:

        q = session.query(Problem_DB).\
            filter(self.parse(Problem_DB.partial, partial)).\
            filter(self.parse(Problem_DB.group, group)).\
            filter(self.parse(Problem_DB.types, _type)).\
            filter(self.parse(Problem_DB.organizations, organization))
        if cached:
            return q.all()

        a = API()
        if search is not None:
            # Can't bother to implement something with db
            # maybe future me can do this
            await a.get_problems(partial=partial, group=group, _type=_type,
                                 organization=organization, search=search)
            return list(map(Problem_DB, a.data.objects))

        page = 1
        await a.get_problems(partial=partial, group=group, _type=_type,
                             organization=organization, search=search,
                             page=page)

        if a.data.total_objects == q.count():
            return q.all()

        for problem in a.data.objects:
            qq = session.query(Problem_DB).\
                filter(Problem_DB.code == problem.code)
            if qq.count() == 0:
                session.add(Problem_DB(problem))

        while a.data.has_more:
            page += 1
            await a.get_problems(partial=partial, group=group, _type=_type,
                                 organization=organization, search=search,
                                 page=page)

            for problem in a.data.objects:
                qq = session.query(Problem_DB).\
                    filter(Problem_DB.code == problem.code)
                if qq.count() == 0:
                    session.add(Problem_DB(problem))
        session.commit()
        return q.all()

    async def get_problem(self, code, cached=True) -> Problem_DB:
        q = session.query(Problem_DB).\
            filter(Problem_DB.code == code)
        if q.count() and cached:
            # has_rating check if it has a detailed row
            if q.first().short_circuit is not None:
                return q.first()

        a = API()
        await a.get_problem(code)
        if q.count():
            q.delete()
        session.add(Problem_DB(a.data.object))
        session.commit()
        return q.first()

    async def get_judges(self) -> List[Judge_DB]:
        # If this ever has more than 1 page, I'll eat a rock
        a = API()
        await a.get_judges()
        return list(map(Judge_DB, a.data.objects))

    async def get_contests(self, tag=None,
                           organization=None) -> List[Contest_DB]:
        a = API()

        page = 1
        await a.get_contests(tag=tag, organization=organization, page=page)

        q = session.query(Contest_DB).\
            filter(self.parse(Contest_DB.tags, tag)).\
            filter(self.parse(Contest_DB.organizations, organization))

        if a.data.total_objects == q.count():
            return q.all()

        for contest in a.data.objects:
            qq = session.query(Contest_DB).\
                filter(Contest_DB.key == contest.key)
            if qq.count() == 0:
                session.add(Contest_DB(contest))

        while a.data.has_more:
            page += 1
            await a.get_contests(tag=tag, organization=organization, page=page)

            for contest in a.data.objects:
                qq = session.query(Contest_DB).\
                    filter(Contest_DB.key == contest.key)
                if qq.count() == 0:
                    session.add(Contest_DB(contest))
        session.commit()
        return q.all()

    async def get_contest(self, key) -> Contest_DB:
        q = session.query(Contest_DB).\
            filter(Contest_DB.key == key)
        if q.count():
            # is_rated checks if it has detailed rows
            if q.first().is_rated is not None:
                return q.first()
        a = API()
        await a.get_contest(key)
        if q.count():
            q.delete()
        session.add(Contest_DB(a.data.object))
        session.commit()
        return q.first()

    async def get_users(self, organization=None) -> List[User_DB]:
        a = API()

        page = 1
        await a.get_users(organization=organization, page=page)

        q = session.query(User_DB).\
            filter(self.parse(User_DB.organizations, organization))

        if a.data.total_objects == q.count():
            return q.all()

        for user in a.data.objects:
            qq = session.query(User_DB).\
                filter(User_DB.id == user.id)
            if qq.count() == 0:
                session.add(User_DB(user))

        while a.data.has_more:
            page += 1
            await a.get_users(organization=organization, page=page)

            for user in a.data.objects:
                qq = session.query(User_DB).\
                    filter(User_DB.id == user.id)
                if qq.count() == 0:
                    session.add(User_DB(user))
        session.commit()
        return q.all()

    async def get_user(self, username) -> User_DB:
        q = session.query(User_DB).\
            filter(func.lower(User_DB.username) == func.lower(username))
        # if q.count():
        #     # solved_problems checks if it has detailed rows
        #     if len(q.first().solved_problems) != 0:
        #         return q.first()

        a = API()
        await a.get_user(username)
        if q.count():
            # Needs to be fetch, the default (evaluate) is not able to eval
            # the query
            q.delete(synchronize_session='fetch')
        session.add(User_DB(a.data.object))
        session.commit()
        return q.first()

    async def get_participations(
        self, contest=None, user=None, is_disqualified=None,
        virtual_participation_number=None
    ) -> List[Participation_DB]:
        a = API()

        page = 1
        await a.get_participations(
            contest=contest, user=user, is_disqualified=is_disqualified,
            virtual_participation_number=virtual_participation_number,
            page=page
        )

        # why the hell are these names so long?
        cond_contest = self.parse(Contest_DB.key, contest)
        if not cond_contest:
            cond_contest = Participation_DB.contest.any(cond_contest)

        cond_user = self.parse(func.lower(User_DB.username), func.lower(user))
        if not cond_user:
            cond_user = Participation_DB.user.any(cond_user)

        q = session.query(Participation_DB).\
            filter(cond_contest).\
            filter(cond_user).\
            filter(self.parse(Participation_DB.is_disqualified,
                              is_disqualified)).\
            filter(self.parse(Participation_DB.virtual_participation_number,
                              virtual_participation_number))

        if a.data.total_objects == q.count():
            return q.all()

        def get_id(participation):
            return participation.id

        participation_id = list(map(get_id, a.data.objects))
        qq = session.query(Submission_DB.id).\
            filter(Submission_DB.id.in_(participation_id)).all()
        qq = list(map(itemgetter(0), qq))
        for submission in a.data.objects:
            if submission.id not in qq:
                session.add(Submission_DB(submission))
        total_pages = a.data.total_pages
        for participation in a.data.objects:
            if participation.id not in participation_id:
                session.add(Participation_DB(participation))

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
            participation_id = list(map(get_id, api.data.objects))
            qq = session.query(Submission_DB.id).\
                filter(Submission_DB.id.in_(participation_id)).all()
            qq = list(map(itemgetter(0), qq))
            for submission in api.data.objects:
                if submission.id not in qq:
                    session.add(Submission_DB(submission))
            total_pages = api.data.total_pages
            for participation in api.data.objects:
                if participation.id not in participation_id:
                    session.add(Participation_DB(participation))
        session.commit()
        return q.all()

    async def get_submissions(self, user=None, problem=None, language=None,
                              result=None) -> List[Submission_DB]:
        # This function is the only one which might take a while to run and
        # has data that is added reguarly. asyncio.gather can apply to all
        # functions but this one is the only one which really needs it
        a = API()
        page = 1
        import time
        start = time.time()
        await a.get_submissions(user=user, problem=problem, language=language,
                                result=result, page=page)
        print("Done Api Call", time.time() - start)
        start = time.time()
        q = session.query(Submission_DB)
        q = q.filter(Submission_DB._user == user)

        cond_user = self.parse(func.lower(User_DB.username), func.lower(user))
        if not cond_user:
            q = q.join(User_DB, cond_user, aliased=True)

        cond_problem = self.parse(Problem_DB.code, problem)
        if not cond_problem:
            q = q.join(Problem_DB, cond_problem, aliased=True)

        cond_lang = self.parse(Language_DB.key, language)
        if not cond_lang:
            q = q.join(Language_DB, cond_lang, aliased=True)

        q = q.filter(self.parse(Submission_DB.result, result))

        if a.data.total_objects == q.count():
            return q.all()

        def get_id(submission):
            return submission.id

        submission_ids = list(map(get_id, a.data.objects))
        qq = session.query(Submission_DB.id).\
            filter(Submission_DB.id.in_(submission_ids)).all()
        qq = list(map(itemgetter(0), qq))
        for submission in a.data.objects:
            if submission.id not in qq:
                session.add(Submission_DB(submission))
        total_pages = a.data.total_pages

        apis = []
        to_gather = []

        async def get_submission(api, user, problem, language, result, page):
            try:
                api.get_submissions(user=user, problem=problem,
                                    language=language,
                                    result=result, page=page)
            except Exception:
                # Sometimes when caching a user with many pages one might not return correctly
                # this will silently return nothing
                # Perhaps I should implement some sort of error catching in the cogs
                pass

        for _ in range(2, total_pages + 1):
            page += 1
            api = API()
            to_await = api.get_submissions(user=user, problem=problem,
                                           language=language, result=result,
                                           page=page)
            apis.append(api)
            to_gather.append(to_await)
        await asyncio.gather(*to_gather)
        for api in apis:
            if api.data.objects is None:
                continue
            submission_ids = list(map(get_id, api.data.objects))
            qq = session.query(Submission_DB.id).\
                filter(Submission_DB.id.in_(submission_ids)).all()
            qq = list(map(itemgetter(0), qq))
            for submission in api.data.objects:
                if submission.id not in qq:
                    session.add(Submission_DB(submission))
        session.commit()
        return q.all()

    async def get_submission(self, id):
        # Can't use this till i figure out whether or not to use api token
        pass

    async def get_latest_submissions(self, user, num) -> List[Submission_DB]:
        a = API()
        ret = await a.get_latest_submission(user, num)
        return ret

    async def get_placement(self, username) -> int:
        a = API()
        return await a.get_placement(username)

    def get_handle(self, id, guild_id):
        q = session.query(Handle_DB).\
            filter(Handle_DB.id == id).\
            filter(Handle_DB.guild_id == guild_id)
        if q.count():
            return q.first().handle

    def get_handle_user(self, handle, guild_id):
        q = session.query(Handle_DB).\
            filter(Handle_DB.handle == handle).\
            filter(Handle_DB.guild_id == guild_id)
        if q.count():
            return q.first().id

    def get_random_problem(self, low=1, high=10):
        q = session.query(Problem_DB)\
            .filter(Problem_DB.points.between(low, high))\
            .order_by(func.random()).limit(1)
        if q.count():
            return q.first()

    def get_unsolved_problems(self, username, types, low=1, high=50):
        # Does not find problems if you first
        # +update_problems
        # +gimme
        # This is cause calling the /problems api does not return is_organization_private
        # The original goal of is_organization_private filter is to prevent leaking problems
        conds = [Problem_DB.types.contains(_type) for _type in types]
        sub_q = session.query(Submission_DB, func.max(Submission_DB.points))\
            .filter(Submission_DB._user == username)\
            .group_by(Submission_DB._code).subquery()
        q = session.query(Problem_DB)\
            .join(sub_q, Problem_DB.code == sub_q.c._code, isouter=True)\
            .filter(func.ifnull(sub_q.c.points, 0) < Problem_DB.points)\
            .filter(or_(*conds))\
            .filter(Problem_DB.points.between(low, high))\
            .filter(Problem_DB.is_organization_private == 0)\
            .filter(Problem_DB.is_public == 1)
        return q.all()

    def get_attempted_problems(self, username, types):
        conds = [Problem_DB.types.contains(_type) for _type in types]
        sub_q = session.query(Submission_DB, func.max(Submission_DB.points))\
            .filter(Submission_DB._user == username)\
            .group_by(Submission_DB._code).subquery()
        q = session.query(Problem_DB)\
            .join(sub_q, Problem_DB.code == sub_q.c._code, isouter=True)\
            .filter(func.ifnull(sub_q.c.points, 0) != 0)\
            .filter(or_(*conds))
        return q.all()

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
