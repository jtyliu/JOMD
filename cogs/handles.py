from discord.ext import commands
import discord
from utils.query import Query
from utils.db import session, User as User_DB, Handle as Handle_DB
# import html
# import random
import typing
import asyncio


class Handles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def whois(self, ctx, member: typing.Optional[discord.Member] = None,
                    handle: typing.Optional[str] = None):
        # TODO: Use embeds and pfps
        query = Query()
        if handle:
            user = await query.get_user(handle)
            handle = user.username
            author_id = query.get_handle_user(handle, ctx.guild.id)
            if author_id:
                # member = await self.bot.fetch_user(author_id)
                name = ctx.message.guild.get_member(author_id)
                await ctx.send(f'`{handle}` is `{name.nick or name.name}`')
            else:
                await ctx.send(f'`{handle}` is not linked with any account here...')
        elif member:
            handle = query.get_handle(member.id, ctx.guild.id)
            if handle:
                await ctx.send(f'`{member.nick or member.name}` is `{handle}`')
            else:
                await ctx.send(f'`{member.nick or member.name}` is not linked with any account here')
        else:
            # wtf
            pass

    @commands.command()
    async def unlink(self, ctx):
        """Unlink your discord account with your dmoj account"""
        query = Query()
        if not query.get_handle(ctx.author.id, ctx.guild.id):
            await ctx.send('You are not linked with any user')
            return
        handle = session.query(Handle_DB)\
            .filter(Handle_DB.id == ctx.author.id)\
            .filter(Handle_DB.guild_id == ctx.guild.id).first()
        session.delete(handle)
        session.commit()
        await ctx.send(f'Unlinked you with handle {handle.handle}')

    @commands.command(usage='dmoj_handle')
    async def link(self, ctx, username: str):
        """Links your discord account to your dmoj account"""
        # Check if user exists
        query = Query()
        user = await query.get_user(username)

        if user is None:
            await ctx.send(f"{username} does not exist on DMOJ")
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
        
        #verify from dmoj user description
        description=await query.get_user_description(username);
        userKey='x'+str(ctx.author.id*ctx.author.id) #Replace this with a funnier message
        if description.find(userKey)==-1:
            await ctx.send('Put `'+userKey+'` in your DMOJ user description and run the command again.')
            return
        
        handle = Handle_DB()
        handle.id = ctx.author.id
        handle.handle = username
        handle.user_id = user.id
        handle.guild_id = ctx.guild.id
        session.add(handle)
        session.commit()
        return await ctx.send(
            "%s, you now have linked your account to %s." %
            (ctx.author.name, username)
        )

    @commands.command(name='set', usage='discord_account dmoj_handle')
    @commands.has_role('Admin')
    async def _set(self, ctx, member: discord.Member, username: str):
        """Manually link two accounts together"""
        query = Query()
        user = await query.get_user(username)

        if user is None:
            await ctx.send(f'{username} does not exist on dmoj')
            return

        username = user.username

        if query.get_handle(member.id, ctx.guild.id):
            await ctx.send(
                '%s, this handle is already linked with %s.' %
                (ctx.author.mention, query.get_handle(member.id, ctx.guild.id)))
            return

        if query.get_handle_user(username, ctx.guild.id):
            await ctx.send('This handle is already linked with another user')
            return

        handle = Handle_DB()
        handle.id = member.id
        handle.handle = username
        handle.user_id = user.id
        handle.guild_id = ctx.guild.id
        session.add(handle)
        session.commit()
        return await ctx.send(
            "%s, %s is now linked with %s." %
            (ctx.author.name, member.name, username)
        )


def setup(bot):
    bot.add_cog(Handles(bot))
