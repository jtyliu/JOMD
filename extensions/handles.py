import functools
from utils.api import ObjectNotFound
from operator import itemgetter
from utils.query import Query
from utils.models import *
from utils.constants import RATING_TO_RANKS, RANKS, ADMIN_ROLES
from lightbulb.utils import nav
import typing as t
from sqlalchemy import func
import asyncio
import hashlib
import lightbulb
import hikari
import re
import logging

logger = logging.getLogger(__name__)

# https://github.com/Rapptz/discord.py/blob/master/discord/utils.py
_MARKDOWN_ESCAPE_COMMON = r"^>(?:>>)?\s|\[.+\]\(.+\)"

_MARKDOWN_STOCK_REGEX = rf"(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})"

_URL_REGEX = r"(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])"


def escape_markdown(text: str, *, ignore_links: bool = True) -> str:
    """A helper function that escapes Discord's markdown"""

    def replacement(match):
        groupdict = match.groupdict()
        is_url = groupdict.get("url")
        if is_url:
            return is_url
        return "\\" + groupdict["markdown"]

    regex = _MARKDOWN_STOCK_REGEX
    if ignore_links:
        regex = f"(?:{_URL_REGEX}|{regex})"
    return re.sub(regex, replacement, text, 0, re.MULTILINE)


def has_any_role_names(role_names: t.List[str]) -> bool:
    def _has_any_role_names(ctx: lightbulb.Context, *, role_names: t.List[str]):
        assert ctx.member is not None

        if any(role.name in role_names for role in ctx.member.get_roles()):
            return True
        raise lightbulb.errors.MissingRequiredRole(
            "You are missing the roles required in order to run this command %s" % role_names
        )

    return lightbulb.Check(functools.partial(_has_any_role_names, role_names=role_names))


plugin = lightbulb.Plugin("Handles")


@plugin.command()
@lightbulb.option(
    "handle",
    "Dmoj handle",
    str,
    required=False,
    default=None,
)
@lightbulb.option("member", "Discord user", hikari.Member, required=False, default=None)
@lightbulb.command("whois", "Lookup linked account")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def whois(ctx):
    member = ctx.options.member
    handle = ctx.options.handle

    query = Query()
    username, linked_username, pfp = None, None, None
    if handle:
        user = None
        try:
            user = await query.get_user(handle)
        except ObjectNotFound:
            username = None
        if user:
            handle = user.username
            author_id = query.get_handle_user(handle, ctx.get_guild().id)
            username = handle
            if author_id:
                member = ctx.get_guild().get_member(author_id)
                linked_username = member.nickname or member.name
                pfp = member.avatar_url
    elif member:
        handle = query.get_handle(member.id, ctx.get_guild().id)
        username = member.nickname or member.name
        if handle:
            linked_username = handle
            pfp = await query.get_pfp(handle)
    if linked_username:
        embed = hikari.Embed(
            color=0xFCDB05,
            title=escape_markdown(f"{username} is {linked_username}"),
        )
        embed.set_thumbnail(pfp)
        return await ctx.respond(embed=embed)
    elif username:
        embed = hikari.Embed(
            title=escape_markdown(f"{username} is not linked with any account here"),
            color=0xFCDB05,
        )
        return await ctx.respond(embed=embed)

    name = None
    if member:
        name = member.nickname or member.name
    embed = hikari.Embed(
        title=escape_markdown(f"Nothing found on {handle or name}"),
        color=0xFCDB05,
    )
    await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.command("unlink", "Unlink your discord account from your dmoj account")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def unlink(ctx: lightbulb.Context) -> None:
    # TODO: Add admin ability to manually unlink
    query = Query()
    if not query.get_handle(ctx.author.id, ctx.get_guild().id):
        await ctx.respond("You are not linked with any user")
        return
    handle = session.query(Handle)\
        .filter(Handle.id == ctx.author.id)\
        .filter(Handle.guild_id == ctx.guild.id).first()
    session.delete(handle)
    session.commit()
    await ctx.respond(escape_markdown(f"Unlinked you with handle {handle.handle}"))


