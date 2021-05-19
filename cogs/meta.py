import discord
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
    @commands.command()
    async def stats(self, ctx):
        """Bot stats"""
        guildCount=len(self.bot.guilds)
        userCount=len(set(self.bot.get_all_members()))
        await ctx.send(f'Guilds: {guildCount}, Users: {userCount}')
    @commands.command()
    async def info(self, ctx):
        """Bot info"""
        embed=discord.Embed()\
            .set_author(name=self.bot.user,icon_url=self.bot.user.avatar_url)\
            .add_field(name="Documentation",value="[Documentation site](https://docs.xadelaide.cf/)",inline=False)\
            .add_field(name="Commands",value="[Command List](https://docs.xadelaide.cf/commands-1/)",inline=False)\
            .add_field(name="Invite",value="[Invite link](https://discord.com/api/oauth2/authorize?client_id=725004198466551880&permissions=73792&scope=bot)",inline=False)\
            .add_field(name="Support",value="[Server link](https://discord.gg/VEWFpgPhnz)",inline=False)
        await ctx.send(embed=embed)
            
    
    


def setup(bot):
    bot.add_cog(Meta(bot))
