import discord
from discord.ext import commands
import datetime

# 🔧 Your log channel ID
LOG_CHANNEL_ID = 1408111163526615170  


class GuildLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_log(self, guild: discord.Guild, action: str):
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        # Invite or vanity link
        invite_link = "Not Found"
        try:
            invites = await guild.invites()
            if invites:
                invite_link = invites[0].url
            elif guild.vanity_url:
                invite_link = guild.vanity_url
        except Exception:
            pass

        # Member counts
        total_members = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots

        # Bot stats
        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds)

        embed = discord.Embed(
            title=f"🤖 Bot {action} a server!",
            color=discord.Color.green() if action == "joined" else discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="📛 Server", value=f"{guild.name} (`{guild.id}`)", inline=False)
        embed.add_field(name="👑 Owner", value=f"{guild.owner} (`{guild.owner_id}`)", inline=False)
        embed.add_field(name="📝 Description", value=guild.description or "Not provided", inline=False)
        embed.add_field(
            name="👥 Members",
            value=f"👤 Users: {humans}\n🤖 Bots: {bots}\n📊 Total: {total_members}",
            inline=False
        )
        embed.add_field(name="🔗 Invite", value=invite_link, inline=False)
        embed.add_field(
            name="📊 Bot Stats",
            value=f"Servers: {total_guilds}\nUsers: {total_users}",
            inline=False
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.send_log(guild, "joined")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.send_log(guild, "left")


async def setup(bot: commands.Bot):
    await bot.add_cog(GuildLog(bot))
