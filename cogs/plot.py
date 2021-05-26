import discord
from discord.ext import commands
import typing
from utils.query import Query
from discord.ext.commands.errors import BadArgument
from utils.db import (session, Contest as Contest_DB,
                      Submission as Submission_DB,
                      User as User_DB,
                      Problem as Problem_DB)
from utils.graph import (plot_type_radar, plot_type_bar, plot_rating,
                         plot_points, plot_solved)
from operator import itemgetter
from sqlalchemy import or_, orm, func
import asyncio
import io
import bisect


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
        """Plot problems solved over time"""
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        users = await asyncio.gather(*[query.get_user(username)
                                     for username in usernames])
        usernames = [user.username for user in users]
        for i in range(len(users)):
            if users[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        total_data = {}
        for username in usernames:
            q = session.query(Submission_DB)\
                .filter(Submission_DB._user == username)
            if q.count() == 0:
                await ctx.send(f"`{username}` does not have any cached submissions,caching now`")
                await query.get_submissions(username)

            q = session.query(func.min(Submission_DB.date))\
                .join(Problem_DB, Problem_DB.code == Submission_DB._code)\
                .filter(Submission_DB._user == username)\
                .filter(Submission_DB.points == Problem_DB.points)\
                .group_by(Submission_DB._code)
            dates = list(map(itemgetter(0), q.all()))
            dates.sort()
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
        """Plot point progression"""
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        users = await asyncio.gather(*[query.get_user(username)
                                     for username in usernames])
        usernames = [user.username for user in users]
        for i in range(len(users)):
            if users[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        total_data = {}
        for username in usernames:
            q = session.query(Submission_DB)\
                .options(orm.joinedload('problem'))\
                .join(User_DB, User_DB.username == Submission_DB._user,
                      aliased=True)\
                .filter(User_DB.username == username)\
                .order_by(Submission_DB.date)

            def calculate_points(points, fully_solved):
                b = 150 * (1 - 0.997**fully_solved)
                p = 0
                for i in range(min(100, len(points))):
                    p += (0.95**i) * points[i]
                return b + p

            submissions = q.all()
            if len(submissions) == 0:
                await ctx.send(f"`{username}` does not have any cached submissions,caching now`")
                await query.get_submissions(username)
                submissions = q.all()
            problems_ACed = dict()
            code_to_points = dict()

            points_arr = []
            data_to_plot = {}
            # O(N^2logN) :blobcreep:
            for submission in submissions:
                code = submission.problem[0].code
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
        """Plot rating progression"""
        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        users = await asyncio.gather(*[query.get_user(username)
                                     for username in usernames])
        usernames = [user.username for user in users]
        for i in range(len(users)):
            if users[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')
        if len(users) > 10:
            return await ctx.send('Too many users given, max 10')

        cond = [Contest_DB.rankings.contains(user.username) for user in users]
        q = session.query(Contest_DB).filter(or_(*cond))\
            .filter(Contest_DB.is_rated == 1)
        contests = q.all()

        def get_rating_change(rankings, users):
            ret = {}
            for ranking in rankings:
                for user in users:
                    if (user.username == ranking['user'] and
                       ranking['new_rating']):
                        ret[user.username] = ranking['new_rating']
            return ret

        data = {}
        data['users'] = [user.username for user in users]
        userPrevRating = {}
        for contest in contests:
            changes = get_rating_change(contest.rankings, users)
            data[contest.end_time] = []
            for user in users:
                if user.username in changes \
                        and (not peak or changes[user.username] >= userPrevRating.get(user.username, -9999)):
                    change = changes[user.username]
                    userPrevRating[user.username] = change
                    data[contest.end_time].append(change)
                else:
                    data[contest.end_time].append(None)
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
        """Graph problems solved by popular problem types"""
        # This is aids, pls fix

        usernames = list(usernames)

        query = Query()
        if usernames == []:
            usernames = [query.get_handle(ctx.author.id, ctx.guild.id)]

        users = await asyncio.gather(*[query.get_user(username)
                                     for username in usernames])
        for i in range(len(users)):
            if users[i] is None:
                return await ctx.send(f'{usernames[i]} does not exist on DMOJ')

        if len(users) > 6:
            return await ctx.send('Too many users given, max 6')

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

        def calculate_points(points: int):
            p = 0
            for i in range(min(100, len(points))):
                p += (0.95**i) * points[i]
            return p

        def to_points(problem):
            return problem.points

        max_percentage = 0

        for username in usernames:
            q = session.query(Submission_DB)\
                .filter(Submission_DB._user == username)
            if q.count() == 0:
                not_cached.append(username)
                await ctx.send(f"`{username}` does not have any cached submissions,caching now`")
                await query.get_submissions(username)

        for i, types in enumerate(important_types):
            total_problems = await query.get_problems(_type=types, cached=True)
            total_points = list(map(to_points, total_problems))
            total_points.sort(reverse=True)
            total_points = calculate_points(total_points)

            for username in usernames:
                problems = query.get_attempted_problems(username, types)

                points = list(map(to_points, problems))
                points.sort(reverse=True)

                points = calculate_points(points)
                if as_percent:
                    percentage = 100 * points / total_points
                else:
                    percentage = points
                max_percentage = max(max_percentage, percentage)
                data[labels[i]].append(percentage)

        print(data)

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
