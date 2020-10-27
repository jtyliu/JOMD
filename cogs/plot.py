import discord
from discord.ext import commands
import typing
from utils.query import user
from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
from utils.graph import plot_radar
import html
import random
import asyncio
import io

class Plot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.group(brief='Graphs for analyzing DMOJ activity',
                    invoke_without_command=True)
    async def plot(self, ctx):
        "Plot various graphs"
        await ctx.send_help('plot')
    
    @plot.command(usage='[usernames]')
    async def type(self, ctx, *usernames):
        usernames = list(usernames)
        datas = await asyncio.gather(*[user.get_user(username) for username in usernames])
        for i in range(len(datas)):
            if datas[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')
        
        if len(datas) > 6:
            return await ctx.send('Too many users given, max 6')

        usernames = [data['username'] for data in datas]

        db = DbConn()
        important_types = [['Data Structures'], ['Dynamic Programming'], ['Graph Theory'], ['String Algorithms'], ['Advanced Math', 'Geometry', 'Intermediate Math', 'Simple Math'], ['Ad Hoc'], ['Greedy Algorithms']]
        labels = ['Data Structures', 'Dynamic Programming', 'Graph Theory', 'String Algorithms', 'Math', 'Ad Hoc', 'Greedy Algorithms']
        frequency = []

        for types in important_types:
            problems = db.get_problem_types(types)
            frequency.append(len(problems))
        
        data = {}
        data['group'] = []
        for label in labels:
            data[label] = []
        for username in usernames:
            data['group'].append(username)
        
        max_percentage = 0
        for i in range(len(important_types)):
            for username in usernames:
                types = important_types[i]
                problems = db.get_solved_problems_types(username, types)
                percentage = 100*len(problems)/frequency[i]
                max_percentage = max(max_percentage, percentage)
                data[labels[i]].append(percentage)

        plot_radar(data, max_percentage)
        with open('./graphs/plot.png', 'rb') as file:
            file = discord.File(io.BytesIO(file.read()), filename='plot.png')
        embed = discord.Embed(
                    title='Problem types solved',
                    description=' '.join(usernames),
                    color=0xfcdb05,
        )
        embed.set_image(url=f'attachment://plot.png',)

        return await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Plot(bot))
