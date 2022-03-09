import hikari
import lightbulb
import typing as t
from utils.api import ObjectNotFound
import typing
from utils.query import Query
from utils.graph import plot_type_radar, plot_type_bar, plot_rating, plot_points, plot_solved
from utils.jomd_common import calculate_points
from lightbulb.commands.base import OptionModifier
from utils.models import *
from operator import attrgetter, itemgetter
from sqlalchemy import or_, orm, func
import asyncio
import io
import bisect
import logging
from lightbulb.converters import base


logger = logging.getLogger(__name__)


plugin = lightbulb.Plugin("Plot")


class PeakConverter(base.BaseConverter[str]):
    """Implementation of the base converter for converting arguments into a peak arguement."""

    __slots__ = ()

    async def convert(self, arg: str) -> str:
        if arg == "+peak":
            return True
        if arg == "+max":
            return True
        raise TypeError("Argument not known")


class GraphTypeConverter(base.BaseConverter[str]):
    """Implementation of the base converter for converting arguments into a graph type arguement."""

    __slots__ = ()

    async def convert(self, arg: str) -> str:
        if arg == "+radar":
            return "radar"
        if arg == "+bar":
            return "bar"
        raise TypeError("Argument not known")


class PercentageConverter(base.BaseConverter[str]):
    """Implementation of the base converter for converting arguments into a percentage arguement."""

    __slots__ = ()

    async def convert(self, arg: str) -> str:
        if arg == "+percent":
            return True
        if arg == "+percentage":
            return True
        if arg == "+point":
            return False
        if arg == "+points":
            return False
        raise TypeError("Argument not known")


@plugin.command()
@lightbulb.command("plot", "Graphs for analyzing DMOJ activity")
@lightbulb.implements(lightbulb.PrefixCommandGroup, lightbulb.SlashCommandGroup)
async def plot(ctx):
    """Plot various graphs"""
    await ctx.respond("TODO: Implement plot help menu")


# TODO: Implement slash commands for subgroups


@plot.child
@lightbulb.option(
    "usernames",
    "Usernames to plot",
    str,
    modifier=OptionModifier.GREEDY,
    required=False,
    default=[],
)
@lightbulb.command("solved", "Plot problems solved over time")
@lightbulb.implements(lightbulb.PrefixSubCommand)
async def solved(ctx):
    """Plot problems solved over time"""
    usernames = ctx.options.usernames

    query = Query()
    if usernames == []:
        usernames = [query.get_handle(ctx.author.id, ctx.get_guild().id)]

    try:
        users = await asyncio.gather(*[query.get_user(username) for username in usernames])
    except ObjectNotFound:
        return await ctx.respond("User not found")

    user_ids = [user.id for user in users]
    usernames = [user.username for user in users]
    for user, username in zip(users, usernames):
        if user is None:
            return await ctx.respond(f'{username} does not exist on DMOJ')
    if len(users) > 10:
        return await ctx.respond("Too many users given, max 10")

    total_data = {}
    for user_id, username in zip(user_ids, usernames):
        q = session.query(func.count(Submission.id))\
            .filter(Submission.user_id == user_id)
        if q.count() == 0:
            await ctx.respond(f"`{username}` does not have any cached submissions, caching now")
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

    embed = hikari.Embed(
        title="Problems Solved",
        color=0xFCDB05,
    )
    with open("./graphs/plot.png", "rb") as file:
        embed.set_image(hikari.Bytes(file.read(), "plot.png"))

    return await ctx.respond(embed=embed)


@plot.child
@lightbulb.option(
    "usernames",
    "Usernames to plot",
    str,
    modifier=OptionModifier.GREEDY,
    required=False,
    default=[],
)
@lightbulb.command("points", "Plot point progression")
@lightbulb.implements(lightbulb.PrefixSubCommand)
async def points(ctx):
    """Plot point progression"""
    usernames = ctx.options.usernames

    query = Query()
    if usernames == []:
        usernames = [query.get_handle(ctx.author.id, ctx.get_guild().id)]

    try:
        users = await asyncio.gather(*[query.get_user(username) for username in usernames])
    except ObjectNotFound:
        return await ctx.respond("User not found")

    user_ids = [user.id for user in users]
    usernames = [user.username for user in users]
    for user, username in zip(users, usernames):
        if user is None:
            return await ctx.respond(f'{username} does not exist on DMOJ')
    if len(users) > 10:
        return await ctx.respond("Too many users given, max 10")

    total_data = {}
    for user_id, username in zip(user_ids, usernames):
        q = session.query(Submission)\
            .options(orm.joinedload('problem'))\
            .filter(Submission.user_id == user_id)\
            .order_by(Submission.date)

        submissions = q.all()
        if len(submissions) == 0:
            await ctx.respond(f"`{username}` does not have any cached submissions, caching now")
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
                if result == "AC":
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
                cur_points = calculate_points(points_arr[::-1], len(problems_ACed))
                data_to_plot[submission.date] = cur_points
        total_data[username] = data_to_plot

    plot_points(total_data)

    embed = hikari.Embed(
        title="Problems Progression",
        color=0xFCDB05,
    )
    with open("./graphs/plot.png", "rb") as file:
        embed.set_image(hikari.Bytes(file.read(), "plot.png"))

    return await ctx.respond(embed=embed)


