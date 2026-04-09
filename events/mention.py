import discord
from discord.ext import commands
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail, ActionRow, Button
from pathlib import Path
import sys

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import REPLY_2, LINK

class MentionReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if the bot was mentioned directly
        if message.content.strip() in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            # Get prefix for this guild
            prefix = await self.bot.get_prefix(message)
            if isinstance(prefix, list):  # handle multiple prefixes
                prefix = prefix[0]

            # Create the Display using Components V2
            section = Section(
                TextDisplay(
                    f"# Hey! I'm {self.bot.user.name}\n"
                    f"> {REPLY_2} My prefix here is `{prefix}`\n"
                    f"> {REPLY_2} Run `{prefix}help` for commands\n"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Bot Avatar"
                ),
                id=1
            )

            # Quick Links ActionRow
            invite_btn = Button(label="Invite Me", style=discord.ButtonStyle.link, url=self.bot.invite_link)
            support_btn = Button(label="Support", style=discord.ButtonStyle.link, url=self.bot.support_link)
            vote_btn = Button(label="Vote", style=discord.ButtonStyle.link, url=self.bot.vote_link)
            
            links_row = ActionRow(invite_btn, support_btn, vote_btn)

            container = Container(
                section,
                Separator(),
                links_row,
                TextDisplay(f"-# Powered by CodeX Development"),
                
            )

            view = LayoutView(timeout=None)
            view.add_item(container)

            try:
                await message.channel.send(view=view)
            except discord.errors.Forbidden:
                pass
            except Exception as e:
                print(f"Error sending mention reply: {e}")

async def setup(bot):
    await bot.add_cog(MentionReply(bot))