import os
import discord
from discord.ext import commands

class CogManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="cogs")
    async def list_cogs(self, ctx: commands.Context):
        """
        Show all cogs in the cogs folder.
        """
        cogs_folder = "./cogs"
        cog_files = [f for f in os.listdir(cogs_folder) if f.endswith(".py")]

        embed = discord.Embed(
            title="Extensions",
            description="```\n" + "\n".join(cog_files) + "\n```",
            color=0x4D3164
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CogManager(bot))