@plugin.command()
@lightbulb.option("username", "Dmoj username", str)
@lightbulb.command("link", "Link your discord account to your dmoj account")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def link(ctx: lightbulb.Context) -> None:
    username = ctx.options.username
    # Check if user exists
    query = Query()
    user = await query.get_user(username)

    if user is None:
        await ctx.respond(escape_markdown(f"{username} does not exist on DMOJ"))
        return

    username = user.username

    if query.get_handle(ctx.author.id, ctx.get_guild().id):
        await ctx.respond(
            "%s, your handle is already linked with %s."
            % (ctx.author.mention, query.get_handle(ctx.author.id, ctx.get_guild().id))
        )
        return

    if query.get_handle_user(username, ctx.get_guild().id):
        await ctx.respond("This handle is already linked with another user")
        return

    # verify from dmoj user description
    description = await query.get_user_description(username)
    userKey = hashlib.sha256(str(ctx.author.id).encode()).hexdigest()
    if userKey not in description:
        await ctx.respond(
            "Put `" + userKey + "` in your DMOJ user description (https://dmoj.ca/edit/profile/) "
            "and run the command again."
        )
        return

    handle = Handle()
    handle.id = ctx.author.id
    handle.handle = username
    handle.user_id = user.id
    handle.guild_id = ctx.get_guild().id
    session.add(handle)
    session.commit()
    await ctx.respond(escape_markdown("%s, you now have linked your account to %s" % (ctx.author, username)))

    rank_to_role = {}
    rc = lightbulb.RoleConverter(ctx)
    for role_id in ctx.get_guild().get_roles():
        role = await rc.convert(str(role_id))
        if role.name in RANKS:
            rank_to_role[role.name] = role

    rank = rating_to_rank(user.rating)
    # TODO Add guild specific option to disable updating roles
    if rank in rank_to_role:
        await _update_rank(ctx.member, rank_to_role[rank], "Dmoj account linked")
    else:
        await ctx.respond("You are missing the `" + rank.name + "` role")


@plugin.command()
@lightbulb.add_checks(has_any_role_names(ADMIN_ROLES))
@lightbulb.option("handle", "Dmoj handle", str)
@lightbulb.option("member", "Discord user or [+remove] to force unlink", hikari.Member)
@lightbulb.command("set", "Manually link two accounts together")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def _set(ctx):
    """Manually link two accounts together"""
    # TODO: I don't like the bot spamming replies to itself, figure out a way to lessen that
    member = ctx.options.member
    username = ctx.options.handle
    query = Query()

    if username != "+remove":
        user = await query.get_user(username)

        if user is None:
            await ctx.respond(escape_markdown(f"{username} does not exist on dmoj"))
            return

        username = user.username

    handle = query.get_handle(member.id, ctx.get_guild().id)
    if handle == username:
        return await ctx.respond(escape_markdown(f"{member.display_name} is already linked with {handle}"))

    if handle:
        handle = session.query(Handle)\
            .filter(Handle.id == member.id)\
            .filter(Handle.guild_id == ctx.guild.id).first()
        session.delete(handle)
        session.commit()
        await ctx.respond(escape_markdown(f"Unlinked {member.display_name} with handle {handle.handle}"))

    if username == "+remove":
        return

    if query.get_handle_user(username, ctx.get_guild().id):
        await ctx.respond("This handle is already linked with another user")
        return

    handle = Handle()
    handle.id = member.id
    handle.handle = username
    handle.user_id = user.id
    handle.guild_id = ctx.get_guild().id
    session.add(handle)
    session.commit()
    await ctx.respond(escape_markdown(f"Linked {member.display_name} with {username}"))

    rank_to_role = {}
    rc = lightbulb.RoleConverter(ctx)
    for role_id in ctx.get_guild().get_roles():
        role = await rc.convert(str(role_id))
        if role.name in RANKS:
            rank_to_role[role.name] = role

    rank = rating_to_rank(user.rating)
    if rank in rank_to_role:
        await _update_rank(member, rank_to_role[rank], "Dmoj account linked")
    else:
        await ctx.respond("You are missing the `" + rank.name + "` role")


