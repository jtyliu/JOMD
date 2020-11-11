import discord
from discord.ext import commands
import typing
from utils.query import user
from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
from utils.jomd_common import str_not_int, point_range, parse_gimme
import html
import random


class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='[username] [latest submissions]')
    async def user(self, ctx, username: typing.Optional[str_not_int]=None,
                   amount: typing.Optional[int]=None):
        """Show user profile and latest submissions

        Use surround your username with '' if it can be interpreted as a number
        """

        db = DbConn()
        username = username or db.get_handle_id(ctx.author.id, ctx.guild.id)

        # If user is not found in db
        if username is None:
            username = amount
            amount = None

        if username is None:
            return

        if amount is not None:
            amount = min(amount, 8)
            if amount < 1:
                return await ctx.send('Request at least one submission')

        data = await user_api.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = data['username']

        def is_rated(user):
            return 1 if 'rating' in user and user['rating'] else 0

        description = 'Calculated points: %.2f' % data['performance_points']
        embed = discord.Embed(
            title=username,
            url=f'https://dmoj.ca/user/{username}',
            description=description,
            color=0xfcdb05,
        )

        embed.set_thumbnail(url=await user_api.get_pfp(username))
        embed.add_field(
            name="Rank by points",
            value=await user_api.get_placement(username),
            inline=False
        )
        embed.add_field(
            name="Problems Solved",
            value=data['problem_count'],
            inline=False
        )
        embed.add_field(
            name="Rating",
            value=data['rating'],
            inline=True
        )
        embed.add_field(
            name="Contests Written",
            value=sum(map(is_rated, data['contests'])),
            inline=True
        )

        await ctx.send(embed=embed)

        if amount is None:
            return

        submissions = await submission_api.get_latest_submission(
            username, amount
        )
        embed = discord.Embed(
            title=f"{username}'s latest submissions",
            color=0xfcdb05
        )
        for submission in submissions:

            problem = db.get_problem(submission.problem)
            if problem.points is not None:
                points = str(int(problem.points))+'p'
                if problem.partial:
                    points += 'p'
            else:
                points = '???'

            embed.add_field(
                name="%s / %s" %
                     (str(submission.score_num), str(submission.score_denom)),
                value="%s | %s" % (submission.result, submission.language),
                inline=True
            )
            embed.add_field(
                name="%s (%s)" %
                     (html.unescape(submission.problem_name), points),
                value="%s | [Problem](https://dmoj.ca/problem/%s)" %
                      (submission.date, submission.problem),
                inline=True
            )
            try:
                embed.add_field(
                    name="%.2fs" % submission.time,
                    value="%s" % submission.memory,
                    inline=True,
                    )
            except TypeError:
                embed.add_field(
                    name="---",
                    value="%s" % submission.memory,
                    inline=True,
                )

        await ctx.send(embed=embed)
        return None

    @commands.command(usage='username [points solved]')
    async def predict(self, ctx, username: typing.Optional[str_not_int]=None,
                      amounts: commands.Greedy[int]=[]):
        """Predict total points after solving N pointer problem(s)

        Use surround your username with '' if it can be interpreted as a number
        """
        db = DbConn()
        username = username or db.get_handle_id(ctx.author.id, ctx.guild.id)

        if username is None and len(amounts) > 0:
            username = str([0])
            amounts.pop(0)

        if amounts == []:
            return await ctx.send(f'No points given!')

        if username is None:
            return

        amounts = amounts[:10]
        data = await user.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = data['username']

        submissions = await user.get_submissions(username)

        problems_ACed = dict()
        code_to_points = dict()
        for submission in submissions:
            code = submission.problem
            points = submission.points
            result = submission.result

            if points is not None:
                if result == 'AC':
                    problems_ACed[code] = 1
                if code not in code_to_points:
                    code_to_points[code] = points
                elif points > code_to_points[code]:
                    code_to_points[code] = points

        fully_solved = len(problems_ACed)
        points = list(code_to_points.values())
        points.sort(reverse=True)

        def calculate_points(points, fully_solved):
            b = 150*(1-0.997**fully_solved)
            p = 0
            for i in range(min(100, len(points))):
                p += (0.95**i)*points[i]
            return b+p

        embed = discord.Embed(
            title=f'Point prediction for {username}',
            description='Current points: %.2fp' %
                        calculate_points(points, fully_solved),
            color=0xfcdb05,
        )

        embed.set_thumbnail(url=await user_api.get_pfp(username))

        for predict_val in amounts:
            points.append(int(predict_val))
            fully_solved += 1
            points.sort(reverse=True)
            updated_points = calculate_points(points, fully_solved)
            embed.add_field(
                name="Solve another %sp" % predict_val,
                value="Total points: %.2fp" % updated_points,
                inline=False,
            )

        return await ctx.send(embed=embed)

    def force(argument) -> typing.Optional[bool]:
        if argument == '+f':
            return True
        raise BadArgument('No force argument')

    @commands.command(usage='[username]')
    async def cache(self, ctx, complete: typing.Optional[force]=False,
                    username: typing.Optional[str]=None):
        """Caches the submissions of a user, will speed up other commands

        Use surround your username with '' if it can be interpreted as a number
        +f              cache every submission
        """
        username = username.replace('\'', '')
        db = DbConn()
        username = username or db.get_handle_id(ctx.author.id, ctx.guild.id)

        if username is None:
            return await ctx.send(f'No username given!')

        data = await user.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = data['username']

        try:
            msg = await ctx.send(f'Caching {username}\'s submissions')
        except Exception as e:
            await msg.edit(content='An error has occured, ' +
                                   'try caching again. Log: '+e.message)
            return

        if complete:
            await user.get_all_submissions(username)
        else:
            await user.get_submissions(username)

        return await msg.edit(content=f'{username}\'s submissions ' +
                                      'have been cached.')

    @commands.command(hidden=True)
    async def gimmie(self, ctx):
        return await ctx.send(':monkey:')

    @commands.command(usage='username [points] [problem types]')
    async def gimme(self, ctx, username: typing.Optional[parse_gimme]=None,
                    points: typing.Optional[point_range]=[1, 50], *filters):
        """Recommend a problem

        Use surround your username with '' if it can be interpreted as a number

        Shorthands:
        - adhoc
        - math
        - bf
        - ctf
        - ds
        - d&c
        - dp
        - geo
        - gt
        - greedy
        - regex
        - string"""
        filters = list(filters)
        db = DbConn()
        username = username or db.get_handle_id(ctx.author.id, ctx.guild.id)

        if username is None:
            return await ctx.send(f'No username provided')

        data = await user.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = data['username']
        shorthands = {
            'adhoc': ['Ad Hoc'],
            'math': ['Advanced Math', 'Intermediate Math', 'Simple Math'],
            'bf': ['Brute Force'],
            'ctf': ['Capture the Flag'],
            'ds': ['Data Structures'],
            'd&c': ['Divide and Conquer'],
            'dp': ['Dynamic Programming'],
            'geo': ['Geometry'],
            'gt': ['Graph Theory'],
            'greedy': ['Greedy Algorithms'],
            'regex': ['Regular Expressions'],
            'string': ['String Algorithms'],
        }

        filter_list = []
        for filter in filters:
            if filter in shorthands:
                filter_list += shorthands[filter]
            else:
                filter_list.append(filter.title())

        filters = filter_list
        # I will add this when the api has a fast way to query total objects
        # Maybe keep track of the last time it was updated and update
        # according to that
        # user.get_submissions(username)

        problems = db.get_unsolved_problems(username, points[0], points[1])

        results = []
        if filters != []:
            for problem in problems:
                if set(problem.types) & set(filters) != set():
                    results.append(problem)
        else:
            results = problems

        if len(results) == 0:
            return await ctx.send('No problems found which satify filters')

        problem = random.choice(results)
        points = str(problem.points)
        if problem.partial:
            points += 'p'

        memory = problem.memory_limit
        if memory >= 1024:
            memory = '%dM' % (memory//1024)
        else:
            memory = '%dK' % (memory)

        embed = discord.Embed(
            title=problem.name,
            url='https://dmoj.ca/problem/%s' % problem.code,
            description='Points: %s\nProblem Types: %s' %
                        (points, ', '.join(problem.types)),
            color=0xfcdb05,
        )

        embed.set_thumbnail(url=await user_api.get_pfp(username))
        embed.add_field(name='Group', value=problem.group, inline=True)
        embed.add_field(
            name='Time',
            value='%ss' % problem.time_limit,
            inline=True
        )
        embed.add_field(name='Memory', value=memory, inline=True)
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(User(bot))
