from discord.ext import commands
from pathlib import Path
import discord
# from utils.api import problem_api
# from utils.db import DbConn
from utils.db import (session, Contest as Contest_DB,
                      Problem as Problem_DB, Submission as Submission_DB)
from utils.query import Query
from utils.api import API
import math
from operator import itemgetter
import time


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def reload_all(self, ctx):
        """Reload a module"""
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
        """Force a recache of a problem, or contest"""
        if _type.lower() == "contest":
            q = session.query(Contest_DB).filter(Contest_DB.key == key)
            if q.count() == 0:
                await ctx.send(f"There is no contests with the key {key} "
                               f"cached. Will try fetching contest")
            else:
                q.delete()
                session.commit()
            query = Query()
            await query.get_contest(key)
            await ctx.send(f"Recached contest {key}")
        if _type.lower() == "problem":
            q = session.query(Problem_DB).filter(Problem_DB.code == key)
            if q.count() == 0:
                await ctx.send(f"There is no contests with the key {key} "
                               f"cached. Will try fetching contest")
            else:
                q.delete()
                session.commit()
            query = Query()
            await query.get_problem(key)
            await ctx.send(f"Recached contest {key}")

    @commands.command()
    async def cache_problems(self, ctx):
        """Cache all new problems"""
        query = Query()
        msg = await ctx.send("Caching...")
        count = 0
        problems = await query.get_problems()
        for problem in problems:
            await query.get_problem(problem.code)
            count += 1
        return await msg.edit(content=f"Cached {count} problems")

    @commands.command()
    async def update_problems(self, ctx):
        """Update all problems in db"""
        msg = await ctx.send("Updating...")
        session.query(Problem_DB).delete()
        session.commit()
        query = Query()
        await query.get_problems()
        return await msg.edit(content=f"Updated all problems")

    @commands.command()
    async def update_submissions(self, ctx):
        """Updates the submissions of every user in db (Warning! Slow!)"""
        q = session.query(Submission_DB._user).distinct(Submission_DB._user)
        usernames = list(map(itemgetter(0), q.all()))
        await ctx.send(f"Recaching submissions for {len(usernames)}"
                       f" users. This will take a long time (perhaps hours).")
        session.query(Submission_DB).delete()
        session.commit()

        query = Query()
        count = 0
        msg = await ctx.send(f"{count}/{len(usernames)} users cached...")
        for username in usernames:
            await msg.edit(content=f"{count}/{len(usernames)} users cached..."
                                   f" ({username})")
            await query.get_submissions(username)
            time.sleep(30) # PLS DON'T GET CLOUDFLARED
            count += 1
        await msg.edit(content=f"{len(usernames)} users cache. Done!")


def setup(bot):
    bot.add_cog(Admin(bot))
