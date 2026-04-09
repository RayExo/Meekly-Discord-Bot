import discord
from discord.ext import commands

class UsersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="users")
    async def users(self, ctx):
        total_users = 0
        for guild in self.bot.guilds:
            total_users += guild.member_count  # includes users + bots

        total_servers = len(self.bot.guilds)

        await ctx.send(f"I can see **{total_users:,}** users across **{total_servers:,}** servers.")

async def setup(bot):
    await bot.add_cog(UsersCog(bot))
