from utils.api import user_api, submission_api
from utils.db import DbConn
import math
import asyncio


class user:
    @staticmethod
    async def get_user(username):
        db = DbConn()
        db_user = db.count_submissions(username)
        if db_user:
            return {'username': db_user[0]}
        api_user = await user_api.get_user(username)
        return api_user

    @staticmethod
    async def get_submissions(username):
        total_submissions = await submission_api.get_submission_total(username)
        db = DbConn()
        cached_submissions = db.get_submissions(username)
        submissions_to_query = total_submissions-len(cached_submissions)
        pages_to_query = math.ceil(submissions_to_query/1000)
        submission_page = [None]*max(pages_to_query, 1)

        for page in range(pages_to_query):
            submission_page[page] = submission_api.get_submissions_page(
                username, page+1
            )

        if pages_to_query:
            submission_page = await asyncio.gather(*submission_page)
            api_submissions = []
            for submission in submission_page:
                api_submissions += submission

            api_submissions = api_submissions[:submissions_to_query]
            db.cache_submissions(api_submissions)
            return api_submissions+cached_submissions
        return cached_submissions
