import discord
from discord.ext import commands
from discord import SelectOption
from discord.ui import (
    LayoutView,
    Container,
    Section,
    TextDisplay,
    Separator,
    Select,
    ActionRow,
    Thumbnail,
    Button,
    MediaGallery,
    button
)
import sys
from pathlib import Path
import logging
import traceback
from datetime import datetime

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import DEFAULT_PREFIX

CATEGORY_COMMANDS = {
    "AutoMod": {
        "color": "blurple",
        "commands": [
            ("automod enable", "Enable automod features"),
            ("automod disable", "Disable automod features"),
            ("automod config", "Configure automod settings"),
            ("automod punishment", "Set punishment methods")
        ],
        "description": "Automatic moderation to keep your server safe from spam, invites, and disruptions."
    },
    "Info": {
        "color": "success",
        "commands": [
            ("help", "Show this help menu"),
            ("ping", "Check bot latency"),
            ("stats", "View bot statistics"),
            ("botinfo", "Get bot information"),
            ("uptime", "Check bot uptime"),
            ("invite", "Get bot invite link"),
            ("support", "Join support server"),
            ("vote", "Vote for the bot")
        ],
        "description": "Information commands to get details about the bot and server."
    },
    "Moderation": {
        "color": "danger",
        "commands": [
            ("ban", "Ban a member from the server"),
            ("kick", "Kick a member from the server"),
            ("mute", "Mute a member"),
            ("unmute", "Unmute a member"),
            ("lock", "Lock a channel"),
            ("unlock", "Unlock a channel"),
            ("hide", "Hide a channel"),
            ("unhide", "Unhide a channel"),
            ("unban", "Unban a member"),
            ("purge", "Delete multiple messages"),
            ("snipe", "View deleted messages"),
            ("warn", "Warn a member")
        ],
        "description": "Powerful moderation tools to manage your server and keep members in check."
    },
    "AntiNuke": {
        "color": "danger",
        "commands": [
            ("antinuke", "View antinuke status"),
            ("antinuke enable", "Enable antinuke protection"),
            ("antinuke disable", "Disable antinuke protection"),
            ("antinuke whitelist", "Whitelist a member"),
            ("antinuke unwwhitelist", "Remove whitelist"),
            ("extraowner set", "Set extra owner"),
            ("extraowner reset", "Reset extra owner"),
            ("extraowner view", "View extra owners")
        ],
        "description": "Advanced protection against server nuking and unauthorized actions."
    },
    "Utility": {
        "color": "primary",
        "commands": [
            ("avatar", "Get member's avatar"),
            ("serverinfo", "Get server information"),
            ("userinfo", "Get user information"),
            ("steal", "Steal an emoji"),
            ("giveaway", "Create a giveaway"),
            ("afk", "Set AFK status"),
            ("reminder", "Set reminders"),
            ("timer", "Create timers"),
            ("banner", "Get server banner"),
            ("users", "Count members"),
            ("setprefix", "Change command prefix"),
            ("resetprefix", "Reset to default prefix")
        ],
        "description": "Useful utility commands for everyday server management and fun features."
    },
    "AI": {
        "color": "success",
        "commands": [
            ("setup_ai", "Setup AI features"),
            ("reset_ai", "Reset AI settings"),
            ("ai_help", "Get AI help information")
        ],
        "description": "Artificial intelligence features for intelligent server interactions."
    },
    "Roles": {
        "color": "primary",
        "commands": [
            ("roles selection", "Create a self-role menu with a list of roles")
        ],
        "Usage": "+roles selection @Valorant @Minecraft @CSGO"
    },
    "Social": {
        "color": "success",
        "commands": [
            ("remind", "Set reminders"),
            ("remind list", "List your active reminders"),
            ("translate", "Translate text to English (default) or any language")
        ],
        "description": "Soical Commands to interact with members and provide fun features like reminders and translation."
    },
    "Embed": {
        "color": "success",
        "commands": [
            ("embed create", "Create and manage personalized embeds.")
        ],
        "description": "Create custom embeds with a user-friendly interface for announcements, promotions, and more."
    },
    "Tracker": {
        "color": "primary",
        "commands": [
            ("invites", "Check your invites"),
            ("inviter", "See who invited you"),
            ("invited", "See who you invited"),
            ("inviteinfo", "Get invite information"),
            ("addinvites", "Add invite count"),
            ("removeinvites", "Remove invite count"),
            ("messages", "Check message count"),
            ("addmessages", "Add message count"),
            ("removemessages", "Remove message count"),
            ("clearmessages", "Clear message counts"),
            ("resetmymessages", "Reset your message count")
        ],
        "description": "Track invites, messages, and member activity to reward active users."
    },
    "Pfp": {
        "color": "success",
        "commands": [
            ("boys", "Random boy profile pictures"),
            ("girls", "Random girl profile pictures"),
            ("couples", "Random couple pictures"),
            ("anime", "Random anime profile pictures"),
            ("pic", "Random pictures")
        ],
        "description": "Get random profile pictures from various categories."
    },
    "Welcome": {
        "color": "success",
        "commands": [
            ("greet setup", "Setup welcome message"),
            ("greet reset", "Reset welcome settings"),
            ("greet channel", "Set welcome channel"),
            ("greet edit", "Edit welcome message"),
            ("greet test", "Test welcome message"),
            ("greet config", "View welcome config"),
            ("greet autodelete", "Set auto-delete timer")
        ],
        "description": "Setup automatic welcome messages for new members."
    },
    "VoiceMaster": {
        "color": "primary",
        "commands": [
            ("voicemaster setup", "Setup voice channels"),
            ("voicemaster remove", "Remove voice channels")
        ],
        "description": "Manage and create temporary voice channels."
    },
    "Autoresponder": {
        "color": "success",
        "commands": [
            ("ar add", "Add auto-response"),
            ("ar remove", "Remove auto-response"),
            ("ar list", "List all auto-responses")
        ],
        "description": "Setup automatic responses to specific keywords."
    },
    "Autoreact": {
        "color": "primary",
        "commands": [
            ("react add", "Add auto-reaction"),
            ("react remove", "Remove auto-reaction"),
            ("react list", "List all auto-reactions")
        ],
        "description": "Setup automatic reactions to specific words."
    }
}


