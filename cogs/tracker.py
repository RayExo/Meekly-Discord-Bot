import discord
from discord.ext import commands
from discord import Embed
from datetime import datetime, timedelta
import aiosqlite
import os
import sys
from pathlib import Path
from discord.ui import Button, View, LayoutView, Container, Section, TextDisplay, Separator, Thumbnail

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import EMOJIES

TRACKER_DB = Path("db/tracker.db")

class TrackerButton(Button):
    def __init__(self, label, cog, ctx):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.tracker_cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Only the command initiator can use these buttons!", ephemeral=True)
            return

        if self.label == "Messages":
            container = await self.tracker_cog.get_messages_layout(self.ctx)
        elif self.label == "Invites":
            container = await self.tracker_cog.get_invites_layout(self.ctx)
        elif self.label == "Blacklist":
            container = await self.tracker_cog.get_blacklist_layout(self.ctx)
        else:  # Tracker Overview
            container = await self.tracker_cog.get_tracker_overview_layout(self.ctx)

        # In case some layout updates might need components, but for now we just edit
        await interaction.response.edit_message(content="", layout=container)

class TrackerView(View):
    def __init__(self, cog, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.tracker_cog = cog
        self.ctx = ctx
        self.add_item(TrackerButton("Tracker Overview", cog, ctx))
        self.add_item(TrackerButton("Messages", cog, ctx))
        self.add_item(TrackerButton("Invites", cog, ctx))
        self.add_item(TrackerButton("Blacklist", cog, ctx))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init_db())

    async def init_db(self):
        async with aiosqlite.connect(TRACKER_DB) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS message_counts (user_id INTEGER PRIMARY KEY, count INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS daily_message_counts (user_id INTEGER PRIMARY KEY, count INTEGER, date TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS blacklisted_channels (channel_id INTEGER PRIMARY KEY)")
            await db.commit()

    def is_fake_invite(self, user):
        return (datetime.utcnow() - user.created_at.replace(tzinfo=None)) < timedelta(days=30)

    async def get_messages_layout(self, ctx, member=None):
        member = member or ctx.author
        async with aiosqlite.connect(TRACKER_DB) as db:
            async with db.execute("SELECT count FROM message_counts WHERE user_id = ?", (member.id,)) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
            async with db.execute("SELECT count FROM daily_message_counts WHERE user_id = ?", (member.id,)) as cursor:
                row = await cursor.fetchone()
                today_msgs = row[0] if row else 0

        days_since_join = (datetime.utcnow().date() - member.joined_at.date()).days
        avg_daily_msgs = count / max(1, days_since_join)
        section = Section(
            TextDisplay(
                f"# **Meekly Message Tracker**\n"
                f"> **User Mention**: {member.mention}\n"
                f"> **Total Messages**: {count}\n"
                f"> **Avg. Daily Messages**: {avg_daily_msgs:.2f}\n"
                f"> **Today's Messages**: {today_msgs}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=member.display_avatar.url),
                description="Message Tracker Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        return container

    async def get_invites_layout(self, ctx, member=None):
        member = member or ctx.author
        invites = await ctx.guild.invites()
        user_invites = [inv for inv in invites if inv.inviter == member]
        fake_invites = sum(1 for inv in user_invites if self.is_fake_invite(inv.inviter))
        total_inv = len(user_invites)
        today_inv = sum(1 for inv in user_invites if inv.created_at.date() == datetime.utcnow().date())
        inv_users = ", ".join([inv.invited.name for inv in user_invites if inv.invited][:10])
        section = Section(
            TextDisplay(
                f"# **Meekly Invite Tracker**\n"
                f"> **User Mention**: {member.mention}\n"
                f"> **Total Invites**: {total_inv}\n"
                f"> **Fake Invites**: {fake_invites}\n"
                f"> **Invited Today**: {today_inv}\n"
                f"> **Invited Users**: {inv_users}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=member.display_avatar.url),
                description="Invite Tracker Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        return container

    async def get_blacklist_layout(self, ctx):
        async with aiosqlite.connect(TRACKER_DB) as db:
            async with db.execute("SELECT channel_id FROM blacklisted_channels") as cursor:
                rows = await cursor.fetchall()
        
        channels = "\n".join([f"<#{row[0]}>" for row in rows])
        section = Section(
            TextDisplay(
                f"# **Meekly Blacklist Tracker**\n"
                f"> Blacklisted channels:\n{channels if channels else 'No blacklisted channels.'}"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        return container

    async def get_tracker_overview_layout(self, ctx):
        async with aiosqlite.connect(TRACKER_DB) as db:
            async with db.execute("SELECT COUNT(*), SUM(count) FROM message_counts") as cursor:
                total_users, total_messages = await cursor.fetchone()
            async with db.execute("SELECT COUNT(*) FROM blacklisted_channels") as cursor:
                total_blacklisted = (await cursor.fetchone())[0]
            async with db.execute("SELECT SUM(count) FROM daily_message_counts") as cursor:
                today_total = (await cursor.fetchone())[0]

        section = Section(
            TextDisplay(
                f"# **Meekly Tracker Overview**\n"
                f"> **Total Tracked Users**: {total_users or 0}\n"
                f"> **Active Blacklisted Channels**: {total_blacklisted or 0}\n"
                f"> **Total Messages Tracked**: {total_messages or 0}\n"
                f"> **Today\'s Total Messages**: {today_total or 0}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Tracker Overview Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        return container

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        async with aiosqlite.connect(TRACKER_DB) as db:
            # Check blacklist
            async with db.execute("SELECT 1 FROM blacklisted_channels WHERE channel_id = ?", (message.channel.id,)) as cursor:
                if await cursor.fetchone():
                    return
            
            # Update total count
            await db.execute("INSERT INTO message_counts (user_id, count) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET count = count + 1", (message.author.id,))
            
            # Update daily count
            today = datetime.utcnow().date().isoformat()
            async with db.execute("SELECT date FROM daily_message_counts WHERE user_id = ?", (message.author.id,)) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] != today:
                    await db.execute("INSERT OR REPLACE INTO daily_message_counts (user_id, count, date) VALUES (?, 1, ?)", (message.author.id, today))
                else:
                    await db.execute("UPDATE daily_message_counts SET count = count + 1 WHERE user_id = ?", (message.author.id,))
            await db.commit()

    @commands.command(name="messages", aliases=["message", "msg", "msgs", "m"])
    async def messages(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        container = await self.get_messages_layout(ctx, member)
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="addmessages", aliases=["addmsg", "addmsgs", "addmessage"])
    async def addmessages(self, ctx, member: discord.Member, count: int):
        async with aiosqlite.connect(TRACKER_DB) as db:
            await db.execute("INSERT INTO message_counts (user_id, count) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET count = count + ?", (member.id, count, count))
            await db.commit()
        
        section = Section(
            TextDisplay(
                f"# **Meekly Message Tracker**\n"
                f"> {EMOJIES['check']} Added {count} messages to {member.mention}."
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="removemessages", aliases=["removemsg", "removemsgs", "removemessage"])
    async def removemessages(self, ctx, member: discord.Member, count: int):
        async with aiosqlite.connect(TRACKER_DB) as db:
            await db.execute("UPDATE message_counts SET count = MAX(0, count - ?) WHERE user_id = ?", (count, member.id))
            await db.commit()
            
        section = Section(
            TextDisplay(
                f"# **Meekly Message Tracker**\n"
                f"> {EMOJIES['check']} Removed {count} messages from {member.mention}."
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="blacklistchannel")
    async def blacklistchannel(self, ctx, channel_id: int):
        async with aiosqlite.connect(TRACKER_DB) as db:
            await db.execute("INSERT OR IGNORE INTO blacklisted_channels (channel_id) VALUES (?)", (channel_id,))
            await db.commit()

        section = Section(
            TextDisplay(
                f"# **Meekly Blacklist Tracker**\n"
                f"> {EMOJIES['check']} Channel <#{channel_id}> has been blacklisted."
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="unblacklistchannel")
    async def unblacklistchannel(self, ctx, channel: str = None):
        async with aiosqlite.connect(TRACKER_DB) as db:
            if channel == "all":
                await db.execute("DELETE FROM blacklisted_channels")
                await db.commit()
                msg = "All channels have been unblacklisted."
            else:
                try:
                    cid = int(channel)
                except:
                    return await ctx.send("Please provide a valid channel ID or 'all'.")
                await db.execute("DELETE FROM blacklisted_channels WHERE channel_id = ?", (cid,))
                await db.commit()
                msg = f"Channel <#{cid}> has been unblacklisted."

        section = Section(
            TextDisplay(
                f"# **Meekly Blacklist Tracker**\n"
                f"> {EMOJIES['check']} {msg}"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="blacklistedchannels")
    async def blacklistedchannels(self, ctx):
        container = await self.get_blacklist_layout(ctx)
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="clearmessages", aliases=["resetmsgs", "resetmsg", "resetmessages", "clearmsgs"])
    async def clearmessages(self, ctx, target: str = "all"):
        async with aiosqlite.connect(TRACKER_DB) as db:
            if target == "all":
                await db.execute("DELETE FROM message_counts")
                await db.execute("DELETE FROM daily_message_counts")
                msg = "All messages have been cleared."
            else:
                try:
                    uid = int(target.strip("<@!>"))
                    await db.execute("DELETE FROM message_counts WHERE user_id = ?", (uid,))
                    await db.execute("DELETE FROM daily_message_counts WHERE user_id = ?", (uid,))
                    msg = f"Messages for <@{uid}> have been cleared."
                except:
                    msg = "Member not found."
            await db.commit()

        section = Section(
            TextDisplay(
                f"# **Meekly Message Tracker**\n"
                f"> {EMOJIES['check']} {msg}"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="resetmymessages", aliases=["rmm", "clearmymessages", "clearmymessage"])
    async def resetmymessages(self, ctx):
        async with aiosqlite.connect(TRACKER_DB) as db:
            await db.execute("DELETE FROM message_counts WHERE user_id = ?", (ctx.author.id,))
            await db.execute("DELETE FROM daily_message_counts WHERE user_id = ?", (ctx.author.id,))
            await db.commit()

        section = Section(
            TextDisplay(
                f"# **Meekly Message Tracker**\n"
                f"> {EMOJIES['check']} Your messages have been reset."
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="invites", aliases=["i"])
    async def invites(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        invites = await ctx.guild.invites()
        user_invites = [inv for inv in invites if inv.inviter == member]
        fake_invites = sum(1 for inv in user_invites if self.is_fake_invite(inv.inviter))
        total_inv = len(user_invites)
        today_inv = sum(1 for inv in user_invites if inv.created_at.date() == datetime.utcnow().date())
        inv_users = ", ".join([inv.invited.name for inv in user_invites if inv.invited][:10])
        section = Section(
            TextDisplay(
                f"# **Meekly Invite Tracker**\n"
                f"> **User Mention**: {member.mention}\n"
                f"> **Total Invites**: {total_inv}\n"
                f"> **Fake Invites**: {fake_invites}\n"
                f"> **Invited Today**: {today_inv}\n"
                f"> **Invited Users**: {inv_users}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=member.display_avatar.url),
                description="Invite Tracker Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="inviter")
    async def inviter(self, ctx):
        invites = await ctx.guild.invites()
        inviter = next((inv.inviter for inv in invites if inv.inviter != ctx.author), None)
        if inviter:
            section = Section(
                TextDisplay(
                    f"# **Meekly Invite Tracker**\n"
                    f"> Your inviter is {inviter.mention}."
                ),
                id=1
            )
        else:
            section = Section(
                TextDisplay(
                    f"# **Meekly Invite Tracker**\n"
                    f"> {EMOJIES['cross']} No inviter found."
                ),
                id=1
            )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="invited")
    async def invited(self, ctx):
        invites = await ctx.guild.invites()
        # Note: This checks for who the user invited
        invited_list = [inv for inv in invites if inv.inviter == ctx.author]
        fake_invites = sum(1 for inv in invited_list if self.is_fake_invite(inv.inviter))
        section = Section(
            TextDisplay(
                f"# **Meekly Invite Tracker**\n"
                f"> You have invited {len(invited_list)} members.\n"
                f"> Fake Invites: {fake_invites}"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="inviteinfo", aliases=["invitecodes", "invitecode", "ic"])
    async def inviteinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        invites = await ctx.guild.invites()
        user_invites = [inv.code for inv in invites if inv.inviter == member]
        fake_invites = sum(1 for inv in [inv for inv in invites if inv.inviter == member] if self.is_fake_invite(inv.inviter))
        section = Section(
            TextDisplay(
                f"# **Meekly Invite Tracker**\n"
                f"> {member.mention}'s invite codes:\n> {', '.join(user_invites) if user_invites else 'None'}\n"
                f"> Fake Invites: {fake_invites}"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Made with by Meekly Development")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="tracker")
    async def tracker(self, ctx):
        container = await self.get_tracker_overview_layout(ctx)
        view = TrackerView(self, ctx, timeout=60)
        view.message = await ctx.send(content="", view=view, layout=container)

async def setup(bot):
    await bot.add_cog(Tracker(bot))