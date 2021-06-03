import discord
from discord.ext import commands
from utils.query import Query
from utils.api import API
from utils.db import session, Problem as Problem_DB, Submission as Submission_DB
import typing


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='[username]')
    async def cache(self, ctx, username: typing.Optional[str] = None):
        '''Caches the submissions of a user, will speed up other commands

        Use surround your username with '' if it can be interpreted as a number
        '''
        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

        username = username.replace('\'', '')

        if username is None:
            return await ctx.send('No username given!')

        user = await query.get_user(username)
        if user is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = user.username

        msg = await ctx.send(f'Caching {username}\'s submissions')
        session.query(Submission_DB).filter(Submission_DB._user == username).delete()
        await query.get_submissions(username)
        return await msg.edit(content=f'{username}\'s submissions ' +
                                      'have been cached')

    @commands.command()
    async def check(self, ctx):
        '''Check if the bot has been rate limited'''
        api = API()
        try:
            await api.get_user('JoshuaL')
            user = api.data.object
            if user is None:
                await ctx.send('There is something wrong with the api, '
                               'please contact an admin')
            else:
                await ctx.send('Api is all good, move along')
        except Exception as e:
            await ctx.send('Seems like I\'m getting cloud flared, rip. Error: ' +
                           str(e))

    @commands.command()
    async def info(self, ctx):
        '''Bot info'''
        guildCount = len(self.bot.guilds)
        userCount = len(set(self.bot.get_all_members()))
        embed = discord.Embed(color=0xffff00)\
            .set_author(name=self.bot.user, icon_url=self.bot.user.avatar_url)\
            .add_field(name='Guilds:', value=guildCount, inline=True)\
            .add_field(name='Users:', value=userCount, inline=True)\
            .add_field(name='Invite',
                       value='[Invite link](https://discord.com/api/oauth2/' +
                       'authorize?client_id=725004198466551880&scope=bot)',
                       inline=False)\
            .add_field(name='Github',
                       value='[Github link](https://github.com/JoshuaTianYangLiu/JOMD)',
                       inline=False)\
            .add_field(name='Support', value='[Server link](https://discord.gg/VEWFpgPhnz)', inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx):
        '''Display cool dmoj stats that no one asked for'''
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
        await ctx.send('The theoretical maximum number of points you can achieve is %.2f\n'
                       'There are %d public problems on DMOJ' % (total_points, total_problems))


def setup(bot):
    bot.add_cog(Meta(bot))
