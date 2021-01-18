from utils.api_new import API
from sqlalchemy import or_, func
from utils.db_new import (session, Problem as Problem_DB,
                          Contest as Contest_DB,
                          Participation as Participation_DB,
                          User as User_DB, Submission as Submission_DB,
                          Organization as Organization_DB,
                          Language as Language_DB, Judge as Judge_DB, Json)
from typing import List
from sqlalchemy.sql import functions


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
                        cond = key.like(f'%"{val}%"')
                    elif isinstance(val, list):
                        cond = or_(key.like(f'%"{v}%"') for v in val)
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
                           organization=None, search=None) -> List[Problem_DB]:
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
        q = session.query(Problem_DB).\
            filter(self.parse(Problem_DB.partial, partial)).\
            filter(self.parse(Problem_DB.group, group)).\
            filter(self.parse(Problem_DB.types, _type)).\
            filter(self.parse(Problem_DB.organizations, organization))

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

    async def get_problem(self, code) -> Problem_DB:
        q = session.query(Problem_DB).\
            filter(Problem_DB.code == code)
        if q.count():
            # time_limit check if it has a detailed row
            if q.first().time_limit is not None:
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
        if q.count():
            # solved_problems checks if it has detailed rows
            if len(q.first().solved_problems) != 0:
                return q.first()

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

        for participation in a.data.objects:
            qq = session.query(Participation_DB).\
                filter(Participation_DB.id == participation.id)
            if qq.count() == 0:
                session.add(Participation_DB(participation))

        while a.data.has_more:
            page += 1
            await a.get_participations(
                contest=contest, user=user, is_disqualified=is_disqualified,
                virtual_participation_number=virtual_participation_number,
                page=page
            )

            for participation in a.data.objects:
                qq = session.query(Participation_DB).\
                    filter(Participation_DB.id == participation.id)
                if qq.count() == 0:
                    session.add(Participation_DB(participation))
        session.commit()
        return q.all()

    async def get_submissions(self, user=None, problem=None, language=None,
                              result=None) -> List[Submission_DB]:
        a = API()
        page = 1
        await a.get_submissions(user=user, problem=problem, language=language,
                                result=result, page=page)

        cond_user = self.parse(func.lower(User_DB.username), func.lower(user))
        if not cond_user:
            cond_user = Submission_DB.user.any(cond_user)

        cond_problem = self.parse(Problem_DB.code, problem)
        if not cond_problem:
            cond_problem = Submission_DB.problem.any(cond_problem)

        cond_lang = self.parse(Language_DB.key, language)
        if not cond_lang:
            cond_lang = Submission_DB.language.any(cond_lang)

        q = session.query(Submission_DB).\
            filter(cond_user).\
            filter(cond_problem).\
            filter(cond_lang).\
            filter(self.parse(Submission_DB.result, result))
        print(q)
        if a.data.total_objects == q.count():
            return q.all()

        for submission in a.data.objects:
            qq = session.query(Submission_DB).\
                filter(Submission_DB.id == submission.id)
            if qq.count() == 0:
                session.add(Submission_DB(submission))

        while a.data.has_more:
            page += 1
            await a.get_submissions(user=user, problem=problem,
                                    language=language, result=result,
                                    page=page)

            for submission in a.data.objects:
                qq = session.query(Submission_DB).\
                    filter(Submission_DB.id == submission.id)
                if qq.count() == 0:
                    session.add(Submission_DB(submission))
        session.commit()
        return q.all()

    async def get_submission(self, id):
        # Can't use this till i figure out whether or not to use api token
        pass
    
    async def get_latest_submissions(self, user, num) -> List[Submission_DB]:
        a = API()
        ret = await a.get_latest_submission(user, num)
        return list(map(Submission_DB, ret))
    
    async def get_placement(self, username) -> int:
        a = API()
        return await a.get_placement(username)