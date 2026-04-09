# events/noprefix.py
import discord
from discord.ext import commands
from discord.ui import Select, View
import asyncio
import aiosqlite
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import TICK, ERROR_X, CHECK, CROSS_MARK, INFO, EMOJIES, TIMER
from main import DEV_ID, CORE_DB, DEVELOPER_IDS

# ---------- CONFIG ----------
LOG_CHANNEL_ID = 1408261262084931664       # <-- your log channel

PLANS = {
    "1 Week":  {"days": 7,  "emoji_id": None, "emoji_char": None},
    "3 Week":    {"days": 21, "emoji_id": None, "emoji_char": None},
    "1 Month": {"days": 30, "emoji_id": None, "emoji_char": None},
    "3 Month": {"days": 90, "emoji_id": None, "emoji_char": None},
    "6 Month": {"days": 180, "emoji_id": None, "emoji_char": None},
    "1 Year": {"days": 365, "emoji_id": None, "emoji_char": None},
}
# ----------------------------

def iso_now():
    return datetime.utcnow().isoformat()

def parse_iso(s):
    return datetime.fromisoformat(s)

class PlanSelect(Select):
    def __init__(self, bot: commands.Bot, target_member: discord.Member, invoker: discord.Member):
        options = []
        for plan,name_info in PLANS.items():
            emoji_obj = None
            if name_info["emoji_id"]:
                emoji_obj = bot.get_emoji(name_info["emoji_id"])
            options.append(discord.SelectOption(
                label=plan,
                description=f"{name_info['days']} days",
                emoji=emoji_obj or name_info["emoji_char"]
            ))
        super().__init__(placeholder="Choose a NoPrefix plan...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.target_member = target_member
        self.invoker = invoker

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        info = PLANS[chosen]
        expires = datetime.utcnow() + timedelta(days=info["days"])

        async with aiosqlite.connect(CORE_DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO noprefix (user_id, plan, added_by, added_at, expires) VALUES (?, ?, ?, ?, ?)",
                (self.target_member.id, chosen, self.invoker.id, iso_now(), expires.isoformat())
            )
            await db.commit()

        # DM the user
        emoji_text = str(self.bot.get_emoji(info["emoji_id"])) if info["emoji_id"] else info["emoji_char"] or ""
        try:
            await self.target_member.send(
                embed=discord.Embed(
                    title=f"{emoji_text} NoPrefix Granted",
                    description=f"You were given **{chosen}** NoPrefix for **{info['days']} days**.",
                    color=0x4D3164,
                    timestamp=datetime.utcnow()
                )
            )
        except Exception:
            pass

        # log to channel
        log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
        if log_ch:
            embed = discord.Embed(
                title="NoPrefix Added",
                color=0x4D3164,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{self.target_member} (`{self.target_member.id}`)", inline=False)
            embed.add_field(name="Plan", value=f"{emoji_text} {chosen}", inline=True)
            embed.add_field(name="Expires", value=expires.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
            embed.add_field(name="Added by", value=f"{self.invoker} (`{self.invoker.id}`)", inline=False)
            await safe_send(log_ch, embed=embed)

        await interaction.response.edit_message(content=f"{CHECK} {self.target_member.mention} added with **{emoji_text} {chosen}**", view=None)


class PlanView(View):
    def __init__(self, bot, member, invoker, timeout=60):
        super().__init__(timeout=timeout)
        self.add_item(PlanSelect(bot, member, invoker))


# helper: safely fetch channel
async def safe_fetch_channel(bot, cid):
    try:
        return await bot.fetch_channel(cid)
    except Exception:
        return None

async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except Exception:
        return None


class NPManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._expiry_task = None

    def is_dev(self, user_id: int):
        return user_id == self.bot.owner_id or user_id in DEVELOPER_IDS

    async def start(self):
        # register listeners
        self.bot.add_listener(self._on_message, "on_message")
        # start expiry loop
        self._expiry_task = self.bot.loop.create_task(self._expiry_loop())

    async def stop(self):
        if self._expiry_task:
            self._expiry_task.cancel()
            self._expiry_task = None
        try:
            self.bot.remove_listener(self._on_message, "on_message")
        except Exception:
            pass

    async def _expiry_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._check_expired()
            except Exception:
                pass
            await asyncio.sleep(60)  # every minute

    async def _check_expired(self):
        async with aiosqlite.connect(CORE_DB) as db:
            async with db.execute("SELECT user_id, plan, expires FROM noprefix") as cursor:
                rows = await cursor.fetchall()
        
        now = datetime.utcnow()
        for uid, plan, expires_str in rows:
            try:
                expires = parse_iso(expires_str)
            except Exception:
                # malformed entry -> remove
                async with aiosqlite.connect(CORE_DB) as db:
                    await db.execute("DELETE FROM noprefix WHERE user_id = ?", (uid,))
                    await db.commit()
                continue
            
            if expires <= now:
                async with aiosqlite.connect(CORE_DB) as db:
                    await db.execute("DELETE FROM noprefix WHERE user_id = ?", (uid,))
                    await db.commit()
                
                # notify user & log
                user = self.bot.get_user(uid)
                if user:
                    try:
                        await user.send(
                            embed=discord.Embed(
                                title="NoPrefix Expired",
                                description=f"Your **{plan}** NoPrefix has expired.",
                                color=0x4D3164,
                                timestamp=datetime.utcnow()
                            )
                        )
                    except Exception:
                        pass
                
                log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
                if log_ch:
                    embed = discord.Embed(
                        title="NoPrefix Expired",
                        color=0x4D3164,
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{user} (`{uid}`)" if user else uid, inline=False)
                    embed.add_field(name="Plan", value=f"{plan}", inline=True)
                    await safe_send(log_ch, embed=embed)

    async def _on_message(self, message: discord.Message):
        # ignore bots
        if message.author.bot:
            return

        content = message.content.strip()
        # remove leading bot mention if present
        for m in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            if content.startswith(m):
                content = content[len(m):].strip()
                break
        # remove leading '+' if present (support +np ...)
        if content.startswith("+"):
            content = content[1:].strip()
        lowered = content.lower()
        
        if lowered.startswith("np") or lowered.startswith("noprefix"):
            args = content.split()  # original casing
            if len(args) == 1:
                if not self.is_dev(message.author.id):
                    await message.channel.send(f"{CROSS_MARK} You are not a developer.")
                    return
                await message.channel.send("Usage: np add @user | np remove @user | np list")
                return

            sub = args[1].lower()
            # ---------- NP ADD ----------
            if sub == "add":
                if not self.is_dev(message.author.id):
                    await message.channel.send(f"{CROSS_MARK} You are not a developer.")
                    return
                target = None
                if message.mentions:
                    target = message.mentions[0]
                elif len(args) >= 3:
                    try:
                        uid = int(args[2])
                        target = message.guild.get_member(uid) or await self.bot.fetch_user(uid)
                    except Exception:
                        target = None
                if not target:
                    await message.channel.send(f"{CROSS_MARK} Provide a user mention or ID. Example: `np add @User`")
                    return

                # show dropdown for plan selection
                view = PlanView(self.bot, target, message.author, timeout=60)
                await message.channel.send(f"Choose plan for {target.mention} — (you have 60s)", view=view)
                return

            # ---------- NP REMOVE ----------
            if sub == "remove":
                if not self.is_dev(message.author.id):
                    await message.channel.send(f"{CROSS_MARK} You are not a developer.")
                    return
                target = None
                if message.mentions:
                    target = message.mentions[0]
                elif len(args) >= 3:
                    try:
                        uid = int(args[2])
                        target = message.guild.get_member(uid) or await self.bot.fetch_user(uid)
                    except Exception:
                        target = None
                if not target:
                    await message.channel.send(f"{CROSS_MARK} Provide a user mention or ID. Example: `np remove @User`")
                    return

                async with aiosqlite.connect(CORE_DB) as db:
                    async with db.execute("SELECT plan FROM noprefix WHERE user_id = ?", (target.id,)) as cursor:
                        row = await cursor.fetchone()
                    if not row:
                        await message.channel.send(f"{CROSS_MARK} {target.mention} does not have NoPrefix.")
                        return
                    await db.execute("DELETE FROM noprefix WHERE user_id = ?", (target.id,))
                    await db.commit()

                plan = row[0]
                try:
                    await target.send(
                        embed=discord.Embed(
                            title=f"{CHECK} NoPrefix Removed",
                            description=f"Your **{plan}** NoPrefix has been removed.",
                            color=0x4D3164,
                            timestamp=datetime.utcnow()
                        )
                    )
                except Exception:
                    pass

                await message.channel.send(f"{CHECK} Removed NoPrefix from {target.mention}")

                # log
                log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
                if log_ch:
                    embed = discord.Embed(
                        title="NoPrefix Removed",
                        color=0x4D3164,
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{target} (`{target.id}`)", inline=False)
                    embed.add_field(name="Plan", value=f"{plan}", inline=True)
                    embed.add_field(name="Removed by", value=f"{message.author} (`{message.author.id}`)", inline=False)
                    await safe_send(log_ch, embed=embed)
                return

            # ---------- NP LIST ----------
            if sub == "list":
                if not self.is_dev(message.author.id):
                    await message.channel.send(f"{CROSS_MARK} You are not a developer.")
                    return
                
                async with aiosqlite.connect(CORE_DB) as db:
                    async with db.execute("SELECT user_id, plan, expires FROM noprefix") as cursor:
                        rows = await cursor.fetchall()
                
                if not rows:
                    await message.channel.send("No active NoPrefix users.")
                    return
                
                embed = discord.Embed(title="Active NoPrefix Users", color=0x4D3164, timestamp=datetime.utcnow())
                for uid, plan, expires_str in rows:
                    try:
                        user_obj = self.bot.get_user(uid)
                        name = user_obj.mention if user_obj else str(uid)
                    except Exception:
                        name = str(uid)
                    
                    try:
                        remaining = (parse_iso(expires_str) - datetime.utcnow()).days
                        rem_text = f"({remaining} days left)"
                    except Exception:
                        rem_text = ""
                    
                    embed.add_field(
                        name=f"{plan} - {name}",
                        value=f"Expires: {expires_str} {rem_text}",
                        inline=False
                    )
                await message.channel.send(embed=embed)
                return

        # 2) Allow NP users to run commands WITHOUT prefix
        async with aiosqlite.connect(CORE_DB) as db:
            async with db.execute("SELECT expires FROM noprefix WHERE user_id = ?", (message.author.id,)) as cursor:
                row = await cursor.fetchone()
        
        if row:
            expires_str = row[0]
            try:
                if parse_iso(expires_str) <= datetime.utcnow():
                    async with aiosqlite.connect(CORE_DB) as db:
                        await db.execute("DELETE FROM noprefix WHERE user_id = ?", (message.author.id,))
                        await db.commit()
                    
                    try:
                        await message.author.send(
                            embed=discord.Embed(
                                title="NoPrefix Expired",
                                description="Your NoPrefix has expired.",
                                color=0x4D3164,
                                timestamp=datetime.utcnow()
                            )
                        )
                    except Exception:
                        pass
                else:
                    ctx = await self.bot.get_context(message)
                    if ctx.valid:
                        return
                    
                    try:
                        prefix = await self.bot.get_prefix(message)
                        if isinstance(prefix, (list, tuple)):
                            prefix = prefix[0]
                    except Exception:
                        prefix = "+"
                    
                    orig = message.content
                    message.content = f"{prefix}{orig}"
                    await self.bot.process_commands(message)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    manager = NPManager(bot)
    await manager.start()

