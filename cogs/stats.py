from __future__ import annotations

import discord
from discord.ext import commands
from discord import ui
import psutil
import platform
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import (
    STATS as EMOJI_STATS,
    UPTIME as EMOJI_UPTIME,
    DATABASE as EMOJI_SYSTEM,
    VERIFIED_DEV as EMOJI_DEVS,
    OS_SYSTEM as EMOJI_OS,
    CPU as EMOJI_CPU,
    RAM as EMOJI_MEM,
    STORAGE as EMOJI_DISK,
    CROWN as EMOJI_OWNER,
    GEARS as EMOJI_TECH,
    LINK as EMOJI_LINKS,
    CREDITS as EMOJI_CREDITS,
    EMOJIES
)


class StatsView(ui.LayoutView):
    def __init__(
        self,
        bot: commands.Bot,
        bot_name: str,
        start_time: float,
        current_page: str = "overview",
        author: discord.User | None = None,
    ):
        super().__init__(timeout=60)

        self.bot = bot
        self.bot_name = bot_name
        self.start_time = start_time
        self.current_page = current_page
        self.author = author
        self.message: discord.Message | None = None

        container = ui.Container()

        if current_page == "overview":
            self._build_overview(container)
        elif current_page == "statistics":
            self._build_statistics(container)
        elif current_page == "system":
            self._build_system(container)
        elif current_page == "developers":
            self._build_developers(container)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(self._build_buttons())

        self.add_item(container)

    # ================= BUTTONS ================= #

    def _build_buttons(self) -> ui.ActionRow:
        def style(page: str):
            return discord.ButtonStyle.blurple if self.current_page == page else discord.ButtonStyle.gray

        overview = ui.Button(label="Overview", style=style("overview"))
        statistics = ui.Button(label="Statistics", style=style("statistics"))
        system = ui.Button(label="System Info", style=style("system"))
        developers = ui.Button(label="Developers", style=style("developers"))

        overview.callback = lambda i: self._switch(i, "overview")
        statistics.callback = lambda i: self._switch(i, "statistics")
        system.callback = lambda i: self._switch(i, "system")
        developers.callback = lambda i: self._switch(i, "developers")

        return ui.ActionRow(overview, statistics, system, developers)

    async def _switch(self, interaction: discord.Interaction, page: str):
        view = StatsView(
            self.bot,
            self.bot_name,
            self.start_time,
            page,
            self.author,
        )
        await interaction.response.edit_message(view=view)
        view.message = interaction.message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author and interaction.user.id != self.author.id:
            await interaction.response.send_message(
                f"{EMOJIES['cross']} This stats menu isn’t for you.",
                ephemeral=True,
            )
            return False
        return True

    # ================= PAGES (UNCHANGED CONTENT) ================= #

    def _header(self, text: str) -> ui.Section:
        if self.bot.user and self.bot.user.avatar:
            return ui.Section(
                ui.TextDisplay(text),
                accessory=ui.Thumbnail(self.bot.user.avatar.url),
            )
        return ui.Section(ui.TextDisplay(text))

    def _quick_links(self) -> ui.ActionRow:
        yt_btn = ui.Button(
            label="Youtube",
            style=discord.ButtonStyle.link,
            url="https://youtube.com/@CodeXDevs"
        )
        support_btn = ui.Button(
            label="Support",
            style=discord.ButtonStyle.link,
            url=self.bot.support_link
        )
        invite_btn = ui.Button(
            label="Free Hosting",
            style=discord.ButtonStyle.link,
            url="https://nexio.host/"
        )
        return ui.ActionRow(yt_btn, support_btn, invite_btn)

    def _build_overview(self, c: ui.Container):
        c.add_item(self._header(f"# {self.bot_name} Application Overview\n-# General information about the bot"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        uptime_seconds = time.time() - self.start_time
        days = int(uptime_seconds // 86400)

        c.add_item(
            ui.TextDisplay(
                f"## About\n"
                f"{self.bot_name} is a powerful moderation bot with advanced security features, "
                f"auto-moderation, voice master, ticket system, giveaways, and much more!\n\n"
                f"## Bot Information\n"
                f"Version 1.0.0 running on Python v{platform.python_version()}\n\n"
                f"## Runtime Details\n"
                f"Last restart: {days} days ago\n"
                f"Discord.py v{discord.__version__} • Cluster 0"
            )
        )
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(self._quick_links())

        if self.author:
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"-# Requested by {self.author.display_name}"))

    def _build_statistics(self, c: ui.Container):
        c.add_item(self._header(f"# {EMOJI_STATS} {self.bot_name} Statistics\n-# Detailed bot statistics"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        total_members = sum(guild.member_count for guild in self.bot.guilds)
        text_channels = sum(len(guild.text_channels) for guild in self.bot.guilds)
        voice_channels = sum(len(guild.voice_channels) for guild in self.bot.guilds)

        c.add_item(
            ui.TextDisplay(
                f"```yaml\n"
                f"Servers: {len(self.bot.guilds):,}\n"
                f"Users: {total_members:,}\n"
                f"Text Channels: {text_channels:,}\n"
                f"Voice Channels: {voice_channels:,}\n"
                f"Commands: {len(self.bot.commands) + len(self.bot.tree.get_commands())}\n"
                f"Cogs Loaded: {len(self.bot.cogs)}\n"
                f"Latency: {round(self.bot.latency * 1000)}ms\n"
                f"```"
            )
        )
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(self._quick_links())

        if self.author:
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"-# Requested by {self.author.display_name}"))

    def _build_system(self, c: ui.Container):
        c.add_item(self._header(f"# {EMOJI_SYSTEM} {self.bot_name} System Information\n-# Host system specifications"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        c.add_item(
            ui.TextDisplay(
                f"```ini\n"
                f"[CPU]: {cpu}%\n"
                f"[RAM]: {ram.used / (1024**3):.2f}GB / {ram.total / (1024**3):.2f}GB\n"
                f"[DISK]: {disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB\n"
                f"```"
            )
        )
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(self._quick_links())

        if self.author:
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"-# Requested by {self.author.display_name}"))

    def _build_developers(self, c: ui.Container):
        c.add_item(self._header(f"# {EMOJI_DEVS} {self.bot_name} Development Team\n-# Meet the team behind this bot"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        c.add_item(
            ui.TextDisplay(
                f"```yaml\n"
                f"Main Developer: Not_Op_gamer404_YT\n"
                f"Co-Developer: ray.dev\n"
                f"Framework: Discord.py v{discord.__version__}\n"
                f"Python: {platform.python_version()}\n"
                f"```"
            )
        )
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        c.add_item(
            ui.TextDisplay(
                f"## {EMOJI_LINKS} Important Links\n"
            )
        )
        c.add_item(self._quick_links())
        if self.author:
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"-# Requested by {self.author.display_name}"))


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot, bot_name: str = "Meekly"):
        self.bot = bot
        self.bot_name = bot_name
        self.start_time = time.time()

    @commands.command(name="stats", aliases=["botinfo", "bi"])
    async def stats(self, ctx: commands.Context):
        view = StatsView(self.bot, self.bot_name, self.start_time, author=ctx.author)
        msg = await ctx.send(view=view)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
