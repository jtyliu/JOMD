from discord.ext import commands
import discord
# import typing
# from utils.query import user
# from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.query import user
from utils.db import DbConn
# import html
# import random
import asyncio


class Handles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def unlink(self, ctx):
        """Unlink your discord account with your dmoj account"""
        db = DbConn()
        if not db.get_handle_id(ctx.author.id, ctx.guild.id):
            await ctx.send('You are not linked with any user')
            return

    @commands.command(usage='dmoj_handle')
    async def link(self, ctx, username: str):
        """Links your discord account to your dmoj account"""
        # Check if user exists
        data = await user.get_user(username)

        if data is None:
            return

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

    @commands.command(name='set', usage='discord_account dmoj_handle')
    @commands.has_role('Admin')
    async def _set(self, ctx, member: discord.Member, username: str):
        """Manually link two accounts together"""
        data = await user.get_user(username)

        if data is None:
            await ctx.send(f'{username} does not exist on dmoj')
            return

        db = DbConn()

        if db.get_handle_id(member.id, ctx.guild.id):
            await ctx.send(
                '%s, this handle is already linked with %s.' %
                (ctx.author.mention, db.get_handle_id(member.id)))
            return

        if db.get_handle_user_id(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        user_data = await user_api.get_user(username)
        username = user_data['username']
        db.cache_handle(member.id, username,
                        user_data['id'], ctx.guild.id)
        return await ctx.send(
            "%s, %s is now linked with %s." %
            (ctx.author.name, member.name, username)
        )


def setup(bot):
    bot.add_cog(Handles(bot))
