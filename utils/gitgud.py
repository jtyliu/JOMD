from utils.api import API
from sqlalchemy import or_, func, desc
from utils.db import (session, Problem as Problem_DB,
                      Contest as Contest_DB,
                      Participation as Participation_DB,
                      User as User_DB, Submission as Submission_DB,
                      Organization as Organization_DB,
                      Language as Language_DB, Judge as Judge_DB,
                      Handle as Handle_DB, Gitgud as Gitgud_DB, CurrentGitgud as CurrentGitgud_DB, Json)
from typing import List
from sqlalchemy.sql import functions
import asyncio
from operator import itemgetter

class Gitgud:

    def get_point(self, handle, guild_id):
        q = session.query(func.sum(Gitgud_DB.point))\
            .filter(Gitgud_DB.handle == handle and Gitgud_DB.guild_id == guild_id)
        return q.first()[0]

    def get_all(self, handle, guild_id):
        q = session.query(Gitgud_DB)\
            .filter(Gitgud_DB.handle == handle and Gitgud_DB.guild_id == guild_id)\
            .order_by(desc(Gitgud_DB.time))
        return q.all()

    def insert(self, handle, guild_id, point, problem, time):
        db = Gitgud_DB()
        db.handle = handle
        db.guild_id = guild_id
        db.point = point
        db.problem_id = problem
        db.time = time
        session.add(db)
        session.commit()

    def get_current(self, handle, guild_id):
        result = session.query(CurrentGitgud_DB)\
            .filter(CurrentGitgud_DB.handle == handle \
                and CurrentGitgud_DB.guild_id == guild_id)
        return result.first()

    # set the user's current gitgud
    def bind(self, handle, guild_id, problem_id, point, time):
        result = self.get_current(handle, guild_id)
        if result is None:
            db = CurrentGitgud_DB()
            db.handle = handle
            db.guild_id = guild_id
            db.problem_id = problem_id
            db.point = point
            db.time = time
            session.add(db)
        else:
            result.problem_id = problem_id
            result.point = point
            result.time = time
        session.commit()

    # clear previous result
    def clear(self, handle, guild_id):
        result = self.get_current(handle, guild_id)
        result.problem_id = None
        session.commit()

    # delete entire table
    def wipe(self):
        session.query(CurrentGitgud_DB).delete()
