from discord import message
from discord.ext import commands
from utils.query import Query
from utils.api import API
from utils.db import session, Problem as Problem_DB

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command()
    async def stats(self, ctx):
        """Display cool dmoj stats that no one asked for"""
        problems = session.query(Problem_DB.points)\
            .order_by(Problem_DB.points.desc()).all()

        def tuple_first(data):
            return data[0]

        def calculate_points(points, fully_solved):
            b = 150 * (1 - 0.997**fully_solved)
            p = 0
            for i in range(min(100, len(points))):
                p += (0.95**i) * points[i]
            return b + p

        problems = list(map(tuple_first, problems))
        total_problems = len(problems)
        total_points = calculate_points(problems, total_problems)
        await ctx.send("The theoretical maximum number of points you can achieve is %.2f\n"
                       "There are %d public problems on DMOJ" % (total_points, total_problems))
        return


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
