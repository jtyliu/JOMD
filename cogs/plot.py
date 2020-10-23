import discord
from discord.ext import commands
import typing
from utils.apiordb import user
from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
import html
import random

class Plot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def plot(self, ctx):
        "Plot various graphs"
        return ctx.send_help(plot)
    
    @plot.commands(usage='')
    async def type(self, ctx, *usernames):
        usernames = list(usernames)




def setup(bot):
    bot.add_cog(Plot(bot))
