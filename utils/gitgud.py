from sqlalchemy import func, desc
from utils.models import *


class Gitgud:

    def get_point(self, handle, guild_id):
        q = session.query(func.sum(Gitgud.point))\
            .filter(Gitgud.handle == handle)\
            .filter(Gitgud.guild_id == guild_id)
        return q.first()[0]

    def get_all(self, handle, guild_id):
        q = session.query(Gitgud)\
            .filter(Gitgud.handle == handle)\
            .filter(Gitgud.guild_id == guild_id)\
            .order_by(desc(Gitgud.time))
        return q.all()

    def insert(self, handle, guild_id, point, problem, time):
        db = Gitgud()
        db.handle = handle
        db.guild_id = guild_id
        db.point = point
        db.problem_id = problem
        db.time = time
        session.add(db)
        session.commit()

    def get_current(self, handle, guild_id):
        result = session.query(CurrentGitgud)\
            .filter(CurrentGitgud.handle == handle)\
            .filter(CurrentGitgud.guild_id == guild_id)
        return result.first()

    def has_solved(self, username, problem_code):
        q = session.query(User)\
            .filter(User.username == username)\
            .join(User.solved_problems)\
            .filter(Problem.code == problem_code)
        if q.count():
            return True
        return False

    # set the user's current gitgud
    def bind(self, handle, guild_id, problem_id, point, time):
        result = self.get_current(handle, guild_id)
        if result is None:
            db = CurrentGitgud()
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
        session.query(CurrentGitgud).delete()
