import typing
from utils.gitgud import Gitgud as Gitgud_utils
from utils.query import Query
from utils.constants import SHORTHANDS, RATING_TO_POINT, POINT_VALUES
from utils.api import ObjectNotFound
from utils.jomd_common import (str_not_int, point_range, parse_gimme,
                               calculate_points)
import discord
from DiscordUtils import Pagination
from discord.ext import commands
from datetime import datetime
from sqlalchemy import orm
import random

class Gitgud(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		
	@commands.command(usage='[points] [problem types]')
	async def gitgud(self, ctx, points: typing.Optional[point_range], *filters):
		"""
	  	Recommend a problem and gain point upon completion

		SHORTHANDS:
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
		- string
		"""
		filters = list(filters)
		query = Query()
		gitgud_util = Gitgud_utils()
		# get the user's dmoj handle
		username = query.get_handle(ctx.author.id, ctx.guild.id)
		# user = await query.get_user(username)

		if username is None:
			return await ctx.send(f"You are not linked to a DMOJ Account. Please link your account before continuing")
		
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
		current = gitgud_util.get_current(username, ctx.guild.id)

		if current is not None and current.problem_id is not None:
			if current.point == 0 and await query.solved(username, current.problem_id):
				gitgud_util.clear(username, ctx.guild.id)
			else:
				problem = await query.get_problem(current.problem_id)
				embed = discord.Embed(
					description=f"You currently have an uncompleted challenge, [{problem.name}](https://dmoj.ca/{problem.code})"
				)
				return await ctx.send(embed=embed)

		filter_list = []
		for filter in filters:
			if filter in SHORTHANDS:
				filter_list.append(SHORTHANDS[filter])

		filters = filter_list

		result = await query.get_unsolved_problem(username, ctx.guild.id, 1, filters, points[0], points[1])
		if result is None:
			return await ctx.send("No problems that satisfies the filter")
		return await ctx.send(embed=result)
	
	@commands.command()
	async def nogud(self, ctx):
		"""
		Cancels any unfinished challenge
		"""
		query = Query()
		gitgud_util = Gitgud_utils()
		
		username = query.get_handle(ctx.author.id, ctx.guild.id)

		if username is None:
			return await ctx.send("You do not have a linked DMOJ account")
		
		current = gitgud_util.get_current(username, ctx.guild.id)
		if current is None or current.problem_id is None:
			return await ctx.send("Nothing to cancel")

		gitgud_util.clear(username, ctx.guild.id)
		return await ctx.send("Challenge skipped")


	@commands.command(usage="[username]")
	async def gitlog(self, ctx, username=None):
		"""
		Show the past gitgud history of a user
		"""
		query = Query()
		username = username or query.get_handle(ctx.author.id, ctx.guild.id)
		try:
			user = await query.get_user(username)
			username = user.username
		except TypeError:
			username = None
		if username is None:
			return await ctx.send("You have not entered a valid DMOJ handle or linked with a DMOJ Account")

		gitgud_util = Gitgud_utils()
		history = gitgud_util.get_all(username, ctx.guild.id)


		if len(history) == 0:
			embed = discord.Embed(description="User have not completed any challenge")
			return await ctx.send(embed=embed)
		# paginate
		count = 0
		page_cnt = min(10, len(history)//10 + bool(len(history)%10))
		embeds = []
		content = ""
		paginator = Pagination.CustomEmbedPaginator(ctx, timeout=60, remove_reactions=True)
		paginator.add_reaction('⏮️', "first")
		paginator.add_reaction('⏪', "back")
		paginator.add_reaction('⏩', "next")
		paginator.add_reaction('⏭️', "last")
		for solved in history:
			# print(solved.problem_id)
			problem = await query.get_problem(solved.problem_id)
			days = (datetime.now() - solved.time).days
			if days==0:
				days_str = "today"
			elif days==1:
				days_str = "yesterday"
			else:
				days_str = f"{days} days ago"
			content += f"[{problem.name}](https://dmoj.ca/{problem.code}) [+{solved.point}] ({days_str})\n"
			count += 1
			if count % 10 == 0:
				embed = discord.Embed()
				embed.add_field(name=f"Gitgud Log for {username} (page {count//10}/{page_cnt})", value=content, inline=True)
				embeds.append(embed)
				content = ""
			if count == 100:
				break
		if count % 10 != 0:
			embed = discord.Embed()
			embed.add_field(name=f"Gitlog for {username} (page {count//10 + 1}/{page_cnt})", value=content, inline=True)
			embeds.append(embed)
		return await paginator.run(embeds)


	@commands.command(brief="Mark challenge as complete")
	async def gotgud(self, ctx):
		"""
		Confirm completion of gitgud challenge
		"""
		query = Query()
		gitgud_util = Gitgud_utils()
		username = query.get_handle(ctx.author.id, ctx.guild.id)

		if username is None:
			return await ctx.send("You are not linked with a DMOJ Account")

		user = await query.get_user(username)
		current = gitgud_util.get_current(username, ctx.guild.id)
		closest = -1000
		for key in RATING_TO_POINT:
			if abs(key - user.rating) <= abs(closest - user.rating):
				closest = key
		
		# convert rating to point and get difference
		rating_point = RATING_TO_POINT[closest]
		if current is None or current.problem_id is None:
			return await ctx.send("No pending challenges")

		# check if user is scamming the bot :monkey:
		if await query.solved(username, current.problem_id):
			# get closest rating
			closest = -1000
			for key in RATING_TO_POINT:
				if abs(key - user.rating) <= abs(closest - user.rating):
					closest = key
			# convert rating to point and get difference
			rating_point = RATING_TO_POINT[closest]
			print(POINT_VALUES.index(current.point) - POINT_VALUES.index(rating_point))
			point = 10 + 2 * (POINT_VALUES.index(current.point) - POINT_VALUES.index(rating_point))
			point = max(point, 0)

			gitgud_util.insert(username, ctx.guild.id, point, current.problem_id, datetime.now())
			gitgud_util.clear(username, ctx.guild.id)

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

			return await ctx.send(f"Challenge took{ret}. "
								  f"{current.handle} gained {point} points")

		else:
			return await ctx.send("You have not completed the challenge")



	@commands.command(usage='[member]')
	async def howgud(self, ctx, username = None):
		"""
		Returns total amount of gitgud points
		"""
		query = Query()
		if username is None:
			username = query.get_handle(ctx.author.id, ctx.guild.id)
		user = await query.get_user(username)
		username = user.username
		ret = Gitgud_utils().get_point(username, ctx.guild.id)
		if ret is None:
			ret = 0
		embed = discord.Embed(
			title=username,
			description=f"points: {ret}"
		)
		return await ctx.send(embed=embed)

def setup(bot):
	bot.add_cog(Gitgud(bot))
