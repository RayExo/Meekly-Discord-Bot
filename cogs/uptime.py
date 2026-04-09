import discord
import time
from discord.ext import commands
from discord.ui import (
    LayoutView,
    Container,
    Section,
    TextDisplay,
    Separator,
    Thumbnail
)
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import TIMER

class Uptime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()  # Save bot start time

    def format_uptime(self):
        current_time = time.time()
        difference = int(current_time - self.start_time)

        days, remainder = divmod(difference, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Formatted string for the UI
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Show how long the bot has been online using CV2 layout"""
        
        # Create the LayoutView
        view = LayoutView()

        # Create the Section with a Thumbnail accessory (Meekly Style)
        section = Section(
            TextDisplay(
                f"### {TIMER} Meekly Uptime\n"
                f"> **System Status:** Online\n"
                f"```\n{self.format_uptime()}\n```"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Uptime Icon"
            )
        )

        # Build the Container
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Power By Meekly Development")
        )

        view.add_item(container)
        
        await ctx.send(view=view)

async def setup(bot):
    await bot.add_cog(Uptime(bot))