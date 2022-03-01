from datetime import datetime

# import discord
# from discord.ext import commands
import hikari
import lightbulb
import typing as t

# from discord.ext.commands.errors import BadArgument
from utils.query import Query
from utils.db import session
from sqlalchemy import alias, func, not_, orm
from utils.db import Problem as Problem_DB, Contest as Contest_DB, User as User_DB, Submission as Submission_DB
from utils.jomd_common import is_int
from utils.api import ObjectNotFound
from utils.constants import SITE_URL, TZ, SHORTHANDS
import asyncio
import random
from operator import itemgetter
import logging
from lightbulb.converters import base
from lightbulb.commands.base import OptionModifier

logger = logging.getLogger(__name__)


plugin = lightbulb.Plugin("User")


class StrNotIntConverter(base.BaseConverter[str]):
    """Implementation of the base converter for converting arguments into a point range."""

    __slots__ = ()

    async def convert(self, arg: str) -> str:
        if is_int(arg):
            raise TypeError("This is an integer")  # kevinyang theorem
        return arg


@plugin.command()
@lightbulb.option("amount", "List last N submissions", int, required=False)
@lightbulb.option("username", "Dmoj username", StrNotIntConverter, required=False)
@lightbulb.set_help("Use surround your username with '' if it can be interpreted as a number")
@lightbulb.command("user", "Show user profile and latest submissions")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def user(ctx):
    # TODO Optimize the two calls to /user
    username = ctx.options.username
    amount = ctx.options.amount
    query = Query()
    username = username or query.get_handle(ctx.author.id, ctx.get_guild().id)

    # If user is not found in db
    if username is None:
        username = str(amount)
        amount = None

    if username is None:
        return

    if amount is not None:
        amount = min(amount, 8)
        if amount < 1:
            return await ctx.respond("Please request at least one submission")

    try:
        user = await query.get_user(username)
    except ObjectNotFound:
        return await ctx.respond(f"{username} does not exist on DMOJ")

    username = user.username

    def is_rated(contest):
        return 1 if contest.is_rated else 0

    description = "Calculated points: %.2f" % user.performance_points
    embed = hikari.Embed(
        title=username,
        url=f"https://dmoj.ca/user/{username}",
        description=description,
        color=0xFCDB05,
    )

    embed.set_thumbnail(await query.get_pfp(username))
    embed.add_field(name="Rank by points", value=await query.get_placement(username), inline=False)
    embed.add_field(name="Problems Solved", value=user.problem_count, inline=False)
    embed.add_field(name="Rating", value=user.rating, inline=True)
    embed.add_field(name="Contests Written", value=sum(map(is_rated, user.contests)), inline=True)

    await ctx.respond(embed=embed)

    if amount is None:
        return

    submissions = await query.get_latest_submissions(username, amount)

    embed = hikari.Embed(title=f"{username}'s latest submissions", color=0xFCDB05)
    for submission in submissions:
        problem = submission.problem[0]
        if problem.points is not None:
            points = str(int(problem.points)) + "p"
            if problem.partial:
                points += "p"
        else:
            points = "???"

        true_short_name = submission.language[0].short_name
        if true_short_name == "":
            # wtf dmoj
            true_short_name = submission.language[0].key

        embed.add_field(
            name="%s / %s" % (str(submission.score_num), str(submission.score_denom)),
            value="%s | %s" % (submission.result, true_short_name),
            inline=True,
        )

        embed.add_field(
            name="%s (%s)" % (submission.problem[0].name, points),
            value="%s | [Problem](https://dmoj.ca/problem/%s)"
            % (
                submission.date.astimezone(TZ)
                .strftime("%b. %d, %Y, %I:%M %p")
                .replace("AM", "a.m.")
                .replace("PM", "p.m."),
                submission.problem[0].code,
            ),
            # Jan. 13, 2021, 12:17 a.m.
            # %b. %d, %Y, %I:%M %p
            inline=True,
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

    await ctx.respond(embed=embed)
    return None


@plugin.command()
@lightbulb.option("amount", "List last N submissions", int, required=False)
@lightbulb.option("username", "List last N submissions", StrNotIntConverter, required=False)
@lightbulb.set_help("Use surround your username with '' if it can be interpreted as a number")
@lightbulb.command("userinfo", "Show user profile and latest submissions (Adelaide command)", aliases=["ui"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def userinfo(ctx):
    """Show user profile and latest submissions

    Use surround your username with '' if it can be interpreted as a number
    """
    username = ctx.options.username
    amount = ctx.options.amount
    query = Query()
    username = username or query.get_handle(ctx.author.id, ctx.get_guild().id)
    # If user is not found in db
    if username is None:
        username = str(amount)
        amount = None

    if username is None:
        return

    if amount is not None:
        amount = min(amount, 8)
        if amount < 1:
            return await ctx.respond("Please request at least one submission")

    try:
        user = await query.get_user(username)
    except ObjectNotFound:
        return await ctx.respond(f"{username} does not exist on DMOJ")

    username = user.username

    def is_rated(contest):
        return 1 if contest.is_rated else 0

    discordHandle = ctx.get_guild().get_member(query.get_handle_user(username, ctx.get_guild().id))
    if discordHandle:
        discordHandle = discordHandle.nickname or discordHandle.name
    else:
        discordHandle = "Unknown"
    if user.rating is None:
        color = 0xFEFEFE  # it breaks when I set it to white
    elif user.rating >= 3000:
        color = 0x000000
    elif user.rating >= 2700:
        color = 0xA00000
    elif user.rating >= 2400:
        color = 0xEE0000
    elif user.rating >= 1900:
        color = 0xFFB100
    elif user.rating >= 1600:
        color = 0x800080
    elif user.rating >= 1300:
        color = 0x0000FF
    elif user.rating >= 1000:
        color = 0x00A900
    elif user.rating >= 0:
        color = 0x999999
    else:
        color = 0x000000
    description = f"Discord name: {discordHandle}"
    embed = hikari.Embed(
        title=username,
        url=f"https://dmoj.ca/user/{username}",
        description=description,
        color=color,  # rating color
    )

    embed.set_thumbnail(await query.get_pfp(username))
    embed.add_field(
        name="Points", value=str(round(user.performance_points)) + "/" + str(round(user.points)), inline=True
    )
    embed.add_field(name="Problems Solved", value=user.problem_count, inline=True)
    embed.add_field(name="Rating", value=str(user.rating) + "/" + str(user.max_rating), inline=True)
    embed.add_field(name="Contests Written", value=sum(map(is_rated, user.contests)), inline=True)

    await ctx.respond(embed=embed)

    if amount is None:
        return

    submissions = await query.get_latest_submissions(username, amount)

    embed = hikari.Embed(title=f"{username}'s latest submissions", color=0xFFFF00)
    for submission in submissions:
        problem = submission.problem[0]
        if problem.points is not None:
            points = str(int(problem.points)) + "p"
            if problem.partial:
                points += "p"
        else:
            points = "???"

        true_short_name = submission.language[0].short_name
        if true_short_name == "":
            # wtf dmoj
            true_short_name = submission.language[0].key

        embed.add_field(
            name="%s / %s" % (str(submission.score_num), str(submission.score_denom)),
            value="%s | %s" % (submission.result, true_short_name),
            inline=True,
        )

        embed.add_field(
            name="%s (%s)" % (submission.problem[0].name, points),
            value="%s | [Problem](https://dmoj.ca/problem/%s)"
            % (
                submission.date.astimezone(TZ)
                .strftime("%b. %d, %Y, %I:%M %p")
                .replace("AM", "a.m.")
                .replace("PM", "p.m."),
                submission.problem[0].code,
            ),
            # Jan. 13, 2021, 12:17 a.m.
            # %b. %d, %Y, %I:%M %p
            inline=True,
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

    await ctx.respond(embed=embed)
    return None


@plugin.command()
@lightbulb.option("point_vals", "Points values", t.Sequence[int], modifier=OptionModifier.GREEDY, required=False, default=[])
@lightbulb.option("username", "Dmoj username", StrNotIntConverter, required=False)
@lightbulb.set_help("Use surround your username with '' if it can be interpreted as a number")
@lightbulb.command("predict", "Predict total points after solving N point problem(s)")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def predict(ctx):
    username = ctx.options.username
    amounts = ctx.options.point_vals
    logger.info("Point vals: %s, username: %s", amounts, username)
    query = Query()
    username = username or query.get_handle(ctx.author.id, ctx.get_guild().id)
    if username is None and len(amounts) > 0:
        username = str([0])
        amounts.pop(0)

    if amounts == []:
        return await ctx.respond("No points given!")

    if username is None:
        return await ctx.respond("No user given")

    amounts = amounts[:10]

    user = await query.get_user(username)
    if user is None:
        return await ctx.respond(f"{username} does not exist on DMOJ")

    username = user.username
    q = (
        session.query(Submission_DB)
        .options(orm.joinedload("problem"))
        .join(User_DB, User_DB.username == Submission_DB._user, aliased=True)
        .filter(User_DB.username == user.username)
    )

    if q.count():
        submissions = q.all()
        msg = None
    else:
        await ctx.respond("No submissions cached, " "Please use +cache to get new submissions")
        return

    problems_ACed = dict()
    code_to_points = dict()
    for submission in submissions:
        code = submission.problem[0].code
        points = submission.points
        result = submission.result

        if points is not None:
            if result == "AC":
                problems_ACed[code] = 1
            if code not in code_to_points:
                code_to_points[code] = points
            elif points > code_to_points[code]:
                code_to_points[code] = points

    fully_solved = len(problems_ACed)
    points = list(code_to_points.values())
    points.sort(reverse=True)

    embed = discord.Embed(
        title=f"Point prediction for {username}",
        description="Current points: %.2fp" % calculate_points(points, fully_solved),
        color=0xFCDB05,
    )

    embed.set_thumbnail(await query.get_pfp(username))

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
    await ctx.respond(embed=embed)
    return


# @commands.command(usage="[usernames]")
# async def vc(self, ctx, *usernames):
#     """Suggest a contest"""
#     usernames = list(usernames)

#     query = Query()
#     if usernames == []:
#         username = query.get_handle(ctx.author.id, ctx.get_guild().id)
#         if username:
#             usernames = [username]

#     users = await asyncio.gather(*[query.get_user(username) for username in usernames])
#     usernames = [user.username for user in users]
#     for i in range(len(users)):
#         if users[i] is None:
#             return await ctx.respond(f"{usernames[i]} does not exist on DMOJ")

#     q = session.query(Contest_DB)
#     for user in users:
#         # if the user has attempted any problems from the problem set
#         sub_q = (
#             session.query(Submission_DB, func.max(Submission_DB.points))
#             .filter(Submission_DB._user == user.username)
#             .group_by(Submission_DB._code)
#             .subquery()
#         )
#         sub_q = (
#             session.query(Problem_DB.code)
#             .join(sub_q, Problem_DB.code == sub_q.c._code, isouter=True)
#             .filter(func.ifnull(sub_q.c.points, 0) != 0)
#         )
#         sub_q = list(map(itemgetter(0), sub_q.all()))
#         q = (
#             q.filter(not_(Contest_DB.rankings.contains(user.username)))
#             .filter(~Contest_DB.problems.any(Problem_DB.code.in_(sub_q)))
#             .filter(Contest_DB.is_private == 0)
#             .filter(Contest_DB.is_organization_private == 0)
#         )

#     if q.count() == 0:
#         await ctx.respond("Cannot find any contests which " "all users have not done")
#         return

#     contests = q.all()

#     while True:
#         contest = random.choice(contests)
#         try:
#             contest = await query.get_contest(contest.key, cached=False)
#             break
#         except ObjectNotFound:
#             pass

#     # When problems are private, it says there are no problems
#     window = "No"
#     is_rated = "Not Rated"
#     if contest.time_limit:
#         window = f"{round(contest.time_limit/60/60, 2)} Hr"
#     if contest.is_rated:
#         is_rated = "Rated"
#     embed = discord.Embed(
#         title=contest.name,
#         url=f"https://dmoj.ca/contest/{contest.key}",
#         description=f"{window} window | {len(contest.problems)} Problems | {is_rated}",
#         color=0xFCDB05,
#     )
#     await ctx.respond(embed=embed)


# def force(argument) -> typing.Optional[bool]:
#     if argument == "+f":
#         return True
#     raise BadArgument("No force argument")


# @commands.command(hidden=True)
# async def gimmie(self, ctx):
#     return await ctx.respond(":monkey:")


# @commands.command(aliases=["recommend"], usage="username [points] [problem types]")
# async def gimme(
#     self, ctx, username: typing.Optional[parse_gimme] = None, points: typing.Optional[point_range] = [1, 50], *filters
# ):
#     """
#     Recommend a problem

#     Use surround your username with '' if it can be interpreted as a number

#     SHORTHANDS:
#     - adhoc
#     - math
#     - bf
#     - ctf
#     - ds
#     - d&c
#     - dp
#     - geo
#     - gt
#     - greedy
#     - regex
#     - string
#     """
#     filters = list(filters)
#     query = Query()
#     username = username or query.get_handle(ctx.author.id, ctx.get_guild().id)

#     if username is None:
#         return await ctx.respond("No username provided")

#     user = await query.get_user(username)
#     if user is None:
#         return await ctx.respond(f"{username} does not exist on DMOJ")

#     username = user.username
#     filter_list = []
#     for filter in filters:
#         if filter in SHORTHANDS:
#             filter_list += SHORTHANDS[filter]
#         else:
#             filter_list.append(filter.title())

#     filters = filter_list

#     # Get all problems that are unsolved by user and fits the filter and
#     # point range
#     result, problem = await gimme_common(username, points, filters)

#     if result is None:
#         return await ctx.respond("No problem that satisfies the filter")
#     return await ctx.respond(embed=result)


# @commands.command(aliases=["stalk", "sp"], usage="[username] [p<=points, p>=points]")
# async def solved(self, ctx, *args):
#     """Shows a user's last solved problems"""
#     minP = 0
#     maxP = 100
#     query = Query()
#     username = None
#     for arg in args:
#         if arg.startswith("p>="):
#             minP = max(minP, int(arg[3:]))
#         elif arg.startswith("p<="):
#             maxP = min(maxP, int(arg[3:]))
#         else:
#             username = (await query.get_user(arg)).username
#     if username is None:
#         username = query.get_handle(ctx.author.id, ctx.get_guild().id)
#     await query.get_submissions(username, result="AC")

#     submissions = (
#         session.query(Submission_DB)
#         .filter(Submission_DB._user == username)
#         .filter(Submission_DB.result == "AC")
#         .options(orm.joinedload(Submission_DB.problem, innerjoin=True))
#         .join(Submission_DB.problem)
#         .filter(Problem_DB.is_organization_private == 0)
#         .filter(Problem_DB.is_public == 1)
#         .order_by(Submission_DB.date)
#         .all()
#     )
#     uniqueSubmissions = []
#     solved = set()
#     for sub in submissions:
#         if sub._code not in solved:
#             solved.add(sub._code)
#             if minP <= sub.points and sub.points <= maxP:
#                 uniqueSubmissions.append(sub)
#     uniqueSubmissions.reverse()
#     page = ""
#     content = []
#     cnt = 0
#     for sub in uniqueSubmissions:
#         age = (datetime.now() - sub.date).days
#         page += f"[{sub.problem[0].name}]({SITE_URL}/problem/{sub._code}) [{sub.points}] ({age} days ago)\n"
#         cnt += 1
#         if cnt % 10 == 0:
#             content.append(page)
#             page = ""
#     if page != "":
#         content.append(page)
#     if len(content) == 0:
#         content.append("No submission")
#     title = "Recently solved problems by " + username
#     message = await ctx.respond(embed=discord.Embed().add_field(name=title, value=content[0]))
#     await scroll_embed(ctx, self.bot, message, title, content)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
