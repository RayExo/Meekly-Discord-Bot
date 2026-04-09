import discord
import aiosqlite
import os
import time
from discord.ext import commands, tasks
from pathlib import Path

# Add parent directory to path to import main config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import PREMIUM_DB
from emojis import EMOJIES, CART, BOOST as BOOST_EMOJI, CHECK as CHECK_EMOJI, CROSS as CROSS_EMOJI, SUPPORT

LOG_CHANNEL_ID = 1458003476029112542

PLANS = {
    "basic":  {"days": 30, "boosts": 3},
    "pro":    {"days": 30, "boosts": 6},
    "ultra":  {"days": 30, "boosts": 12}
}

class PremiumSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.expiry_loop.start()

    async def log(self, msg):
        ch = self.bot.get_channel(LOG_CHANNEL_ID)
        if ch:
            await ch.send(msg)

    # ---------- OWNER ----------
    @commands.command()
    @commands.is_owner()
    async def premium(self, ctx, user: discord.User, plan: str):
        plan = plan.lower()
        if plan not in PLANS:
            return await ctx.send("❌ Invalid plan")

        expires = int(time.time() + PLANS[plan]["days"] * 86400)

        async with aiosqlite.connect(PREMIUM_DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO premium_users (user_id, plan, expires, boosts) VALUES (?, ?, ?, ?)",
                (user.id, plan, expires, PLANS[plan]["boosts"])
            )
            await db.commit()

        await self.log(f"✅ Premium added → {user} ({plan})")
        await ctx.send(f"{CHECK_EMOJI} Successfully Premium activated {user} ({plan})")

    # ---------- BOOST ----------
    @commands.command()
    async def boost(self, ctx):
        uid, gid = ctx.author.id, ctx.guild.id

        async with aiosqlite.connect(PREMIUM_DB) as db:
            # Check premium
            async with db.execute("SELECT boosts, expires FROM premium_users WHERE user_id = ?", (uid,)) as cursor:
                premium_row = await cursor.fetchone()
            
            if not premium_row or premium_row[1] <= time.time():
                return await ctx.send(f"{CROSS_EMOJI} You don't own Premium\n {CART} Buy Premium to boost servers\n\n {SUPPORT} Purchase Premium [Here]({self.bot.support_link})")

            max_boosts = premium_row[0]
            
            # Check used boosts
            async with db.execute("SELECT SUM(amount) FROM user_boosts WHERE user_id = ?", (uid,)) as cursor:
                used_row = await cursor.fetchone()
                used = used_row[0] if used_row and used_row[0] else 0

            if used >= max_boosts:
                return await ctx.send(
                    f"🚫 No free boosts\n"
                    f"💎 Used: {used}/{max_boosts}"
                )

            # Add boost
            await db.execute(
                "INSERT INTO user_boosts (user_id, guild_id, amount) VALUES (?, ?, 1) ON CONFLICT(user_id, guild_id) DO UPDATE SET amount = amount + 1",
                (uid, gid)
            )
            # Update guild boosts
            await db.execute(
                "INSERT INTO guild_boosts (guild_id, total_boosts) VALUES (?, 1) ON CONFLICT(guild_id) DO UPDATE SET total_boosts = total_boosts + 1",
                (gid,)
            )
            await db.commit()

        await self.log(f"💎 Boost added → {ctx.author} | {ctx.guild.name}")
        await ctx.send(f"{CHECK_EMOJI} {ctx.author.display_name} Boosts {ctx.guild.name}")

    @commands.command()
    async def boost_remove(self, ctx):
        uid, gid = ctx.author.id, ctx.guild.id

        async with aiosqlite.connect(PREMIUM_DB) as db:
            async with db.execute("SELECT amount FROM user_boosts WHERE user_id = ? AND guild_id = ?", (uid, gid)) as cursor:
                row = await cursor.fetchone()
            
            if not row or row[0] <= 0:
                return await ctx.send(f"{CROSS_EMOJI} No boost here")

            # Remove boost
            if row[0] == 1:
                await db.execute("DELETE FROM user_boosts WHERE user_id = ? AND guild_id = ?", (uid, gid))
            else:
                await db.execute("UPDATE user_boosts SET amount = amount - 1 WHERE user_id = ? AND guild_id = ?", (uid, gid))
            
            # Update guild boosts
            await db.execute("UPDATE guild_boosts SET total_boosts = MAX(0, total_boosts - 1) WHERE guild_id = ?", (gid,))
            await db.commit()

        await self.log(f"➖ Boost removed → {ctx.author} | {ctx.guild.name}")
        await ctx.send(f"{ctx.author.display_name} Remove Boost from  {ctx.guild.name}")

    # ---------- AUTO EXPIRY ----------
    @tasks.loop(minutes=5)
    async def expiry_loop(self):
        now = int(time.time())
        async with aiosqlite.connect(PREMIUM_DB) as db:
            # Get expired users
            async with db.execute("SELECT user_id FROM premium_users WHERE expires <= ?", (now,)) as cursor:
                expired_uids = [row[0] for row in await cursor.fetchall()]
            
            for uid in expired_uids:
                # Find their boosts to decrement guild totals
                async with db.execute("SELECT guild_id, amount FROM user_boosts WHERE user_id = ?", (uid,)) as cursor:
                    boosts = await cursor.fetchall()
                
                for gid, amt in boosts:
                    await db.execute("UPDATE guild_boosts SET total_boosts = MAX(0, total_boosts - ?) WHERE guild_id = ?", (amt, gid))
                
                # Delete user records
                await db.execute("DELETE FROM user_boosts WHERE user_id = ?", (uid,))
                await db.execute("DELETE FROM premium_users WHERE user_id = ?", (uid,))
                
                await self.log(f"⏰ Premium expired → {uid}")
            
            if expired_uids:
                await db.commit()

    @expiry_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(PremiumSystem(bot))

