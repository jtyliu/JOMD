import typing as t
from utils.gitgud import GitgudUtils
from utils.query import Query
from utils.constants import SHORTHANDS, RATING_TO_POINT, POINT_VALUES
from utils.jomd_common import gimme_common, PointRangeConverter
from utils.models import *
import lightbulb
from lightbulb.converters import base
from lightbulb.commands.base import OptionModifier
import hikari
from lightbulb.utils import nav
from datetime import datetime
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


plugin = lightbulb.Plugin("GitGud")


@plugin.command()
@lightbulb.option("filters", "Problem filters", str, required=False, modifier=OptionModifier.GREEDY, default=[])
@lightbulb.option(
    "points",
    "point range, e.g. ('1', '1-10') DOES NOT WORK WITH SLASH COMMANDS",
    PointRangeConverter,
    required=False,
    default=None,
)
@lightbulb.set_help(
    """SHORTHANDS:
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
)
@lightbulb.command("gitgud", "Recommend a problem and gain point upon completion")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def gitgud(ctx: lightbulb.Context) -> None:
    # TODO Fix converters for slash commands
    points = ctx.options.points
    filters = ctx.options.filters
    query = Query()
    gitgud_util = GitgudUtils()
    # get the user's dmoj handle
    username = query.get_handle(ctx.author.id, ctx.get_guild().id)
    # user = await query.get_user(username)

    if username is None:
        return await ctx.respond("You are not linked to a DMOJ Account. " "Please link your account before continuing")

    user = await query.get_user(username)

    if points is None:
        points = [0, 0]
        closest = -1000
        for key in RATING_TO_POINT:
            if abs(key - user.rating) <= abs(closest - user.rating):
                closest = key
        points[0] = RATING_TO_POINT[closest]
        points[1] = points[0]
    # return if the user haven't finished the previous problem
    current = gitgud_util.get_current(username, ctx.get_guild().id)

    if current is not None and current.problem_id is not None:
        if not gitgud_util.has_solved(username, current.problem_id):
            # User has a current problem unsolved
            problem = await query.get_problem(current.problem_id)
            embed = hikari.Embed(
                description=f"You currently have an uncompleted "
                f"challenge, [{problem.name}]"
                f"(https://dmoj.ca/problem/{problem.code})",
                color=0xFCDB05,
            )
            return await ctx.respond(embed=embed)

    filter_list = []
    for filter in filters:
        if filter in SHORTHANDS:
            filter_list+=SHORTHANDS[filter]

    filters = filter_list

    embed, problem = await gimme_common(username, points, filters)

    if embed is None:
        return await ctx.respond("No problems that satisfies the filter")

    gitgud_util.bind(username, ctx.get_guild().id, problem.code, problem.points, datetime.now())

    embed.description = "Points: %s\nProblem Types ||%s||" % (problem.points, ", ".join(problem.types))

    return await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.command("nogud", "Cancels any unfinished challenge")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def nogud(ctx):
    query = Query()
    gitgud_util = GitgudUtils()

    username = query.get_handle(ctx.author.id, ctx.get_guild().id)

    if username is None:
        return await ctx.respond("You do not have a linked DMOJ account")

    current = gitgud_util.get_current(username, ctx.get_guild().id)
    if current is None or current.problem_id is None:
        return await ctx.respond("Nothing to cancel")

    gitgud_util.clear(username, ctx.get_guild().id)
    return await ctx.respond("Challenge skipped")


# TODO Make a DmojUserConverter


@plugin.command()
@lightbulb.option("username", "Dmoj username", str, required=False, default=None)
@lightbulb.command("gitlog", "Cancels any unfinished challenge")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def gitlog(ctx):
    """
    Show the past gitgud history of a user
    """
    query = Query()
    username = ctx.options.username
    username = username or query.get_handle(ctx.author.id, ctx.get_guild().id)
    try:
        user = await query.get_user(username)
        username = user.username
    except TypeError:
        username = None
    if username is None:
        return await ctx.respond("You have not entered a valid DMOJ handle " "or linked with a DMOJ Account")

    gitgud_util = GitgudUtils()
    history = gitgud_util.get_all(username, ctx.get_guild().id)

    if len(history) == 0:
        embed = hikari.Embed(description="User have not completed any " "challenge")
        return await ctx.respond(embed=embed)
    # paginate

    pag = lightbulb.utils.EmbedPaginator()
    for idx, solved in enumerate(history):
        # problem = solved.problem_id or await query.get_problem(solved.problem_id)
        problem = await query.get_problem(solved.problem_id)
        days = (datetime.now() - solved.time).days
        if days == 0:
            days_str = "today"
        elif days == 1:
            days_str = "yesterday"
        else:
            days_str = f"{days} days ago"
        pag.add_line(f"[{problem.name}](https://dmoj.ca/problem/{problem.code}) " f"[+{solved.point}] ({days_str})")
        if idx == 100:
            break

    @pag.embed_factory()
    def build_embed(page_index, content):
        return hikari.Embed(color=0xFCDB05,).add_field(
            name=f"Gitgud Log for {username} " f"(page {page_index})",  # Can't put total length :/
            value=content,
            inline=True,
        )

    navigator = nav.ButtonNavigator(pag.build_pages())
    await navigator.run(ctx)


@plugin.command()
@lightbulb.command("gotgud", "Mark challenge as complete")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def gotgud(ctx):
    query = Query()
    gitgud_util = GitgudUtils()
    username = query.get_handle(ctx.author.id, ctx.get_guild().id)

    if username is None:
        return await ctx.respond("You are not linked with a DMOJ Account")

    user = await query.get_user(username)
    current = gitgud_util.get_current(username, ctx.get_guild().id)
    closest = -1000
    for key in RATING_TO_POINT:
        if abs(key - user.rating) <= abs(closest - user.rating):
            closest = key

    # convert rating to point and get difference
    rating_point = RATING_TO_POINT[closest]
    if current is None or current.problem_id is None:
        return await ctx.respond("No pending challenges")

    # check if user is scamming the bot :monkey:
    if gitgud_util.has_solved(username, current.problem_id):
        # get closest rating
        closest = -1000
        for key in RATING_TO_POINT:
            if abs(key - user.rating) <= abs(closest - user.rating):
                closest = key
        # convert rating to point and get difference
        rating_point = RATING_TO_POINT[closest]
        point_diff = POINT_VALUES.index(current.point) - POINT_VALUES.index(rating_point)

        point = 10 + 2 * (point_diff)
        point = max(point, 0)

        gitgud_util.insert(username, ctx.get_guild().id, point, current.problem_id, datetime.now())
        gitgud_util.clear(username, ctx.get_guild().id)

        completion_time = datetime.now() - current.time
        # convert from timedelta to readable string
        ret = ""
        cnt = 0
        if completion_time.days // 365 != 0:
            ret += f" {completion_time.days // 365} years"
            cnt += 1
        if completion_time.days % 365 != 0:
            ret += f" {completion_time.days % 365} days"
            cnt += 1
        if completion_time.seconds // 3600 != 0:
            ret += f" {completion_time.seconds // 3600} hours"
            cnt += 1
        if cnt < 3 and completion_time.seconds % 3600 // 60 != 0:
            ret += f" {completion_time.seconds % 3600 // 60} minutes"
            cnt += 1
        if cnt < 3 and completion_time.seconds % 60 != 0:
            ret += f" {completion_time.seconds % 60} seconds"

        return await ctx.respond(f"Challenge took{ret}. " f"{current.handle} gained {point} points")

    else:
        return await ctx.respond("You have not completed the challenge")


@plugin.command()
@lightbulb.option("username", "Dmoj username", str, required=False, default=None)
@lightbulb.command("howgud", "Returns total amount of gitgud points")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def howgud(ctx):
    username = ctx.options.username
    query = Query()
    if username is None:
        username = query.get_handle(ctx.author.id, ctx.get_guild().id)
    user = await query.get_user(username)
    username = user.username
    ret = GitgudUtils().get_point(username, ctx.get_guild().id)
    if ret is None:
        ret = 0
    # TODO Add profile pic?
    embed = hikari.Embed(
        title=username,
        description=f"points: {ret}",
        color=0xFCDB05,
    )
    return await ctx.respond(embed=embed)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
