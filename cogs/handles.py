from discord.ext import commands
import discord
from utils.query import Query
from utils.db import session, User as User_DB, Handle as Handle_DB
# import html
# import random
import asyncio


class Handles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def unlink(self, ctx):
        """Unlink your discord account with your dmoj account"""
        query = Query()
        if not query.get_handle(ctx.author.id, ctx.guild.id):
            await ctx.send('You are not linked with any user')
            return
        handle = session.query(Handle_DB)\
            .filter(Handle_DB.id == ctx.author.id)\
            .filter(Handle_DB.guild_id == ctx.guild.id).first()
        session.delete(handle)
        session.commit()
        await ctx.send(f'Unlinked you with handle {handle.handle}')


    @commands.command(usage='dmoj_handle')
    async def link(self, ctx, username: str):
        """Links your discord account to your dmoj account"""
        # Check if user exists
        query = Query()
        user = await query.get_user(username)

        if user is None:
            await ctx.send(f"{username} does not exist on DMOJ")
            return
        
        username = user.username

        if query.get_handle(ctx.author.id, ctx.guild.id):
            await ctx.send(
                '%s, your handle is already linked with %s.' %
                (ctx.author.mention,
                 query.get_handle(ctx.author.id, ctx.guild.id))
            )
            return

        if query.get_handle_user(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        problem = query.get_random_problem()

        if problem is None:
            await ctx.send('No problems are cached.. '
                           'Pls do something about that')
            # Will implement this
            # Just cache the problems and get a random one
            return

        await ctx.send(
            '%s, submit a compiler error to <https://dmoj.ca/problem/%s> '
            'within 60 seconds' % (ctx.author.mention, problem.code))
        await asyncio.sleep(60)

        submissions = await query.get_latest_submissions(username, 10)

        for submission in submissions:
            if (submission.result == 'CE' and
                    submission.problem[0].code == problem.code):
                user = await query.get_user(username)
                username = user.username

                handle = Handle_DB()
                handle.id = ctx.author.id
                handle.handle = username
                handle.user_id = user.id
                handle.guild_id = ctx.guild.id
                session.add(handle)
                session.commit()
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
        query = Query()
        user = await query.get_user(username)

        if user is None:
            await ctx.send(f'{username} does not exist on dmoj')
            return

        username = user.username

        if query.get_handle(member.id, ctx.guild.id):
            await ctx.send(
                '%s, this handle is already linked with %s.' %
                (ctx.author.mention, query.get_handle(member.id, ctx.guild.id)))
            return

        if query.get_handle_user(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        user = await query.get_user(username)
        username = user.username

        handle = Handle_DB()
        handle.id = member.id
        handle.handle = username
        handle.user_id = user.id
        handle.guild_id = ctx.guild.id
        session.add(handle)
        session.commit()
        return await ctx.send(
            "%s, %s is now linked with %s." %
            (ctx.author.name, member.name, username)
        )


def setup(bot):
    bot.add_cog(Handles(bot))
