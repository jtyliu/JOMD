from discord.ext import commands
from utils.query import Query
from utils.api import API
from utils.db import session, Problem as Problem_DB


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def check(self, ctx):
        """Check if the bot has been rate limited"""
        api = API()
        try:
            await api.get_judges()
            user = api.data.objects
            if user is None:
                await ctx.send('There is something wrong with the api, '
                               'please contact an admin')
            else:
                await ctx.send('Api is all good, move along.')
        except Exception as e:
            await ctx.send('Seems like I\'m getting cloud flared, rip. ' +
                           str(e))

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
        await ctx.send("The theoretical maximum number of points "
                       "you can achieve is %.2f" % total_points)
        return


def setup(bot):
    bot.add_cog(Meta(bot))
