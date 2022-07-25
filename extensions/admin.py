from utils.api import ObjectNotFound
import lightbulb
import hikari
from pathlib import Path
from utils.db import session, Contest as Contest_DB, Problem as Problem_DB, Submission as Submission_DB
from utils.query import Query
from operator import itemgetter
import time
import logging
import traceback

logger = logging.getLogger(__name__)


plugin = lightbulb.Plugin("Admin")
plugin.add_checks(lightbulb.checks.owner_only)
# NOTE: REMOVE SLASH COMMANDS UNTIL SLASH PERMS V2 COME OUT


@plugin.listener(lightbulb.PrefixCommandCompletionEvent)
async def on_prefix_command(event: lightbulb.PrefixCommandCompletionEvent) -> None:
    server = event.context.get_guild().name
    user = event.context.author
    command = event.context.command.name
    logger.info("+%s used by %s in %s", command, user, server)


@plugin.listener(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent) -> None:
    try:
        logger.warning("Error handling: raised %s", event)
        if isinstance(event.exception, lightbulb.NotEnoughArguments):
            return await event.context.respond(f"Not enough arguments ({event.exception})")
        if isinstance(event.exception, lightbulb.CommandInvocationError):
            if isinstance(event.exception.original, hikari.ForbiddenError):
                return await event.context.respond(
                    f"I do not have permissions to do this ({event.exception.original.message})"
                )
        if isinstance(event.exception, lightbulb.CommandNotFound):
            return await event.context.respond(f"Where command? ({event.exception})")

        if isinstance(event.exception, lightbulb.errors.MissingRequiredRole):
            return await event.context.respond(f"Missing required roles ({event.exception})")

        if isinstance(event.exception, lightbulb.errors.NotOwner):
            return await event.context.respond("You are not the owner of this bot!")

        trace = "".join(traceback.format_exception(None, event.exception, event.exception.__traceback__))
        await event.context.respond(
            """Unhandled exception ({0})
Backtrace:""".format(
                event.exception
            ),
            attachment=hikari.Bytes(trace, "traceback.txt"),
        )
    except Exception as e:
        logger.critical("Error handling raised error: was handling %s, raised %s", event, e)
        await event.context.respond("Crtitical error encountered, check logs")


@plugin.listener(lightbulb.SlashCommandCompletionEvent)
async def on_slash_command(event: lightbulb.SlashCommandCompletionEvent) -> None:
    server = event.context.get_guild().name
    user = event.context.author
    command = event.context.command.name
    logger.info("/%s used by %s in %s", command, user, server)


@plugin.command()
@lightbulb.command("reload_all", "Reload all extensions")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def reload_all(ctx: lightbulb.Context) -> None:
    try:
        extensions = [file.stem for file in Path("extensions").glob("*.py")]
        for extension in extensions:
            ctx.bot.reload_extensions(f"extensions.{extension}")
    except lightbulb.ExtensionNotLoaded as e:
        await ctx.respond(f"{e.__class__.__name__}: {e}")
    else:
        await ctx.respond("All extensions have been reloaded")


@plugin.command()
@lightbulb.option("key", "key/id of problem or contest", str)
@lightbulb.option("type", "Thing to recache", choices=["contest", "problem"])
@lightbulb.command("force", "Force a recache of a problem, or contest")
@lightbulb.implements(lightbulb.PrefixCommand)
async def force(ctx: lightbulb.Context) -> None:
    if ctx.options.type.lower() == "contest":
        q = session.query(Contest_DB).filter(Contest_DB.key == ctx.options.key)
        if q.count() == 0:
            await ctx.respond(
                f"There is no contests with the key {ctx.options.key} " f"cached. Will try fetching contest"
            )
        else:
            q.delete()
            session.commit()
        query = Query()
        try:
            await query.get_contest(ctx.options.key)
        except ObjectNotFound:
            return await ctx.respond("Contest not found")
        await ctx.respond(f"Recached contest {ctx.options.key}")
    if ctx.options.type.lower() == "problem":
        q = session.query(Problem_DB).filter(Problem_DB.code == ctx.options.key)
        if q.count() == 0:
            await ctx.respond(
                f"There is no problems with the key {ctx.options.key} " f"cached. Will try fetching problem"
            )
        else:
            q.delete()
            session.commit()
        query = Query()
        try:
            await query.get_problem(ctx.options.key)
        except ObjectNotFound:
            return await ctx.respond("Problem not found")
        await ctx.respond(f"Recached problem {ctx.options.key}")
    else:
        await ctx.send_help()


@plugin.command()
@lightbulb.command("cache_contests", "Cache every contest")
@lightbulb.implements(lightbulb.PrefixCommand)
async def cache_contests(ctx: lightbulb.Context) -> None:
    # TODO Add live counter
    query = Query()
    msg = await ctx.respond("Caching...")
    contests = await query.get_contests()
    for contest in contests:
        await query.get_contest(contest.key)
    return await msg.edit(content=f"Cached {len(contests)} contests")


@plugin.command()
@lightbulb.command("update_problems", "Clears problem table and recaches problems")
@lightbulb.implements(lightbulb.PrefixCommand)
async def update_problems(ctx: lightbulb.Context) -> None:
    """Update all problems in db (For when Nick nukes problems)"""
    # TODO Add live counter
    msg = await ctx.respond("Updating...")
    session.query(Problem_DB).delete()
    session.commit()
    query = Query()
    await query.get_problems()
    return await msg.edit(content="Updated all problems")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