@plot.child
@lightbulb.option(
    "usernames",
    "Usernames to plot",
    str,
    modifier=OptionModifier.GREEDY,
    required=False,
    default=[],
)
@lightbulb.option(
    "peak",
    "[+peak, +max] Only plot increase in rating",
    PeakConverter,
    required=False,
    default=False,
)
@lightbulb.command("rating", "Plot rating progression")
@lightbulb.implements(lightbulb.PrefixSubCommand)
async def rating(ctx):
    """Plot rating progression"""
    peak = ctx.options.peak
    usernames = ctx.options.usernames

    query = Query()
    if usernames == []:
        usernames = [query.get_handle(ctx.author.id, ctx.get_guild().id)]

    try:
        users = await asyncio.gather(*[query.get_user(username) for username in usernames])
    except ObjectNotFound:
        return await ctx.respond("User not found")

    user_ids = [user.id for user in users]
    usernames = [user.username for user in users]
    for user, username in zip(users, usernames):
        if user is None:
            return await ctx.respond(f'{username} does not exist on DMOJ')
    if len(users) > 10:
        return await ctx.respond("Too many users given, max 10")

    q = session.query(User.username, Participation.new_rating, Contest.end_time).\
        join(Participation.contest).\
        join(Participation.user).\
        filter(Participation.user_id.in_(user_ids)).\
        filter(Participation.new_rating != None).\
        order_by(Contest.end_time)
    data = q.all()

    plot_rating(data)

    embed = hikari.Embed(
        title="Rating Progression",
        color=0xFCDB05,
    )
    with open("./graphs/plot.png", "rb") as file:
        embed.set_image(hikari.Bytes(file.read(), "plot.png"))

    return await ctx.respond(embed=embed)


@plot.child
@lightbulb.option(
    "usernames",
    "Usernames to plot",
    str,
    modifier=OptionModifier.GREEDY,
    required=False,
    default=[],
)
@lightbulb.option(
    "graph_type",
    "[+radar, +bar] Plot as radar or bar graph",
    GraphTypeConverter,
    required=False,
    default="radar",
)
@lightbulb.option(
    "as_percent",
    "[+percent, +point] Plot as percentage or point value",
    PercentageConverter,
    required=False,
    default=True,
)
@lightbulb.command("type", "Graph problems solved by popular problem types")
@lightbulb.implements(lightbulb.PrefixSubCommand)
async def type(ctx):
    """Graph problems solved by popular problem types"""
    # TODO: This is aids, pls fix

    usernames = ctx.options.usernames
    graph_type = ctx.options.graph_type
    as_percent = ctx.options.as_percent

    query = Query()
    if usernames == []:
        usernames = [query.get_handle(ctx.author.id, ctx.get_guild().id)]

    try:
        users = await asyncio.gather(*[query.get_user(username) for username in usernames])
    except ObjectNotFound:
        return await ctx.respond("User not found")

    for i in range(len(users)):
        if users[i] is None:
            return await ctx.respond(f"{usernames[i]} does not exist on DMOJ")

    if len(users) > 6:
        return await ctx.respond("Too many users given, max 6")

    usernames = [data.username for data in users]

    important_types = [
        ["Data Structures"],
        ["Dynamic Programming"],
        ["Graph Theory"],
        ["String Algorithms"],
        ["Advanced Math", "Geometry", "Intermediate Math", "Simple Math"],
        ["Ad Hoc"],
        ["Greedy Algorithms"],
    ]
    labels = [
        "Data Structures",
        "Dynamic Programming",
        "Graph Theory",
        "String Algorithms",
        "Math",
        "Ad Hoc",
        "Greedy Algorithms",
    ]

    data = {}
    data["group"] = []
    for label in labels:
        data[label] = []
    for username in usernames:
        data["group"].append(username)

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
            await ctx.respond(f"`{username}` does not have any cached submissions, caching now")
            await query.get_submissions(username)

    for i, types in enumerate(important_types):
        total_problems = await query.get_problems(_type=types, cached=True)
        total_points = list(map(attrgetter("points"), total_problems))
        total_points.sort(reverse=True)
        total_points = calculate_partial_points(total_points)

        for username in usernames:
            points = query.get_attempted_problems(username, types)

            points.sort(reverse=True)

            points = calculate_partial_points(points)
            if as_percent:
                percentage = 100 * points / total_points
            else:
                percentage = points
            max_percentage = max(max_percentage, percentage)
            data[labels[i]].append(percentage)

    logger.debug("plot type data: %s", data)

    if graph_type == "radar":
        plot_type_radar(data, as_percent, max_percentage)
    elif graph_type == "bar":
        plot_type_bar(data, as_percent)

    embed = hikari.Embed(
        title="Problem types solved",
        color=0xFCDB05,
    )
    with open("./graphs/plot.png", "rb") as file:
        embed.set_image(hikari.Bytes(file.read(), "plot.png"))

    return await ctx.respond(embed=embed)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
