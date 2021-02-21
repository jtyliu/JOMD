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
from datetime import datetime
from sqlalchemy import orm
import asyncio
from operator import itemgetter

# Post new contests
# Rating change predictions for all users in a server

class Contest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(usage="[contest key]")
    async def ranklist(self, ctx, key):
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

        def to_handle(handle):
            return handle.handle

        usernames = list(map(to_handle, handles))
        
        # The only way to calculate rating changes is by getting the volitility of all the users
        # that means 100+ seperate api calls
        # How does evan do it?
        import requests
        r = requests.get(f"https://evanzhang.ca/rating/contest/{key}/api")
        rankings = r.json()["users"]

        # Don't really need this, just sanity check
        # users = await asyncio.gather(*[query.get_user(username)
        #                              for username in users])
        # usernames = [user.username for user in users]
        # Filter for those who participated in contest
        usernames = list(set(usernames) & set(rankings.keys()))
        
        # The length is 0 is contest is still ongoing
        problems = len(contest.problems)
        print(usernames)
        data = []
        for ranking in contest.rankings:
            for username in usernames:
                if ranking["user"] == username:
                    evan_ranking = rankings[username]
                    rank = {
                        "rank": int(evan_ranking["rank"]),
                        "username": username+":",
                        "old_rating": evan_ranking["old_rating"],
                        "new_rating": evan_ranking["new_rating"],
                    }
                    if evan_ranking["rating_change"] > 0:
                        rank["rating_change"] = "+"+str(evan_ranking["rating_change"])
                    else:
                        rank["rating_change"] = evan_ranking["rating_change"]
                    # This is a quick fix :>
                    problems = len(ranking["solutions"])
                    for i in range(1, problems+1):
                        solution = ranking["solutions"][i-1]
                        if solution:
                            rank[str(i)] = int(solution["points"])
                        else:
                            rank[str(i)] = 0
                    data.append(rank)
        max_len = {}
        max_len["rank"] = len("#")
        max_len["username"] = len("Handle")

        for rank in data:
            for k, v in rank.items():
                max_len[k] = max(len(str(v)), max_len.get(k, 0))

        format_output = "{:>"+str(max_len["rank"])+"} "
        format_output += "{:"+str(max_len["username"]+1)+"}  "
        for i in range(1, problems+1):
            format_output += "{:"+str(max_len[str(i)])+"} "

        format_output += " "
        format_output += "{:>"+str(max_len["rating_change"])+"}  "
        format_output += "{:"+str(max_len["old_rating"])+"} "
        format_output += "{:"+str(max_len["new_rating"])+"} "
        output = format_output.format(
            "#",
            "Handle",
            *[str(i) for i in range(1, problems+1)],
            "∆",
            "Old",
            "New"
        )
        output += "\n"
        hyphens = format_output.format(
            "—"*max_len["rank"],
            "—"*max_len["username"],
            *["—"*max_len[str(i)] for i in range(1, problems+1)],
            "—"*max_len["rating_change"],
            "—"*max_len["old_rating"],
            "—"*max_len["new_rating"],
        )
        output += hyphens
        output += "\n"
        for rank in data:
            output += format_output.format(
                rank["rank"],
                rank["username"],
                *[rank[str(i)] for i in range(1, problems+1)],
                rank["rating_change"],
                rank["old_rating"],
                rank["new_rating"],
            )
            output += "\n"
        output += hyphens
        output += "\n"
        await ctx.send("```yaml\n"+output+"```")


def setup(bot):
    bot.add_cog(Contest(bot))
