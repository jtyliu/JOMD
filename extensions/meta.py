import lightbulb
import hikari
from utils.query import Query
from utils.api import API
from utils.models import *
from utils.jomd_common import calculate_points
import typing


plugin = lightbulb.Plugin("Meta")


@plugin.command()
@lightbulb.option("username", "Dmoj username to cache", str, required=False)
@lightbulb.set_help("Use surround your username with '' if it can be interpreted as a number")
@lightbulb.command("cache", "Caches the submissions of a user, will speed up other commands")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def cache(ctx: lightbulb.Context) -> None:
    query = Query()
    username = ctx.options.username or query.get_handle(ctx.author.id, ctx.get_guild().id)

    if username is None:
        return await ctx.respond("No username given!")

    username = username.replace("'", "")

    user = await query.get_user(username)
    if user is None:
        return await ctx.respond(f"{username} does not exist on DMOJ")

    username = user.username

    msg = await ctx.respond(f"Caching {username}'s submissions")
    session.query(Submission).filter(Submission.user_id == user.id).delete()
    await query.get_submissions(username)
    return await msg.edit(content=f"{username}'s submissions " + "have been cached")


@plugin.command()
@lightbulb.command("check", "Perform sanity check on bot")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def check(ctx: lightbulb.Context) -> None:
    api = API()
    await api.get_user("JoshuaL")
    user = api.data.object
    if user is None:
        await ctx.respond("There is something wrong with the api, " "please contact an admin")
    else:
        await ctx.respond("Api is all good, move along")


@plugin.command()
@lightbulb.command("info", "Who asked?")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def info(ctx: lightbulb.Context) -> None:
    """Bot info"""
    guildCount = len(ctx.app.cache.get_guilds_view())
    userCount = len(set(ctx.app.cache.get_users_view()))
    embed = (
        hikari.Embed(color=0xFFFF00)
        .set_author(name=str(ctx.app.get_me()), icon=ctx.app.get_me().display_avatar_url)
        .add_field(name="Guilds:", value=guildCount, inline=True)
        .add_field(name="Users:", value=userCount, inline=True)
        .add_field(
            name="Invite",
            value="[Invite link](https://discord.com/api/oauth2/" + "authorize?client_id=725004198466551880&scope=bot)",
            inline=False,
        )
        .add_field(name="Github", value="[Github link](https://github.com/JoshuaTianYangLiu/JOMD)", inline=False)
        .add_field(name="Support", value="[Server link](https://discord.gg/VEWFpgPhnz)", inline=False)
    )
    await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.command("stats", "Who asked?")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stats(ctx: lightbulb.Context) -> None:
    problems = session.query(Problem.points).order_by(Problem.points.desc()).all()

    def tuple_first(data):
        return data[0]

    problems = list(map(tuple_first, problems))
    total_problems = len(problems)
    total_points = calculate_points(problems, total_problems)
    await ctx.respond(
        "The theoretical maximum number of points you can achieve is %.2f\n"
        "There are %d public problems on DMOJ" % (total_points, total_problems)
    )


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
