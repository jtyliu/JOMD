from utils.api import user_api
from utils.db import DbConn

class user:
    @staticmethod
    async def get_user(username):
        db = DbConn()
        db_user = db.count_submissions(username)
        if db_user:
            return db_user
        api_user = await user_api.get_user(username)
        return api_user
        