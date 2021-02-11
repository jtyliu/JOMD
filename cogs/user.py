import discord
from discord.ext import commands
import typing
from discord.ext.commands.errors import BadArgument
from utils.query import Query
from utils.db import session
from sqlalchemy import func, or_, not_, orm, distinct
from utils.db import (session, Problem as Problem_DB,
                      Contest as Contest_DB,
                      Participation as Participation_DB,
                      User as User_DB, Submission as Submission_DB,
                      Organization as Organization_DB,
                      Language as Language_DB, Judge as Judge_DB,
                      Handle as Handle_DB, Json)
from utils.jomd_common import (str_not_int, point_range, parse_gimme,
                               calculate_points)
from utils.api import ObjectNotFound
from utils.constants import TZ
import asyncio
import random
from operator import itemgetter



class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='[username] [latest submissions]')
    async def user(self, ctx, username: typing.Optional[str_not_int]=None,
                   amount: typing.Optional[int]=None):
        """Show user profile and latest submissions

        Use surround your username with '' if it can be interpreted as a number
        """

        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

        # If user is not found in db
        if username is None:
            username = str(amount)
            amount = None

        if username is None:
            return

        if amount is not None:
            amount = min(amount, 8)
            if amount < 1:
                return await ctx.send('Please request at least one submission')

        try:
            user = await query.get_user(username)
        except ObjectNotFound:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = user.username

        def is_rated(contest):
            return 1 if contest.is_rated else 0

        description = 'Calculated points: %.2f' % user.performance_points
        embed = discord.Embed(
            title=username,
            url=f'https://dmoj.ca/user/{username}',
            description=description,
            color=0xfcdb05,
        )

        embed.set_thumbnail(url=await query.get_pfp(username))
        embed.add_field(
            name="Rank by points",
            value=await query.get_placement(username),
            inline=False
        )
        embed.add_field(
            name="Problems Solved",
            value=user.problem_count,
            inline=False
        )
        embed.add_field(
            name="Rating",
            value=user.rating,
            inline=True
        )
        embed.add_field(
            name="Contests Written",
            value=sum(map(is_rated, user.contests)),
            inline=True
        )

        await ctx.send(embed=embed)

        if amount is None:
            return

        submissions = await query.get_latest_submissions(username, amount)

        embed = discord.Embed(
            title=f"{username}'s latest submissions",
            color=0xfcdb05
        )
        for submission in submissions:
            problem = submission.problem[0]
            if problem.points is not None:
                points = str(int(problem.points))+'p'
                if problem.partial:
                    points += 'p'
            else:
                points = '???'

            true_short_name = submission.language[0].short_name
            if true_short_name == '':
                # wtf dmoj
                true_short_name = submission.language[0].key

            embed.add_field(
                name="%s / %s" %
                     (str(submission.score_num), str(submission.score_denom)),
                value="%s | %s" % (submission.result,
                                   true_short_name),
                inline=True
            )

            embed.add_field(
                name="%s (%s)" %
                     (submission.problem[0].name, points),
                value="%s | [Problem](https://dmoj.ca/problem/%s)" %
                      (submission.date.astimezone(TZ).
                       strftime("%b. %d, %Y, %I:%M %p").
                       replace('AM', 'a.m.').
                       replace('PM', 'p.m.'),
                       submission.problem[0].code),
                      # Jan. 13, 2021, 12:17 a.m.
                      # %b. %d, %Y, %I:%M %p
                inline=True
            )
            try:
                embed.add_field(
                    name="%.2fs" % submission.time,
                    value="%s" % submission.memory_str,
                    inline=True,
                    )
            except TypeError:
                embed.add_field(
                    name="---",
                    value="%s" % submission.memory_str,
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
        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

        if username is None and len(amounts) > 0:
            username = str([0])
            amounts.pop(0)

        if amounts == []:
            return await ctx.send(f'No points given!')

        if username is None:
            return

        amounts = amounts[:10]

        user = await query.get_user(username)
        if user is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = user.username
        q = session.query(Submission_DB).options(orm.joinedload('problem'))\
            .join(User_DB, User_DB.username == Submission_DB._user,
                  aliased=True)\
            .filter(User_DB.username == user.username)

        if q.count():
            submissions = q.all()
            msg = None
        else:
            await ctx.send('No submissions cached, '
                           'Please use +cache to get new submissions')
            return

        problems_ACed = dict()
        code_to_points = dict()
        for submission in submissions:
            code = submission.problem[0].code
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

        embed = discord.Embed(
            title=f'Point prediction for {username}',
            description='Current points: %.2fp' %
                        calculate_points(points, fully_solved),
            color=0xfcdb05,
        )

        embed.set_thumbnail(url=await query.get_pfp(username))

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

        if msg:
            await msg.delete()
        await ctx.send(embed=embed)
        return

    @commands.command(usage='[usernames]')
    async def vc(self, ctx, *usernames):
        """Suggest a contest"""
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

        q = session.query(Contest_DB)
        for user in users:
            # if the user has attempted any problems from the problem set
            sub_q = session.query(Submission_DB,
                                  func.max(Submission_DB.points))\
                .filter(Submission_DB._user == user.username)\
                .group_by(Submission_DB._code).subquery()
            sub_q = session.query(Problem_DB.code)\
                .join(sub_q, Problem_DB.code == sub_q.c._code, isouter=True)\
                .filter(func.ifnull(sub_q.c.points, 0) != 0)
            sub_q = list(map(itemgetter(0), sub_q.all()))
            q = q.filter(not_(Contest_DB.rankings.contains(user.username)))\
                .filter(~Contest_DB.problems.any(Problem_DB.code.in_(sub_q)))

        if q.count() == 0:
            await ctx.send("Cannot find any contests which "
                           "all users have not done")
            return
        contest = random.choice(q.all())

        # When problems are private, it says there are no problems
        window = 'No'
        if contest.time_limit:
            window = f"{contest.time_limit/60/60} Hr"
        embed = discord.Embed(
            title=contest.name, url=f"https://dmoj.ca/contest/{contest.key}",
            description=f"{window} window | {len(contest.problems)} Problems",
            color=0xfcdb05
        )
        await ctx.send(embed=embed)

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
        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

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
                                   'try caching again. Log: '+e.message)
            return

        await query.get_submissions(username)

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
        query = Query()
        username = username or query.get_handle(ctx.author.id, ctx.guild.id)

        if username is None:
            return await ctx.send(f'No username provided')

        user = await query.get_user(username)
        if user is None:
            return await ctx.send(f'{username} does not exist on DMOJ')

        username = user.username
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

        # Get all problems that are unsolved by user and fits the filter and point range
        results = query.get_unsolved_problems(username, filters,
                                              points[0], points[1])

        if len(results) == 0:
            return await ctx.send('No problems found which satify filters')

        problem = random.choice(results)
        points = str(problem.points)
        if problem.partial:
            points += 'p'

        memory = problem.memory_limit
        if memory >= 1024*1024:
            memory = '%dG' % (memory//1024//1024)
        elif memory >= 1024:
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

        embed.set_thumbnail(url=await query.get_pfp(username))
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
