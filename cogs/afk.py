import discord
from discord.ext import commands
from discord import ui
import aiosqlite
import os
import time
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import CHECK, CROSS, INFO, TIMER

DB_PATH = "db/afk.db"

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs("db", exist_ok=True)
        self.bot.loop.create_task(self._init_db())

    async def _init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, message TEXT, time INTEGER)")
            await db.commit()

    def format_time(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0: parts.append(f"{days}d")
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        if seconds > 0 or not parts: parts.append(f"{seconds}s")
        
        return " ".join(parts)

    @commands.command(name="afk", help="Set your AFK status.")
    async def afk_command(self, ctx, *, message: str = "I'm semi-active!"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO afk VALUES (?,?,?)", (ctx.author.id, message, int(time.time())))
            await db.commit()
        
        # CV2 Layout for AFK confirmation
        view = ui.LayoutView()
        container = ui.Container(accent_color=0x4D3164)
        container.add_item(ui.TextDisplay(f"{CHECK} You are now AFK: **{message}**"))
        view.add_item(container)
        
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        
        # Try to rename user if bot has permissions
        try:
            if ctx.author != ctx.guild.owner and ctx.guild.me.guild_permissions.manage_nicknames:
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name[:25]}")
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # 1. Check if the sender is returning from AFK
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT message, time FROM afk WHERE user_id = ?", (message.author.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    afk_msg, afk_time = row
                    await db.execute("DELETE FROM afk WHERE user_id = ?", (message.author.id,))
                    await db.commit()
                    
                    duration = self.format_time(time.time() - afk_time)
                    
                    # Welcome back message (CV2)
                    view = ui.LayoutView()
                    container = ui.Container(accent_color=0x00FF00) # Green for welcome back
                    container.add_item(ui.TextDisplay(f"Welcome back {message.author.mention}, I've removed your AFK!"))
                    container.add_item(ui.TextDisplay(f"{TIMER} You were AFK for: **{duration}**"))
                    view.add_item(container)
                    
                    await message.channel.send(view=view, allowed_mentions=discord.AllowedMentions.none())
                    
                    # Try to remove AFK nick
                    try:
                        if message.author != message.guild.owner and message.guild.me.guild_permissions.manage_nicknames:
                            if message.author.display_name.startswith("[AFK]"):
                                await message.author.edit(nick=message.author.display_name[6:])
                    except:
                        pass

        # 2. Check if anyone mentioned is AFK
        if message.mentions:
            for user in message.mentions:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT message, time FROM afk WHERE user_id = ?", (user.id,)) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            afk_msg, afk_time = row
                            duration = self.format_time(time.time() - afk_time)
                            
                            # AFK Notification (CV2)
                            view = ui.LayoutView()
                            container = ui.Container(accent_color=0xFF0000) # Red/Accent for AFK info
                            container.add_item(ui.TextDisplay(f"### {user.display_name} is AFK"))
                            container.add_item(ui.TextDisplay(f"> {afk_msg}"))
                            container.add_item(ui.TextDisplay(f"{TIMER} AFK since: **{duration} ago**"))
                            view.add_item(container)
                            
                            await message.channel.send(view=view, delete_after=15, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(AFK(bot))