class HelpView(LayoutView):
    # Constants
    BANNER_URL = "https://media.discordapp.net/attachments/1491456300469719171/1491464117612056797/codex.gif"

    def __init__(self, bot: commands.Bot, author: discord.Member):
        super().__init__(timeout=120)
        self.bot = bot
        self.author = author

        # Display home menu
        container = self._build_home_container()
        self.add_item(container)

    def _create_dropdown(self, default_category: str = None) -> Select:
        """Create a fresh dropdown instance."""
        options = [
            SelectOption(
                label=category,
                value=category,
                description=f"View {len(CATEGORY_COMMANDS[category]['commands'])} commands",
                default=(category == default_category) if default_category else False
            )
            for category in CATEGORY_COMMANDS.keys()
        ]
        dropdown = Select(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_category_select"
        )
        dropdown.callback = self.on_select
        return dropdown

    def _get_banner_gallery(self) -> MediaGallery:
        """Get the banner image as a media gallery."""
        gallery = MediaGallery()
        gallery.add_item(
            media=self.BANNER_URL,
            description="Codex Banner"
        )
        return gallery

    def _get_welcome_section(self) -> Section:
        """Get the welcome text section with stats."""
        total_commands = sum(len(cat['commands']) for cat in CATEGORY_COMMANDS.values())
        welcome_text = (
            "# Meekly Help!\n\n"
            "> A small but powerful bot for your server!\n"
            "> Everything you need to manage, protect, and grow your Discord server.\n\n"
            "**Quick Stats:**\n"
            f"> • **{len(CATEGORY_COMMANDS)}** Command Categories\n"
            f"> • **{total_commands}** Total Commands\n"
            "> • **Fast & Reliable** Support\n"
        )
        
        return Section(
            TextDisplay(welcome_text),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Meekly Bot"
            ),
            id=1
        )

    def _build_home_container(self) -> Container:
        """Build the home menu container."""
        dropdown = self._create_dropdown()
        
        # Quick action buttons
        yt_btn = Button(
            label="Youtube",
            style=discord.ButtonStyle.link,
            url="https://youtube.com/@CodeXDevs"
        )
        
        support_btn = Button(
            label="Supoort",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/codexdev"
        )
        
        invite_btn = Button(
            label="Free Hosting",
            style=discord.ButtonStyle.link,
            url="https://nexio.host/"
        )
        
        quick_links_row = ActionRow(yt_btn, support_btn, invite_btn)
        
        return Container(
            self._get_banner_gallery(),
            Separator(),
            self._get_welcome_section(),
            Separator(),
            TextDisplay("**Choose a category:**"),
            ActionRow(dropdown),
            Separator(),
            # TextDisplay("-# Quick Links"),
            quick_links_row
        )

    def _get_category_section(self, category: str) -> Section:
        """Get the category commands section with formatted command list."""
        category_data = CATEGORY_COMMANDS.get(category)
        if not category_data:
            return None

        prefix = DEFAULT_PREFIX
        commands_list = ""
        
        for cmd_name, cmd_desc in category_data['commands']:
            commands_list += f"- **{cmd_name}**\n >  {cmd_desc}\n"

        detailed_text = (
            f"# {category} Commands\n\n"
            f"{commands_list}"
        )

        # Ensure text doesn't exceed 4000 character limit
        if len(detailed_text) > 3950:
            # Truncate and add indicator
            detailed_text = detailed_text[:3900] + "\n\n... and more commands (too many to display)"

        return Section(
            TextDisplay(detailed_text),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description=f"{category} Commands"
            ),
            id=2
        )

    def _build_category_container(self, category: str) -> Container:
        """Build category view container with back button."""
        dropdown = self._create_dropdown(default_category=category)
        
        back_button = Button(
            label="Back to Main Menu",
            style=discord.ButtonStyle.primary,
            custom_id="help_back_home"
        )
        back_button.callback = self.on_back_home

        # Use two separate ActionRows: one for dropdown, one for button
        dropdown_row = ActionRow(dropdown)
        button_row = ActionRow(back_button)

        return Container(
            self._get_banner_gallery(),
            Separator(),
            self._get_category_section(category),
            Separator(),
            TextDisplay("**Choose another category or go back:**"),
            dropdown_row,
            button_row
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "This help menu isn't for you. Please run the `help` command yourself.",
                ephemeral=True
            )
            return False
        return True

    async def on_select(self, interaction: discord.Interaction):
        """Handle category dropdown selection."""
        try:
            # Defer first to prevent timeout
            await interaction.response.defer()
            
            # Get selected value from interaction data
            selected_category = interaction.data.get('values', [None])[0]
            
            if not selected_category or selected_category not in CATEGORY_COMMANDS:
                await interaction.followup.send(
                    "No commands found for this category.", 
                    ephemeral=True
                )
                return

            container = self._build_category_container(selected_category)
            self.clear_items()
            self.add_item(container)
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=self
            )
        except Exception as e:
            # Log the error for debugging
            print(f"Error in on_select: {e}")
            print(traceback.format_exc())
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)[:100]}",
                        ephemeral=True
                    )
                except:
                    pass

    async def on_back_home(self, interaction: discord.Interaction):
        """Go back to home menu."""
        try:
            await interaction.response.defer()
            
            container = self._build_home_container()
            self.clear_items()
            self.add_item(container)
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=self
            )
        except Exception as e:
            # Log the error for debugging
            print(f"Error in on_back_home: {e}")
            print(traceback.format_exc())
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)[:100]}",
                        ephemeral=True
                    )
                except:
                    pass


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.log_channel_id = None  # Will be set from config or environment

    async def log_error(self, ctx: commands.Context, error: Exception, error_type: str = "Error"):
        """Log errors to a designated channel and console."""
        # Log to console
        self.logger.error(f"[{error_type}] {error}", exc_info=True)
        
        # Try to send to log channel
        if self.log_channel_id:
            try:
                log_channel = self.bot.get_channel(self.log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title=f"Help Command Error",
                        description=f"**Error Type:** {error_type}",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(
                        name="Guild",
                        value=f"{ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'})",
                        inline=False
                    )
                    embed.add_field(
                        name="User",
                        value=f"{ctx.author} ({ctx.author.id})",
                        inline=False
                    )
                    embed.add_field(
                        name="Error Message",
                        value=f"```{str(error)[:1024]}```",
                        inline=False
                    )
                    embed.add_field(
                        name="Traceback",
                        value=f"```{traceback.format_exc()[:1024]}```",
                        inline=False
                    )
                    await log_channel.send(embed=embed)
            except Exception as log_error:
                self.logger.error(f"Failed to send error log: {log_error}")

    async def log_usage(self, ctx: commands.Context):
        """Log successful help command usage."""
        self.logger.info(
            f"Help command used by {ctx.author} ({ctx.author.id}) "
            f"in {ctx.guild.name if ctx.guild else 'DM'}"
        )
        
        if self.log_channel_id:
            try:
                log_channel = self.bot.get_channel(self.log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="Help Command Used",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{ctx.author} ({ctx.author.id})", inline=True)
                    embed.add_field(
                        name="Guild",
                        value=f"{ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'})",
                        inline=True
                    )
                    await log_channel.send(embed=embed)
            except Exception as log_error:
                self.logger.error(f"Failed to send usage log: {log_error}")

    @commands.command(name="help", aliases=["h"])
    async def help_command(self, ctx: commands.Context):
        """Display the help menu with error logging."""
        try:
            view = HelpView(self.bot, ctx.author)
            await ctx.send(view=view)
            await self.log_usage(ctx)
        except Exception as error:
            await self.log_error(ctx, error, "HelpCommandError")
            # Send user-friendly error message
            embed = discord.Embed(
                title="Help Command Error",
                description="An error occurred while loading the help menu. This has been reported to the developers.",
                color=discord.Color.red()
            )
            try:
                await ctx.send(embed=embed, ephemeral=True)
            except:
                await ctx.send("An error occurred while loading the help menu.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
