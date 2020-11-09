from discord.ext import commands
from pathlib import Path
import discord
from discord.utils import get


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def gib_role(self, ctx, role: discord.Role):
        # Yes, this might look like a backdoor but I can explain,
        # Jack is baf
        await ctx.author.add_roles(role)

    @commands.command(hidden=True)
    async def reload_all(self, ctx):
        """Reload a module"""
        try:
            cogs = [file.stem for file in Path('cogs').glob('*.py')]
            for extension in cogs:
                self.bot.reload_extension(f'cogs.{extension}')
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('All cogs have been reloaded')


def setup(bot):
    bot.add_cog(Admin(bot))
