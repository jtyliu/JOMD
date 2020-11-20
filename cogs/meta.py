import discord
from discord.ext import commands
import typing
from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
from utils.jomd_common import str_not_int, point_range, parse_gimme
import html
import random


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def check(self, ctx):
        """Check if the bot has been rate limited"""
        user = await user_api.get_user('JoshuaL')
        if user is None:
            await ctx.send('There is something wrong with the api, '
                           'please contact an admin')
        else:
            await ctx.send('Api is all good, move along.')


def setup(bot):
    bot.add_cog(Meta(bot))
