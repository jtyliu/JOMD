from discord.ext import commands
from pathlib import Path
import discord
from utils.api import problem_api
from utils.db import DbConn
import math


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def gib_role(self, ctx, role: discord.Role):
        # Yes, this might look like a backdoor but I can explain,
        # Jack is baf
        await ctx.author.add_roles(role)

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
    async def cache_problems(self, ctx):
        """Update db and cache all new problems"""
        db = DbConn()
        await ctx.send("Caching Problems...")
        total = await problem_api.get_problem_total()
        pages = math.ceil(total/1000)
        total_cached = 0
        for page in range(1, pages+1):
            problems = await problem_api.get_problems(page)
            for problem in problems:
                if db.get_problem(problem.code):
                    continue
                problem = await problem_api.get_problem(problem.code)
                if problem.is_public:
                    db.cache_problem(problem)
                    total_cached += 1
        await ctx.send(f"{total_cached} problems added to db.")


def setup(bot):
    bot.add_cog(Admin(bot))
