from discord.ext import commands
# import typing
# from utils.query import user
# from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
# import html
# import random
import asyncio


class Handles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='dmoj username')
    async def link(self, ctx, username: str):
        """Links your discord account to your dmoj account"""
        db = DbConn()
        if db.get_handle_id(ctx.author.id, ctx.guild.id):
            await ctx.send(
                '%s, your handle is already linked with %s.' %
                (ctx.author.mention, db.get_handle_id(ctx.author.id)))
            return
        if db.get_handle_user_id(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        problem = db.get_random_problem()
        await ctx.send(
            '%s, submit a compiler error to <https://dmoj.ca/problem/%s> '
            'within 60 seconds' % (ctx.author.mention, problem.code))
        await asyncio.sleep(60)

        submissions = await submission_api.get_latest_submission(username, 10)

        for submission in submissions:
            if (submission.result == 'CE' and
                    submission.problem == problem.code):
                user_data = await user_api.get_user(username)
                username = user_data['username']
                db.cache_handle(ctx.author.id, username,
                                user_data['id'], ctx.guild.id)
                return await ctx.send(
                    "%s, you now have linked your account to %s." %
                    (ctx.author.name, username)
                )
        else:
            return await ctx.send('I don\'t see anything :monkey: '
                                  '(Failed to link accounts)')


def setup(bot):
    bot.add_cog(Handles(bot))
