import discord
from discord.ext import commands
import typing
from utils.query import user
from discord.ext.commands.errors import BadArgument
from utils.db import DbConn
from utils.graph import plot_radar, plot_bar
import asyncio
import io


class Plot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(brief='Graphs for analyzing DMOJ activity',
                    invoke_without_command=True)
    async def plot(self, ctx):
        """Plot various graphs"""
        await ctx.send_help('plot')

    def graph_type(argument) -> typing.Optional[str]:
        if '+' not in argument:
            raise BadArgument('No graph type provided')
        if argument == '+radar':
            return 'radar'
        if argument == '+bar':
            return 'bar'
        raise BadArgument('Graph type not known')

    def as_percentage(argument) -> typing.Optional[bool]:
        if argument == '+percent':
            return True
        if argument == '+percentage':
            return True
        if argument == '+point':
            return False
        raise BadArgument('Argument not known')

    @plot.command(usage='[+percent, +point] [+radar, +bar] [usernames]')
    async def type(self, ctx,
                   as_percent: typing.Optional[as_percentage]=False,
                   graph: typing.Optional[graph_type]='radar',
                   *usernames):
        """Graph problems solved by popular problem types"""

        usernames = list(usernames)

        db = DbConn()
        if usernames == []:
            usernames = [db.get_handle_id(ctx.author.id, ctx.guild.id)]

        datas = await asyncio.gather(*[user.get_user(username)
                                     for username in usernames])
        for i in range(len(datas)):
            if datas[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')

        if len(datas) > 6:
            return await ctx.send('Too many users given, max 6')

        usernames = [data['username'] for data in datas]

        important_types = [
            ['Data Structures'], ['Dynamic Programming'], ['Graph Theory'],
            ['String Algorithms'],
            ['Advanced Math', 'Geometry', 'Intermediate Math', 'Simple Math'],
            ['Ad Hoc'], ['Greedy Algorithms']
        ]
        labels = ['Data Structures', 'Dynamic Programming', 'Graph Theory',
                  'String Algorithms', 'Math', 'Ad Hoc', 'Greedy Algorithms']
        frequency = []

        for types in important_types:
            problems = db.get_problem_types(types)
            frequency.append(problems)

        data = {}
        data['group'] = []
        for label in labels:
            data[label] = []
        for username in usernames:
            data['group'].append(username)

        def calculate_points(points: int):
            p = 0
            for i in range(min(100, len(points))):
                p += (0.95**i)*points[i]
            return p

        def to_points(problem):
            return problem.points

        max_percentage = 0
        for i in range(len(important_types)):
            for username in usernames:
                types = important_types[i]
                problems = db.get_attempted_submissions_types(username, types)
                total_problems = db.get_problem_types(types)
                points = list(map(to_points, problems))
                total_points = list(map(to_points, total_problems))

                points.sort(reverse=True)
                total_points.sort(reverse=True)

                points = calculate_points(points)
                total_points = calculate_points(total_points)
                if as_percent:
                    percentage = 100*points/total_points
                else:
                    percentage = points
                max_percentage = max(max_percentage, percentage)
                data[labels[i]].append(percentage)

        if graph == 'radar':
            plot_radar(data, as_percent, max_percentage)
        elif graph == 'bar':
            plot_bar(data, as_percent, max_percentage)

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
