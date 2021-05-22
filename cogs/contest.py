from utils.jomd_common import scroll_message
from utils.constants import SITE_URL
from utils.db import (session, Problem as Problem_DB,
                      Contest as Contest_DB,
                      Participation as Participation_DB,
                      User as User_DB, Submission as Submission_DB,
                      Organization as Organization_DB,
                      Language as Language_DB, Judge as Judge_DB,
                      Handle as Handle_DB, Json)
from utils.query import Query
from utils.api import ObjectNotFound
import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timezone
from sqlalchemy import orm
import asyncio
from operator import itemgetter, attrgetter

# Post new contests
# Rating change predictions for all users in a server


class Contest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["contest"], usage="[contest key] [+server, +all, dmoj_handles]")
    async def ranklist(self, ctx, key, *args):
        """List rating predictions of a contest"""
        q = session.query(Contest_DB).filter(Contest_DB.key == key)
        # Clear cache
        if q.count():
            q.delete()
            session.commit()
        query = Query()
        try:
            contest = await query.get_contest(key)
        except ObjectNotFound:
            await ctx.send("Contest not found")
            return

        q = session.query(Handle_DB).filter(Handle_DB.guild_id == ctx.guild.id)
        handles = q.all()

        usernames = []
        showAll = False
        if len(args) == 0:
            usernames += list(map(attrgetter('handle'), handles))
        for arg in args:
            arg = arg.lower()
            if arg == "+server":
                usernames += list(map(attrgetter('handle'), handles))
            elif arg == "+all":
                showAll = True
            else:
                usernames.append((await query.get_user(arg)).username)

        # The only way to calculate rating changes is by getting the volitility of all the users
        # that means 100+ seperate api calls
        # How does evan do it?
        import requests
        r = requests.get(f"https://evanzhang.ca/rating/contest/{key}/api")
        if r:
            rankings = r.json()["users"]

        # Don't really need this, just sanity check
        # users = await asyncio.gather(*[query.get_user(username)
        #                              for username in users])
        # usernames = [user.username for user in users]
        # Filter for those who participated in contest
        user_rankings = list(map(itemgetter("user"), contest.rankings))
        if showAll:
            usernames = list(set(user_rankings))
        else:
            usernames = list(set(usernames) & set(user_rankings))

        # The length is 0 is contest is still ongoing
        problems = len(contest.problems)

        data = []

        for rank_num, ranking in enumerate(contest.rankings):
            # TODO: ok ish, but placements match the rankings
            for username in usernames:
                if ranking["user"] == username:
                    # If contest is not rated, this crashes
                    if contest.is_rated:
                        evan_ranking = rankings[username]
                        rank_dict = {
                            "rank": int(evan_ranking["rank"]),
                            "username": username + ":",
                            "old_rating": evan_ranking["old_rating"],
                            "new_rating": evan_ranking["new_rating"],
                        }
                        if evan_ranking["rating_change"] and evan_ranking["rating_change"] > 0:
                            rank_dict["rating_change"] = "+" + str(evan_ranking["rating_change"])
                        else:
                            rank_dict["rating_change"] = evan_ranking["rating_change"]
                    else:
                        rank_dict = {
                            "rank": rank_num + 1,
                            "username": username + ":",
                        }
                    # This is a quick fix :>
                    problems = len(ranking["solutions"])
                    for i in range(1, problems + 1):
                        solution = ranking["solutions"][i - 1]
                        if solution:
                            rank_dict[str(i)] = int(solution["points"])
                        else:
                            rank_dict[str(i)] = '-'
                    data.append(rank_dict)
        max_len = {}
        max_len["rank"] = len("#")
        max_len["username"] = len("Handle")
        for i in range(1, problems + 1):
            max_len[str(i)] = len(str(i))
        max_len["rating_change"] = max_len["old_rating"] = max_len["new_rating"] = 3

        for rank in data:
            for k, v in rank.items():
                max_len[k] = max(len(str(v)), max_len.get(k, 0))

        format_output = "{:>" + str(max_len["rank"]) + "} "
        format_output += "{:" + str(max_len["username"] + 1) + "}  "
        for i in range(1, problems + 1):
            format_output += "{:" + str(max_len[str(i)]) + "} "

        to_format = [
            "#",
            "Handle",
            *[str(i) for i in range(1, problems + 1)],
        ]

        hyphen_format = [
            "—" * max_len["rank"],
            "—" * max_len["username"],
            *["—" * max_len[str(i)] for i in range(1, problems + 1)],
        ]
        if contest.is_rated:
            format_output += " "
            format_output += "{:>" + str(max_len["rating_change"]) + "}  "
            format_output += "{:" + str(max_len["old_rating"]) + "} "
            format_output += "{:" + str(max_len["new_rating"]) + "} "
            to_format += [
                "∆",
                "Old",
                "New",
            ]

            hyphen_format += [
                "—" * max_len["rating_change"],
                "—" * max_len["old_rating"],
                "—" * max_len["new_rating"],
            ]
        outputBegin = format_output.format(*to_format)
        outputBegin += "\n"
        hyphens = format_output.format(*hyphen_format)
        outputBegin += hyphens
        outputBegin += "\n"
        outputEnd = hyphens + "\n"

        content = []
        output = outputBegin
        for rank in data:
            if contest.is_rated:
                output += format_output.format(
                    rank["rank"],
                    rank["username"],
                    *[rank[str(i)] for i in range(1, problems + 1)],
                    str(rank["rating_change"]),
                    str(rank["old_rating"]),
                    str(rank["new_rating"]),
                )
            else:
                output += format_output.format(
                    rank["rank"],
                    rank["username"],
                    *[rank[str(i)] for i in range(1, problems + 1)],
                )
            output += "\n"
            if(len(output) + len(outputEnd) * 2 > 1980):
                output += outputEnd
                content.append("```yaml\n" + output + "```")
                output = outputBegin
        output += outputEnd
        content.append("```yaml\n" + output + "```")
        await ctx.send("Results for " + contest.name + "(" + SITE_URL + "contest/" + key + "): ")
        message = await ctx.send(content[0])
        await scroll_message(ctx, self.bot, message, content)

    @commands.command(aliases=['pc'], usage="[contest key]")
    async def postcontest(self, ctx, key):
        """Updates post-contest role"""

        query = Query()

        username = query.get_handle(ctx.author.id, ctx.guild.id)

        if username is None:
            return await ctx.send("Your account is not linked!")

        q = session.query(Contest_DB).filter(Contest_DB.key == key)
        # Clear cache
        if q.count():
            q.delete()
            session.commit()
        try:
            contest = await query.get_contest(key)
        except ObjectNotFound:
            await ctx.send("Contest not found")
            return

        role = get(ctx.guild.roles, name="postcontest " + key)
        if not role:
            return await ctx.send(f"No `postcontest {key}` role found.")

        for ranking in contest.rankings:
            if ranking['user'] != username:
                continue

            endTime = datetime.strptime(ranking['end_time'], '%Y-%m-%dT%H:%M:%S%z')
            if endTime > datetime.now(timezone.utc).astimezone():
                return ctx.send("Your window is not done.")
            else:
                try:
                    await ctx.author.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send("No permission to assign the role.")
                return await ctx.send("You've been added to post contest.")


def setup(bot):
    bot.add_cog(Contest(bot))
