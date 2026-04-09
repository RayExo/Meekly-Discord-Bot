import discord
import asyncio
from discord import ui
from discord.ext import commands, tasks
import aiosqlite
import os
import time
import re
import aiohttp
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import CHECK, CROSS, INFO, TIMER

DB_PATH = "db/social_v2.db"

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_task = None
        os.makedirs("db", exist_ok=True)
        self.bot.loop.create_task(self.initialize())

    def cog_unload(self):
        if self.check_task:
            self.check_task.cancel()

    async def initialize(self):
        # Auto-cleanup old legacy database if it exists
        if os.path.exists("db/social.db"):
            try:
                os.remove("db/social.db")
            except:
                pass
                
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, message TEXT, end_time INTEGER)")
            await db.commit()
        # Start the fail-safe background task
        self.check_task = self.bot.loop.create_task(self.background_reminder_check())

    def parse_time(self, time_str):
        # Parses 1h30m, 10s, 5d, etc.
        time_regex = re.compile(r'(\d+)([dhms])')
        time_map = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
        
        matches = time_regex.findall(time_str.lower())
        if not matches:
            return None
            
        total_seconds = 0
        for val, unit in matches:
            total_seconds += int(val) * time_map[unit]
        return total_seconds

    @commands.group(name="remind", aliases=["reminder"], help="Set or list reminders.", invoke_without_command=True)
    async def remind(self, ctx, time_input: str = None, *, message: str = None):
        if time_input is None:
            return await ctx.send_help(ctx.command)
            
        seconds = self.parse_time(time_input)
        if not seconds:
            return await ctx.send(f"{CROSS} Invalid time format! Use `1h30m`, `10s`, etc.")
        
        if seconds > 31536000: # 1 year limit
            return await ctx.send(f"{CROSS} I can't remind you more than a year in advance!")

        end_time = int(time.time()) + seconds
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("INSERT INTO reminders (user_id, channel_id, message, end_time) VALUES (?, ?, ?, ?)", 
                             (ctx.author.id, ctx.channel.id, message, end_time))
            reminder_id = cursor.lastrowid
            await db.commit()
            
        view = ui.LayoutView()
        container = ui.Container(accent_color=0x4D3164)
        container.add_item(ui.TextDisplay(f"### {TIMER} Reminder Set"))
        container.add_item(ui.TextDisplay(f"I'll remind you about **{message}** <t:{end_time}:R>."))
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

        # Start an immediate wait-and-fire task for this reminder
        self.bot.loop.create_task(self.wait_and_remind(reminder_id, seconds, ctx.author.id, ctx.channel.id, message))

    @remind.command(name="version", help="Check the reminder system version.")
    async def reminder_version(self, ctx):
        await ctx.send(f"{INFO} Reminder System Version: `v2.1` (DB: `{DB_PATH}`)")

    async def wait_and_remind(self, reminder_id, seconds, uid, cid, msg):
        await asyncio.sleep(seconds)
        # Check if reminder still exists in DB (hasn't been fired by background task)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT id FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
                if await cursor.fetchone():
                    await self.fire_reminder(reminder_id, uid, cid, msg)

    async def fire_reminder(self, reminder_id, uid, cid, msg):
        channel = self.bot.get_channel(cid)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(cid)
            except:
                pass

        if channel:
            try:
                # Message 1: The Ping
                view_ping = ui.LayoutView()
                container_ping = ui.Container(accent_color=0xFF0000)
                container_ping.add_item(ui.TextDisplay(f"<@{uid}>")) 
                view_ping.add_item(container_ping)
                
                # Message 2: The Content
                view_content = ui.LayoutView()
                container_content = ui.Container(accent_color=0xFF0000)
                container_content.add_item(ui.TextDisplay(f"## {TIMER} Reminder!"))
                container_content.add_item(ui.TextDisplay(f"Heads up! You asked me to remind you:\n> {msg}"))
                view_content.add_item(container_content)
                
                # Send both (no content text allowed in CV2)
                allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)
                await channel.send(view=view_ping, allowed_mentions=allowed)
                await channel.send(view=view_content, allowed_mentions=allowed)
            except:
                pass
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await db.commit()

    async def background_reminder_check(self):
        while not self.bot.is_closed():
            try:
                now = int(time.time())
                async with aiosqlite.connect(DB_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT id, user_id, channel_id, message FROM reminders WHERE end_time <= ?", (now,)) as cursor:
                        rows = await cursor.fetchall()
                        for row in rows:
                            await self.fire_reminder(row["id"], row["user_id"], row["channel_id"], row["message"])
            except:
                pass
            await asyncio.sleep(15) # Check every 15s for legacy/recovery reminders

    @remind.command(name="list", help="List your active reminders.")
    async def list_reminders(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT message, end_time FROM reminders WHERE user_id = ? ORDER BY end_time ASC", (ctx.author.id,)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await ctx.send(f"{INFO} You have no active reminders.")
                
                desc = "\n".join([f"• **{row[0]}** - <t:{row[1]}:R>" for row in rows])
                embed = discord.Embed(title="Your Reminders", description=desc, color=0x4D3164)
                await ctx.send(embed=embed)

    @commands.command(name="translate", help="Translate text to English (default) or any language.")
    async def translate(self, ctx, to_lang: str, *, text: str):
        """Usage: +translate es Hello -> Hola"""
        # Using a free translation API (MyMemory)
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"autodetect|{to_lang}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = data.get("responseData", {}).get("translatedText")
                    if translated:
                        view = ui.LayoutView()
                        container = ui.Container(accent_color=0x4D3164)
                        container.add_item(ui.TextDisplay(f"## Translation Result"))
                        container.add_item(ui.Separator())
                        container.add_item(ui.TextDisplay(f"**Original:**\n> {text}"))
                        container.add_item(ui.TextDisplay(f"**Translated ({to_lang.upper()}):**\n> {translated}"))
                        container.add_item(ui.Separator(visible=False))
                        container.add_item(ui.TextDisplay("-# Powered by MyMemory API"))
                        view.add_item(container)
                        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
                    else:
                        await ctx.send(f"{CROSS} Translation failed.")
                else:
                    await ctx.send(f"{CROSS} API error. Please try again later.")

async def setup(bot):
    await bot.add_cog(Social(bot))
