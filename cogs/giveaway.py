import discord
from discord.ext import commands, tasks
import sqlite3
import random
import time
from datetime import datetime
import os
import re
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure db directory exists
        os.makedirs("db", exist_ok=True)
        self.db = sqlite3.connect("db/giveaways.db")
        self.create_table()
        self.check_giveaways.start()

    def create_table(self):
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER,
                    prize TEXT,
                    winners INTEGER,
                    end_time INTEGER,
                    host_id INTEGER,
                    ended BOOLEAN DEFAULT 0
                )
            """)

    def cog_unload(self):
        self.check_giveaways.cancel()
        self.db.close()

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        current_time = int(time.time())
        with self.db:
            cursor = self.db.execute(
                "SELECT id, guild_id, channel_id, message_id, prize, winners FROM giveaways WHERE ended = 0 AND end_time <= ?",
                (current_time,)
            )
            rows = cursor.fetchall()
        for row in rows:
            giveaway_id, guild_id, channel_id, message_id, prize, num_winners = row
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(message_id)
                await self.end_giveaway(giveaway_id, message, prize, num_winners)
            except discord.NotFound:
                with self.db:
                    self.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))
            except discord.Forbidden:
                with self.db:
                    self.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))

    @commands.group(name="giveaway", invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True)
    async def giveaway(self, ctx):
        """Displays help for giveaway commands when no subcommand is provided."""
        section = Section(
            TextDisplay(
                f"# **Giveaway Command Help**\n"
                f"> Available giveaway commands and their usage:\n"
                f"> **giveaway start <duration> <winners> <prize>**\n"
                f"> Start a new giveaway. Duration (e.g., 1d 2h 30m, 2d), number of winners, and prize name. Requires manage_guild permission.\n"
                f"> Example: `giveaway start 2h 3 $50 Gift Card`\n\n"
                f"> **giveaway end <message_id>**\n"
                f"> End a giveaway early by its message ID. Requires manage_guild permission.\n"
                f"> Example: `giveaway end 123456789012345678`\n\n"
                f"> **giveaway reroll <message_id>**\n"
                f"> Reroll winners for a giveaway by its message ID. Requires manage_guild permission.\n"
                f"> Example: `giveaway reroll 123456789012345678`\n\n"
                f"> **giveaway list**\n"
                f"> List all active giveaways in the server.\n"
                f"> Example: `giveaway list`"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Giveaway Help Thumbnail"
            ),
            id=1
        )

        container = Container(
            section,
            Separator(),
            TextDisplay("-# React with 🎉 to enter giveaways!")
        )

        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @giveaway.command(name="start")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def giveaway_start(self, ctx, duration: str, winners: int, *, prize: str):
        """Start a giveaway. Usage: giveaway start <duration> <winners> <prize>"""
        if winners < 1:
            return await ctx.send("Number of winners must be at least 1!")

        try:
            duration_seconds = self.parse_duration(duration)
            if duration_seconds <= 0:
                raise ValueError
        except ValueError:
            return await ctx.send("Invalid duration format! Use something like '1d 2h 30m', '2d', '1h30m'.")

        end_time = int(time.time()) + duration_seconds
        end_time_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")

        section = Section(
            TextDisplay(
                f"# **🎉 New Giveaway!**\n"
                f"> **Prize**: {prize}\n"
                f"> **Winners**: {winners}\n"
                f"> **Ends**: <t:{end_time}:R>\n"
                f"> **Hosted by**: {ctx.author.mention}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Giveaway Start Thumbnail"
            ),
            id=1
        )

        container = Container(
            section,
            Separator(),
            TextDisplay("-# React with 🎉 to enter!")
        )

        view = LayoutView(timeout=None)
        view.add_item(container)
        message = await ctx.send(view=view)
        await message.add_reaction("🎉")

        with self.db:
            self.db.execute(
                "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, host_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ctx.guild.id, ctx.channel.id, message.id, prize, winners, end_time, ctx.author.id)
            )

        await ctx.send(f"Giveaway started! It will end at {end_time_str}.")

    async def end_giveaway(self, giveaway_id, message, prize, num_winners):
        reactions = message.reactions
        giveaway_reaction = discord.utils.get(reactions, emoji="🎉")
        if not giveaway_reaction:
            return

        users = [user async for user in giveaway_reaction.users() if not user.bot]

        section = Section(
            TextDisplay(
                f"# **Giveaway Ended!**\n"
                f"> **Prize**: {prize}\n"
                + (f"> **Winner(s)**: {', '.join(w.mention for w in random.sample(users, min(num_winners, len(users))))}"
                   if users else "> **Winner(s)**: No valid participants!")
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Giveaway End Thumbnail"
            ),
            id=1
        )

        container = Container(
            section,
            Separator(),
            TextDisplay("-# Giveaway has concluded!")
        )

        view = LayoutView(timeout=None)
        view.add_item(container)

        await message.edit(view=view)
        if users:
            selected_winners = random.sample(users, min(num_winners, len(users)))
            winner_mentions = ", ".join(w.mention for w in selected_winners)
            await message.channel.send(f"Congratulations {winner_mentions}! You won **{prize}**!")

        with self.db:
            self.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))

    @giveaway.command(name="end")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def giveaway_end(self, ctx, message_id: int):
        """End a giveaway early. Usage: giveaway end <message_id>"""
        with self.db:
            cursor = self.db.execute(
                "SELECT id, prize, winners, channel_id FROM giveaways WHERE message_id = ? AND guild_id = ? AND ended = 0",
                (message_id, ctx.guild.id)
            )
            result = cursor.fetchone()
            if not result:
                return await ctx.send("No active giveaway found with that message ID!")

            giveaway_id, prize, num_winners, channel_id = result

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("Giveaway channel not found!")

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            with self.db:
                self.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))
            return await ctx.send("Giveaway message not found!")

        await self.end_giveaway(giveaway_id, message, prize, num_winners)
        await ctx.send("Giveaway ended successfully!")

    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def giveaway_reroll(self, ctx, message_id: int):
        """Reroll a giveaway. Usage: giveaway reroll <message_id>"""
        with self.db:
            cursor = self.db.execute(
                "SELECT id, prize, winners, channel_id FROM giveaways WHERE message_id = ? AND guild_id = ?",
                (message_id, ctx.guild.id)
            )
            result = cursor.fetchone()
            if not result:
                return await ctx.send("No giveaway found with that message ID!")

            giveaway_id, prize, num_winners, channel_id = result

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("Giveaway channel not found!")

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            with self.db:
                self.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))
            return await ctx.send("Giveaway message not found!")

        await self.end_giveaway(giveaway_id, message, prize, num_winners)
        await ctx.send("Giveaway rerolled successfully!")

    @giveaway.command(name="list")
    @commands.bot_has_permissions(send_messages=True)
    async def giveaway_list(self, ctx):
        """List all active giveaways in the server."""
        with self.db:
            cursor = self.db.execute(
                "SELECT id, prize, winners, end_time, channel_id, message_id FROM giveaways WHERE guild_id = ? AND ended = 0",
                (ctx.guild.id,)
            )
            giveaways = cursor.fetchall()

        if not giveaways:
            return await ctx.send("No active giveaways in this server!")

        giveaway_text = ""
        for giveaway in giveaways:
            giveaway_id, prize, winners, end_time, channel_id, message_id = giveaway
            channel = ctx.guild.get_channel(channel_id)
            giveaway_text += (
                f"**Giveaway ID: {giveaway_id}**\n"
                f"> **Prize**: {prize}\n"
                f"> **Winners**: {winners}\n"
                f"> **Ends**: <t:{end_time}:R>\n"
                f"> **Channel**: {channel.mention if channel else 'Unknown'}\n"
                f"> [Jump to Giveaway](https://discord.com/channels/{ctx.guild.id}/{channel_id}/{message_id})\n\n"
            )

        section = Section(
            TextDisplay(
                f"# **Active Giveaways**\n"
                f"{giveaway_text}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Giveaway List Thumbnail"
            ),
            id=1
        )

        container = Container(
            section,
            Separator(),
            TextDisplay("-# React with 🎉 to enter giveaways!")
        )

        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    def parse_duration(self, duration: str) -> int:
        """Parse duration string (e.g., '1d 2h 30m 10s') to seconds."""
        duration = duration.lower().replace(" ", "")
        total_seconds = 0
        patterns = [
            (r'(\d+)d', 86400),
            (r'(\d+)h', 3600),
            (r'(\d+)m', 60),
            (r'(\d+)s', 1)
        ]
        for pattern, multiplier in patterns:
            match = re.search(pattern, duration)
            if match:
                total_seconds += int(match.group(1)) * multiplier
                duration = re.sub(pattern, '', duration)
        if duration:  # If anything left, invalid
            raise ValueError("Invalid duration format")
        return total_seconds

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Giveaway(bot))