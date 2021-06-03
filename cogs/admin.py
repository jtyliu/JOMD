from utils.api import ObjectNotFound
from discord.ext import commands
from pathlib import Path
from utils.db import (session, Contest as Contest_DB,
                      Problem as Problem_DB, Submission as Submission_DB)
from utils.query import Query
from operator import itemgetter
import time
import logging
logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        server = ctx.guild.name
        user = ctx.author
        command = ctx.command
        logger.info('+%s used by %s in %s', command, user, server)

    @commands.command()
    async def reload_all(self, ctx):
        '''
        Reload a module
        '''
        try:
            cogs = [file.stem for file in Path('cogs').glob('*.py')]
            for extension in cogs:
                self.bot.reload_extension(f'cogs.{extension}')
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('All cogs have been reloaded')

    @commands.command()
    async def force(self, ctx, _type, key):
        '''
        Force a recache of a problem, or contest
        '''
        if _type.lower() == 'contest':
            q = session.query(Contest_DB).filter(Contest_DB.key == key)
            if q.count() == 0:
                await ctx.send(f'There is no contests with the key {key} '
                               f'cached. Will try fetching contest')
            else:
                q.delete()
                session.commit()
            query = Query()
            try:
                await query.get_contest(key)
            except ObjectNotFound:
                return await ctx.send('Contest not found')
            await ctx.send(f'Recached contest {key}')
        if _type.lower() == 'problem':
            q = session.query(Problem_DB).filter(Problem_DB.code == key)
            if q.count() == 0:
                await ctx.send(f'There is no problems with the key {key} '
                               f'cached. Will try fetching problem')
            else:
                q.delete()
                session.commit()
            query = Query()
            try:
                await query.get_problem(key)
            except ObjectNotFound:
                return await ctx.send('Problem not found')
            await ctx.send(f'Recached problem {key}')

    @commands.command()
    async def cache_contests(self, ctx):
        '''Individually caches every contest'''
        query = Query()
        msg = await ctx.send('Caching...')
        contests = await query.get_contests()
        for contest in contests:
            await query.get_contest(contest.key)
        return await msg.edit(content=f'Cached {len(contests)} contests')

    @commands.command()
    async def update_problems(self, ctx):
        '''Update all problems in db (For when Nick nukes problems)'''
        msg = await ctx.send('Updating...')
        session.query(Problem_DB).delete()
        session.commit()
        query = Query()
        await query.get_problems()
        return await msg.edit(content='Updated all problems')


def setup(bot):
    bot.add_cog(Admin(bot))
