import discord
from discord.ext import commands
import typing
from utils.apiordb import user
from utils.api import user_api, submission_api
import html

class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='username [latest submissions]')
    async def user(self, ctx, username: str, amount: typing.Optional[int] = None):
        if amount is not None:
            amount = min(amount, 8)
            if amount < 1:
                return await ctx.send('Request at least one submission')

        data = await user.get_user(username)
        if data is None:
            return await ctx.send(f'{username} does not exist on DMOJ')
        
        username = data['username']

        def is_rated(user):
            return 'rating' in user
        
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
                name="%d / %d" % (submission.score_num, submission.score_denom),
                value="%s | %s" % (submission.result, submission.language),
                inline=True
            )
            embed.add_field(
                name="%s" % html.unescape(submission.problem_name),
                value="%s | [Problem](https://dmoj.ca/problem/%s)" % (submission.date, submission.problem),
                inline=True
            )
            embed.add_field(
                name="%.2fs" % (submission.time),
                value="%s" % submission.memory,
                inline=True
            )

        await ctx.send(embed=embed)
        return None






def setup(bot):
    bot.add_cog(UserCog(bot))