@plugin.command()
@lightbulb.option(
    "arg",
    "[rating|maxrating|points|solved]",
    str,
    required=False,
    choices=["rating", "maxrating", "points", "solved"],
    default="rating",
)
@lightbulb.command(
    "top", "Shows registered server members in ranked order (Adelaide Command)", aliases=["users", "leaderboard"]
)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def top(ctx):
    """Shows registered server members in ranked order"""
    arg = ctx.options.arg.lower()
    if arg != "rating" and arg != "maxrating" and arg != "points" and arg != "solved":
        return await ctx.respond_help("top")
    users = (
        session.query(User)
        .join(Handle, Handle.handle == User.username)
        .filter(Handle.guild_id == ctx.get_guild().id)
    )
    leaderboard = []
    for user in users:
        if arg == "rating":
            leaderboard.append([-(user.rating or -9999), user.username])
        elif arg == "maxrating":
            leaderboard.append([-(user.max_rating or -9999), user.username])
        elif arg == "points":
            leaderboard.append([-user.performance_points, user.username])
        elif arg == "solved":
            leaderboard.append([-(user.problem_count or 0), user.username])
    leaderboard.sort()
    pag = lightbulb.utils.EmbedPaginator()
    for i, user in enumerate(leaderboard):
        if (arg == "rating" or arg == "maxrating") and user[0] == 9999:
            pag.add_line(f"{i+1} {user[1]} unrated")
        else:
            pag.add_line(f"{i+1} {user[1]} {-round(user[0],3)}")

    if len(leaderboard) == 0:
        pag.add_line("No users")

    @pag.embed_factory()
    def build_embed(page_index, content):
        return hikari.Embed().add_field(name="Top DMOJ " + arg, value=content)

    navigator = nav.ButtonNavigator(pag.build_pages())
    await navigator.run(ctx)


def rating_to_rank(rating):
    if rating is None:
        return RANKS[0]  # Unrated
    for rank in RATING_TO_RANKS:
        if rank[0] <= rating < rank[1]:
            return RATING_TO_RANKS[rank]


async def _update_rank(member: hikari.Member, role: hikari.Role, reason: str):
    add_role = all([role.name != cur_role.name for cur_role in member.get_roles()])
    to_remove = []
    for cur_role in member.get_roles():
        if role.name != cur_role.name and cur_role.name in RANKS:
            to_remove.append(cur_role)
    if len(to_remove) != 0:
        for r in to_remove:
            await member.remove_role(r, reason=reason)
    if add_role:
        await member.add_role(role, reason=reason)


@plugin.command()
@lightbulb.add_checks(has_any_role_names(ADMIN_ROLES))
@lightbulb.command("update_roles", "Manually update roles")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def update_roles(ctx):
    """Manually update roles"""
    # Big problem, I stored rankings column in Contest table as Json instead of using foreign keys to participation
    # TODO: Migrate to work with participation table

    msg = await ctx.respond("Fetching ratings...")

    q = session.query(User.username, Participation.user_id, func.max(Contest.end_time).label('end_time')).\
        join(Participation.contest).\
        join(Participation.user).\
        filter(Participation.new_rating != None).\
        filter(Handle.guild_id == ctx.get_guild().id).\
        group_by(Participation.user_id).subquery()

    q = session.query(Handle.id, Participation.new_rating).\
        join(Participation.contest).\
        join(Handle, Handle.user_id == Participation.user_id).\
        join(q, q.c.user_id == Participation.user_id).\
        filter(q.c.end_time == Contest.end_time).\
        filter(Contest.is_rated == 1).\
        filter(Handle.guild_id == ctx.get_guild().id)

    rating = {handle_id: new_rating for (handle_id, new_rating) in q}

    handle_ids = session.query(Handle.id).filter(Handle.guild_id == ctx.get_guild().id).all()
    members = {handle_id: ctx.guild.get_member(handle_id) for (handle_id,) in handle_ids}

    rank_to_role = {role.name: role for role in ctx.guild.roles if role.name in RANKS}

    await msg.edit(content="Updating roles...")

    missing_roles = []

    for (handle_id, member) in members.items():
        new_rating = rating.get(handle_id, None)
        rank = rating_to_rank(new_rating)
        if rank in rank_to_role:
            await _update_rank(member, rank_to_role[rank], 'Dmoj rank update')
        elif rank not in missing_roles:
            missing_roles.append(rank)

    if len(missing_roles) != 0:
        await ctx.respond("You are missing the " + ", ".join(missing_roles) + " roles")
    await msg.edit(content="Roles updated")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
