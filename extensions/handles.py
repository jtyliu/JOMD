from utils.api import ObjectNotFound
from utils.jomd_common import scroll_embed
from operator import itemgetter
from discord.ext import commands
from discord.utils import escape_markdown
import discord
from utils.query import Query
from utils.models import *
from utils.constants import RATING_TO_RANKS, RANKS, ADMIN_ROLES
from sqlalchemy import func
import typing
import asyncio
import hashlib
import traceback


class HandlesCog(commands.Cog, name='Handles'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def whois(self, ctx, member: typing.Optional[discord.Member] = None,
                    handle: typing.Optional[str] = None):
        try:
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
                    author_id = query.get_handle_user(handle, ctx.guild.id)
                    username = handle
                    if author_id:
                        member = ctx.message.guild.get_member(author_id)
                        linked_username = member.nick or member.name
                        pfp = member.avatar_url
            elif member:
                handle = query.get_handle(member.id, ctx.guild.id)
                username = member.nick or member.name
                if handle:
                    linked_username = handle
                    pfp = await query.get_pfp(handle)
            if linked_username:
                embed = discord.Embed(
                    color=0xfcdb05,
                    title=escape_markdown(f'{username} is {linked_username}'),
                )
                embed.set_thumbnail(url=pfp)
                return await ctx.send(embed=embed)
            elif username:
                embed = discord.Embed(
                    title=escape_markdown(f'{username} is not linked with any account here'),
                    color=0xfcdb05,
                )
                return await ctx.send(embed=embed)
        except Exception:
            pass
        name = None
        if member:
            name = member.nick or member.name
        embed = discord.Embed(
            title=escape_markdown(f'Nothing found on {handle or name}'),
            color=0xfcdb05,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def unlink(self, ctx):
        '''Unlink your discord account with your dmoj account'''
        # TODO: Add admin ability to manually unlink
        query = Query()
        if not query.get_handle(ctx.author.id, ctx.guild.id):
            await ctx.send('You are not linked with any user')
            return
        handle = session.query(Handle)\
            .filter(Handle.id == ctx.author.id)\
            .filter(Handle.guild_id == ctx.guild.id).first()
        session.delete(handle)
        session.commit()
        await ctx.send(escape_markdown(f'Unlinked you with handle {handle.handle}'))

    @commands.command(usage='dmoj_handle')
    async def link(self, ctx, username: str):
        '''Links your discord account to your dmoj account'''
        # Check if user exists
        query = Query()
        user = await query.get_user(username)

        if user is None:
            await ctx.send(escape_markdown(f'{username} does not exist on DMOJ'))
            return

        username = user.username

        if query.get_handle(ctx.author.id, ctx.guild.id):
            await ctx.send(
                '%s, your handle is already linked with %s.' %
                (ctx.author.mention,
                 query.get_handle(ctx.author.id, ctx.guild.id))
            )
            return

        if query.get_handle_user(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        # verify from dmoj user description
        description = await query.get_user_description(username)
        userKey = hashlib.sha256(str(ctx.author.id).encode()).hexdigest()
        if userKey not in description:
            await ctx.send('Put `' + userKey + '` in your DMOJ user description (https://dmoj.ca/edit/profile/) '
                           'and run the command again.')
            return

        handle = Handle()
        handle.id = ctx.author.id
        handle.handle = username
        handle.user_id = user.id
        handle.guild_id = ctx.guild.id
        session.add(handle)
        session.commit()
        await ctx.send(escape_markdown(
            '%s, you now have linked your account to %s' %
            (ctx.author.name, username)
        ))

        rank_to_role = {role.name: role for role in ctx.guild.roles if role.name in RANKS}
        rank = self.rating_to_rank(user.rating)
        if rank in rank_to_role:
            await self._update_rank(ctx.author, rank_to_role[rank], 'Dmoj account linked')
        else:
            await ctx.send('You are missing the `' + rank.name + '` role')

    @commands.command(name='set', usage='discord_account [dmoj_handle, +remove]')
    @commands.has_any_role(*ADMIN_ROLES)
    async def _set(self, ctx, member, username: str):
        '''Manually link two accounts together'''
        query = Query()
        member = await query.parseUser(ctx, member)

        if username != '+remove':
            user = await query.get_user(username)

            if user is None:
                await ctx.send(escape_markdown(f'{username} does not exist on dmoj'))
                return

            username = user.username

        handle = query.get_handle(member.id, ctx.guild.id)
        if handle == username:
            return await ctx.send(escape_markdown(f'{member.display_name} is already linked with {handle}'))

        if handle:
            handle = session.query(Handle)\
                .filter(Handle.id == member.id)\
                .filter(Handle.guild_id == ctx.guild.id).first()
            session.delete(handle)
            session.commit()
            await ctx.send(escape_markdown(f'Unlinked {member.display_name} with handle {handle.handle}'))

        if username == '+remove':
            return

        if query.get_handle_user(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        handle = Handle()
        handle.id = member.id
        handle.handle = username
        handle.user_id = user.id
        handle.guild_id = ctx.guild.id
        session.add(handle)
        session.commit()
        await ctx.send(escape_markdown(f'Linked {member.name} with {username}'))

        rank_to_role = {role.name: role for role in ctx.guild.roles if role.name in RANKS}
        rank = self.rating_to_rank(user.rating)
        if rank in rank_to_role:
            await self._update_rank(ctx.author, rank_to_role[rank], 'Dmoj account linked')
        else:
            await ctx.send('You are missing the `' + rank.name + '` role')

    @commands.command(aliases=['users', 'leaderboard'], usage='[rating|maxrating|points|solved]')
    async def top(self, ctx, arg='rating'):
        '''Shows registered server members in ranked order'''
        arg = arg.lower()
        if arg != 'rating' and arg != 'maxrating' and arg != 'points' and arg != 'solved':
            return await ctx.send_help('top')
        users = session.query(User).join(Handle, Handle.handle == User.username)\
            .filter(Handle.guild_id == ctx.guild.id)
        leaderboard = []
        for user in users:
            if arg == 'rating':
                leaderboard.append([-(user.rating or -9999), user.username])
            elif arg == 'maxrating':
                leaderboard.append([-(user.max_rating or -9999), user.username])
            elif arg == 'points':
                leaderboard.append([-user.performance_points, user.username])
            elif arg == 'solved':
                leaderboard.append([-(user.problem_count or 0), user.username])
        leaderboard.sort()
        content = []
        page = ''
        for i, user in enumerate(leaderboard):
            if (arg == 'rating' or arg == 'maxrating') and user[0] == 9999:
                page += f'{i+1} {user[1]} unrated\n'
            else:
                page += f'{i+1} {user[1]} {-round(user[0],3)}\n'
            if i % 10 == 9:
                content.append(page)
                page = ''
        if page != '':
            content.append(page)
        if len(content) == 0:
            content.append('No users')
        message = await ctx.send(embed=discord.Embed().add_field(name='Top DMOJ ' + arg, value=content[0]))
        await scroll_embed(ctx, self.bot, message, 'Top DMOJ ' + arg, content)

    def rating_to_rank(self, rating):
        if rating is None:
            return RANKS[0]  # Unrated
        for rank in RATING_TO_RANKS:
            if rank[0] <= rating < rank[1]:
                return RATING_TO_RANKS[rank]

    async def _update_rank(self, member, rank, reason):
        add_role = all([rank.name != role.name for role in member.roles])
        to_remove = []
        for role in member.roles:
            if rank.name != role.name and role.name in RANKS:
                to_remove.append(role)

        if len(to_remove) != 0:
            await member.remove_roles(*to_remove, reason=reason)
        if add_role:
            await member.add_roles(rank, reason=reason)

    @commands.command()
    @commands.has_any_role(*ADMIN_ROLES)
    async def update_roles(self, ctx):
        '''Manually update roles'''
        # Big problem, I stored rankings column in Contest table as Json instead of using foreign keys to participation
        # TODO: Migrate to work with participation table

        msg = await ctx.send('Fetching ratings...')

        q = session.query(User.username, Participation.user_id, func.max(Contest.end_time).label('end_time')).\
            join(Participation.contest).\
            join(Participation.user).\
            filter(Participation.new_rating != None).\
            filter(Handle.guild_id == 621087609170427916).\
            group_by(Participation.user_id).subquery()

        q = session.query(Handle.id, Participation.new_rating).\
            join(Participation.contest).\
            join(Handle, Handle.user_id == Participation.user_id).\
            join(q, q.c.user_id == Participation.user_id).\
            filter(q.c.end_time == Contest.end_time).\
            filter(Contest.is_rated == 1).\
            filter(Handle.guild_id == 621087609170427916)

        rating = {handle_id: new_rating for (handle_id, new_rating) in q}

        handle_ids = session.query(Handle.id).filter(Handle.guild_id == 621087609170427916).all()
        members = {handle_id: ctx.guild.get_member(handle_id) for (handle_id,) in handle_ids}

        rank_to_role = {role.name: role for role in ctx.guild.roles if role.name in RANKS}

        await msg.edit(content='Updating roles...')

        missing_roles = []
        try:
            for (handle_id, member) in members.items():
                new_rating = rating.get(handle_id, None)
                rank = self.rating_to_rank(new_rating)
                if rank in rank_to_role:
                    await self._update_rank(member, rank_to_role[rank], 'Dmoj rank update')
                elif rank not in missing_roles:
                    missing_roles.append(rank)
        except Exception:
            await ctx.send('An error occurred. ' + traceback.format_exc())
            return

        if len(missing_roles) != 0:
            await ctx.send('You are missing the ' + ', '.join(missing_roles) + ' roles')
        await msg.edit(content='Roles updated')


def setup(bot):
    bot.add_cog(HandlesCog(bot))
