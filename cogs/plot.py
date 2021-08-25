from utils.api import ObjectNotFound
import discord
from discord.ext import commands
import typing
from utils.query import Query
from discord.ext.commands.errors import BadArgument
from utils.models import *
from utils.graph import (plot_type_radar, plot_type_bar, plot_rating,
                         plot_points, plot_solved)
from utils.jomd_common import calculate_points
from operator import attrgetter, itemgetter
from sqlalchemy import or_, orm, func
import asyncio
import io
import bisect
import logging
logger = logging.getLogger(__name__)


class Plot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(brief='Graphs for analyzing DMOJ activity',
                    invoke_without_command=True)
    async def plot(self, ctx):
        '''Plot various graphs'''
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
        if argument == '+points':
            return False
        raise BadArgument('Argument not known')

    def plot_peak(argument) -> typing.Optional[bool]:
        if argument == '+peak':
            return True
        if argument == '+max':
            return True
        raise BadArgument('Argument not known')

    @plot.command(usage='[usernames]')
    async def solved(self, ctx, *usernames):
        '''Plot problems solved over time'''
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        try:
            users = await asyncio.gather(*[query.get_user(username)
                                         for username in usernames])
        except ObjectNotFound:
            return await ctx.send('User not found')

        user_ids = [user.id for user in users]
        usernames = [user.username for user in users]
        for user, username in zip(users, usernames):
            if user is None:
                return await ctx.send(f'{username} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        total_data = {}
        for user_id, username in zip(user_ids, usernames):
            q = session.query(func.count(Submission.id))\
                .filter(Submission.user_id == user_id)
            if q.scalar() == 0:
                await ctx.send(f'`{username}` does not have any cached submissions, caching now')
                await query.get_submissions(username)

            q = session.query(func.min(Submission.date)).\
                join(Problem.submissions).\
                filter(Submission.user_id == user_id).\
                filter(Submission.points == Problem.points).\
                group_by(Submission.problem_id).\
                order_by(func.min(Submission.date))

            dates = [date for (date,) in q]
            data_to_plot = {}
            cnt = 0
            for date in dates:
                cnt += 1
                data_to_plot[date] = cnt
            total_data[username] = data_to_plot

        plot_solved(total_data)

        with open('./graphs/plot.png', 'rb') as file:
            file = discord.File(io.BytesIO(file.read()), filename='plot.png')
        embed = discord.Embed(
            title='Problems Solved',
            color=0xfcdb05,
        )
        embed.set_image(url='attachment://plot.png')

        return await ctx.send(embed=embed, file=file)

    @plot.command(usage='[usernames]')
    async def points(self, ctx, *usernames):
        '''Plot point progression'''
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        try:
            users = await asyncio.gather(*[query.get_user(username)
                                         for username in usernames])
        except ObjectNotFound:
            return await ctx.send('User not found')

        user_ids = [user.id for user in users]
        usernames = [user.username for user in users]
        for user, username in zip(users, usernames):
            if user is None:
                return await ctx.send(f'{username} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        total_data = {}
        for user_id, username in zip(user_ids, usernames):
            q = session.query(Submission)\
                .options(orm.joinedload('problem'))\
                .filter(Submission.user_id == user_id)\
                .order_by(Submission.date)

            submissions = q.all()
            if len(submissions) == 0:
                await ctx.send(f'`{username}` does not have any cached submissions, caching now')
                await query.get_submissions(username)
                submissions = q.all()
            problems_ACed = dict()
            code_to_points = dict()

            points_arr = []
            data_to_plot = {}
            # O(N^2logN) :blobcreep:
            for submission in submissions:
                code = submission.problem.code
                points = submission.points
                result = submission.result

                if points is not None:
                    if result == 'AC':
                        problems_ACed[code] = 1
                    if code not in code_to_points:
                        # log N search, N insert
                        code_to_points[code] = points
                        bisect.insort(points_arr, points)
                    elif points > code_to_points[code]:
                        # N remove, log N search, N insert
                        points_arr.remove(code_to_points[code])
                        code_to_points[code] = points
                        bisect.insort(points_arr, points)
                    cur_points = calculate_points(points_arr[::-1],
                                                  len(problems_ACed))
                    data_to_plot[submission.date] = cur_points
            total_data[username] = data_to_plot

        plot_points(total_data)

        with open('./graphs/plot.png', 'rb') as file:
            file = discord.File(io.BytesIO(file.read()), filename='plot.png')
        embed = discord.Embed(
            title='Point Progression',
            color=0xfcdb05,
        )
        embed.set_image(url='attachment://plot.png')

        return await ctx.send(embed=embed, file=file)

    @plot.command(usage='[+peak] [usernames]')
    async def rating(self, ctx, peak: typing.Optional[plot_peak] = False, *usernames):
        '''Plot rating progression'''
        # NOTE: The function does not work, https://github.com/DMOJ/online-judge/pull/1743 needs to be merged
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        try:
            users = await asyncio.gather(*[query.get_user(username)
                                         for username in usernames])
        except ObjectNotFound:
            return await ctx.send('User not found')

        user_ids = [user.id for user in users]
        usernames = [user.username for user in users]
        for user, username in zip(users, usernames):
            if user is None:
                return await ctx.send(f'{username} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        q = session.query(User.username, Participation.new_rating, Contest.end_time).\
            join(Participation.contest).\
            join(Participation.user).\
            filter(Participation.user_id.in_(user_ids)).\
            filter(Participation.new_rating != None).\
            order_by(Contest.end_time)
        data = q.all()
        print(data)
        plot_rating(data)
        with open('./graphs/plot.png', 'rb') as file:
            file = discord.File(io.BytesIO(file.read()), filename='plot.png')
        embed = discord.Embed(
            title='Contest Rating',
            color=0xfcdb05,
        )
        embed.set_image(url='attachment://plot.png')

        return await ctx.send(embed=embed, file=file)

    @plot.command(usage='[+percent, +point] [+radar, +bar] [usernames]')
    async def type(self, ctx,
                   as_percent: typing.Optional[as_percentage] = True,
                   graph: typing.Optional[graph_type] = 'radar',
                   *usernames):
        '''Graph problems solved by popular problem types'''
        # This is aids, pls fix

        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        try:
            users = await asyncio.gather(*[query.get_user(username)
                                         for username in usernames])
        except ObjectNotFound:
            return await ctx.send('User not found')

        for i in range(len(users)):
            if users[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')

        if len(users) > 6:
            return await ctx.send('Too many users given, max 6')

        user_ids = [data.id for data in users]
        usernames = [data.username for data in users]

        important_types = [
            ['Data Structures'], ['Dynamic Programming'], ['Graph Theory'],
            ['String Algorithms'],
            ['Advanced Math', 'Geometry', 'Intermediate Math', 'Simple Math'],
            ['Ad Hoc'], ['Greedy Algorithms']
        ]
        labels = ['Data Structures', 'Dynamic Programming', 'Graph Theory',
                  'String Algorithms', 'Math', 'Ad Hoc', 'Greedy Algorithms']

        data = {}
        data['group'] = []
        for label in labels:
            data[label] = []
        for username in usernames:
            data['group'].append(username)

        def calculate_partial_points(points: int):
            p = 0
            for i in range(min(100, len(points))):
                p += (0.95**i) * points[i]
            return p

        max_percentage = 0

        for user_id, username in zip(user_ids, usernames):
            q = session.query(Submission)\
                .filter(Submission.user_id == user_id)
            if q.count() == 0:
                await ctx.send(f'`{username}` does not have any cached submissions, caching now')
                await query.get_submissions(username)

        for i, types in enumerate(important_types):
            total_problems = await query.get_problems(_type=types, cached=True)
            total_points = list(map(attrgetter('points'), total_problems))
            total_points.sort(reverse=True)
            total_points = calculate_partial_points(total_points)

            for username in usernames:
                points = query.get_attempted_problems(username, types)
<<<<<<< HEAD
=======

>>>>>>> master
                points.sort(reverse=True)

                points = calculate_partial_points(points)
                if as_percent:
                    percentage = 100 * points / total_points
                else:
                    percentage = points
                max_percentage = max(max_percentage, percentage)
                data[labels[i]].append(percentage)

        logger.debug('plot type data: %s', data)

        if graph == 'radar':
            plot_type_radar(data, as_percent, max_percentage)
        elif graph == 'bar':
            plot_type_bar(data, as_percent)

        with open('./graphs/plot.png', 'rb') as file:
            file = discord.File(io.BytesIO(file.read()), filename='plot.png')
        embed = discord.Embed(
            title='Problem types solved',
            color=0xfcdb05,
        )
        embed.set_image(url='attachment://plot.png')

        return await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Plot(bot))
