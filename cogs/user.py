import discord
from discord.ext import commands
import typing
from utils.query import user
from discord.ext.commands.errors import BadArgument
from utils.api import user_api, submission_api
from utils.db import DbConn
import html
import random

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='username [latest submissions]')
    async def user(self, ctx, username: str, amount: typing.Optional[int] = None):
        """Show user profile and latest submissions"""
        if amount is not None:
            amount = min(amount, 8)
            if amount < 1:
                return await ctx.send('Request at least one submission')

        data = await user_api.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')
        
        username = data['username']

        def is_rated(user):
            return 1 if 'rating' in user else 0 
        
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
        
        submissions = await submission_api.get_latest_submission(username, amount)
        embed = discord.Embed(
            title=f"{username}'s latest submissions",
            color=0xfcdb05
        )

        for submission in submissions:
            
            embed.add_field(
                name="%s / %s" % (str(submission.score_num), str(submission.score_denom)),
                value="%s | %s" % (submission.result, submission.language),
                inline=True
            )
            embed.add_field(
                name="%s" % html.unescape(submission.problem_name),
                value="%s | [Problem](https://dmoj.ca/problem/%s)" % (submission.date, submission.problem),
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
    async def predict(self, ctx, username : str, amounts : commands.Greedy[int]):
        """Predict total points after solving N pointer problem(s)"""
        if amounts == []:
            return await ctx.send(f'No points given!')

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

            if points != None and points != 0:
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
            description='Current points: %.2fp' % calculate_points(points, fully_solved),
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

    @commands.command(usage='username')
    async def cache(self, ctx, username : str):
        """Caches the submissions of a user, will speed up other commands"""
        data = await user.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')
        
        username = data['username']

        try:
            msg = await ctx.send(f'Caching {username}\'s submissions')
        except:
            return await msg.edit(content='An error has occured, try caching again')

        await user.get_submissions(username)

        return await msg.edit(content=f'{username}\'s submissions have been cached.')


    def point_range(argument) -> typing.Optional[list]:
        if '-' in argument:
            argument = argument.split('-')
            if len(argument) != 2:
                raise BadArgument('Too many -, invalid range')
            try:
                point_high = int(argument[0])
                point_low = int(argument[1])
                return [point_high, point_low]
            except ValueError as e:
                raise BadArgument('Point values are not an integer')
        try:
            point_high = point_low = int(argument)
            return [point_high, point_low]
        except ValueError as e:
            raise BadArgument('Point value is not an integer')

    @commands.command(hidden=True)
    async def gimmie(self, ctx):
        return await ctx.send(':monkey:')

    @commands.command(usage='username [points] [problem types]')
    async def gimme(self, ctx, username : str, points : typing.Optional[point_range]=[1,50], *filters):
        """Recommend a problem

        Shorthands: ['adhoc','math','bf','ctf','ds','d&c','dp','geo','gt','greedy','regex','string']"""
        filters = list(filters)
        
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
        # Maybe keep track of the last time it was updated and update according to that
        # user.get_submissions(username)
        
        db = DbConn()
        problems = db.get_unsolvedproblems(username, points[0], points[1])

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
                        description='Points: %s\nProblem Types: %s' % (points, ', '.join(problem.types)),
                        color=0xfcdb05,
        )

        embed.set_thumbnail(url=await user_api.get_pfp(username))
        embed.add_field(name='Group', value=problem.group, inline=True)
        embed.add_field(name='Time', value='%ss' % problem.time_limit, inline=True)
        embed.add_field(name='Memory', value=memory, inline=True)
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(User(bot))