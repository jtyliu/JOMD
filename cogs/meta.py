from discord.ext import commands
from utils.query import Query


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def check(self, ctx):
        """Check if the bot has been rate limited"""
        query = Query()
        user = await query.get_user('JoshuaL')
        if user is None:
            await ctx.send('There is something wrong with the api, '
                           'please contact an admin')
        else:
            await ctx.send('Api is all good, move along.')


def setup(bot):
    bot.add_cog(Meta(bot))
