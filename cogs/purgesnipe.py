import discord
from discord.ext import commands
from collections import deque
import datetime
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail

class PurgeSnipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.deleted_messages = {}  # channel_id: deque of (content, author, created_at, attachments)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:  # Ignore DMs
            return
        channel_id = message.channel.id
        if channel_id not in self.deleted_messages:
            self.deleted_messages[channel_id] = deque(maxlen=10)
        attachments = [att.url for att in message.attachments]
        self.deleted_messages[channel_id].append({
            'content': message.content,
            'author': message.author,
            'created_at': message.created_at,
            'attachments': attachments
        })

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def purge(self, ctx, amount: int):
        """Purge a specified number of messages from the channel. Usage: purge <amount>"""
        if amount < 1 or amount > 1000:
            return await ctx.send("Amount must be between 1 and 1000.")
        purged = await ctx.channel.purge(limit=amount)
        await ctx.send(f"Purged {len(purged)} messages.", delete_after=5)

    @commands.command(name="snipe")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def snipe(self, ctx, index: int = 1):
        """Snipe the last deleted message(s). Usage: snipe [index] (default 1, latest deleted)"""
        channel_id = ctx.channel.id
        if channel_id not in self.deleted_messages or not self.deleted_messages[channel_id]:
            return await ctx.send("No deleted messages to snipe in this channel.")
        
        messages = list(self.deleted_messages[channel_id])
        if index < 1 or index > len(messages):
            return await ctx.send(f"Invalid index. Available deleted messages: 1 to {len(messages)}")
        
        msg_data = messages[-index]  # -1 is latest
        content = msg_data['content'] or "[No content]"
        attachments = "\n".join(msg_data['attachments']) if msg_data['attachments'] else "None"
        timestamp = msg_data['created_at'].strftime("%Y-%m-%d %H:%M:%S UTC")

        section = Section(
            TextDisplay(
                f"# **Sniped Deleted Message #{index}**\n"
                f"> **Author**: {msg_data['author'].display_name} (ID: {msg_data['author'].id})\n"
                f"> **Content**: {content}\n"
                f"> **Attachments**: {attachments}\n"
                f"> **Deleted At**: {timestamp}"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=msg_data['author'].display_avatar.url if msg_data['author'].avatar else self.bot.user.display_avatar.url),
                description="Snipe Thumbnail"
            ),
            id=1
        )

        container = Container(
            section,
            Separator(),
            TextDisplay(f"-# Deleted message #{index} (latest is 1)")
        )

        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

async def setup(bot):
    await bot.add_cog(PurgeSnipe(bot))