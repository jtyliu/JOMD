from discord.ext import commands
from utils.query import Query
from utils.api import API
from utils.db import session, Problem as Problem_DB
import typing

class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='[username]')
    async def cache(self, ctx, username: typing.Optional[str] = None):
        """Caches the submissions of a user, will speed up other commands

        Use surround your username with '' if it can be interpreted as a number
        """
        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

        username = username.replace('\'', '')

        if username is None:
            return await ctx.send(f'No username given!')

        user = await query.get_user(username)
        if user is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = user.username

        try:
            msg = await ctx.send(f'Caching {username}\'s submissions')
        except Exception as e:
            await msg.edit(content='An error has occured, ' +
                                   'try caching again. Log: ' + e)
            return

        await query.get_submissions(username)

        return await msg.edit(content=f'{username}\'s submissions ' +
                                      'have been cached.')

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
    


def setup(bot):
    bot.add_cog(Meta(bot))
