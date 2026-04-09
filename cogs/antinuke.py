import discord
from discord.ext import commands
import aiosqlite
import asyncio
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail, Button, View
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import EMOJIES, GEARS, CHECK as CHECK_EMOJI, INFO, ENABLED, DISABLED, CROSS as CROSS_EMOJI

class Antinuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS antinuke (
                guild_id INTEGER PRIMARY KEY,
                status BOOLEAN
            )
        ''')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS extraowners (
                guild_id INTEGER,
                owner_id INTEGER,
                PRIMARY KEY (guild_id, owner_id)
            )
        ''')
        await self.db.commit()

    async def enable_limit_settings(self, guild_id):
        default_limits = DEFAULT_LIMITS  # Define elsewhere, e.g., {"ban": 3, "kick": 3, ...}
        for action, limit in default_limits.items():
            await self.db.execute('INSERT OR REPLACE INTO limit_settings (guild_id, action_type, action_limit, time_window) VALUES (?, ?, ?, ?)', (guild_id, action, limit, TIME_WINDOW))
            await self.db.commit()

    async def disable_limit_settings(self, guild_id):
        await self.db.execute('DELETE FROM limit_settings WHERE guild_id = ?', (guild_id,))
        await self.db.commit()

    @commands.command(name='antinuke', aliases=['antiwizz', 'anti'], help="Enables/Disables Anti-Nuke Module in the server")
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx, option: str = None):
        guild_id = ctx.guild.id
        pre = ctx.prefix

        async with self.db.execute('SELECT status FROM antinuke WHERE guild_id = ?', (guild_id,)) as cursor:
            row = await cursor.fetchone()

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            section = Section(
                TextDisplay(
                    f"# **{CROSS_EMOJI} Access Denied**\n"
                    f"> Only Server Owner or Extra Owner can Run this Command!"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Access Denied Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# Command restricted to server owner or extra owners")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)
            return

        is_activated = row[0] if row else False

        if option is None:
            section = Section(
                TextDisplay(
                    f"# **__Antinuke__**\n"
                    f"> Boost your server security with Antinuke! It automatically bans any admins involved in suspicious activities, ensuring the safety of your whitelisted members. Strengthen your defenses – activate Antinuke today!\n\n"
                    f"__**Antinuke Enable**__\n> To Enable Antinuke, Use - `{pre}antinuke enable`\n\n"
                    f"__**Antinuke Disable**__\n> To Disable Antinuke, Use - `{pre}antinuke disable`"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Antinuke Info Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# Antinuke command usage information")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)

        elif option.lower() == 'enable':
            if is_activated:
                section = Section(
                    TextDisplay(
                        f"# **Security Settings For {ctx.guild.name}**\n"
                        f"> Your server __**already has Antinuke enabled.**__\n"
                        f"> Current Status: {ENABLED} Enabled\n"
                        f"> To Disable use `{pre}antinuke disable`"
                    ),
                    accessory=Thumbnail(
                        media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                        description="Antinuke Status Thumbnail"
                    ),
                    id=1
                )
                container = Container(
                    section,
                    Separator(),
                    TextDisplay("-# Antinuke already enabled")
                )
                view = LayoutView(timeout=None)
                view.add_item(container)
                await ctx.send(view=view)
            else:
                setup_embed = discord.Embed(
                    title=f"Antinuke Setup {GEARS}",
                    description=f"{CHECK_EMOJI} | Initializing Quick Setup!",
                    color=0x000000
                )
                setup_message = await ctx.send(embed=setup_embed)

                if not ctx.guild.me.guild_permissions.administrator:
                    setup_embed.description += f"\n{INFO} | Setup failed: Missing **Administrator** permission."
                    await setup_message.edit(embed=setup_embed)
                    return

                await asyncio.sleep(1)
                setup_embed.description += f"\n{CHECK_EMOJI} | Checking Meekly's role position for optimal configuration..."
                await setup_message.edit(embed=setup_embed)

                await asyncio.sleep(1)
                setup_embed.description += f"\n{CHECK_EMOJI} | Crafting and configuring the Meekly Supreme role..."
                await setup_message.edit(embed=setup_embed)

                try:
                    role = await ctx.guild.create_role(
                        name="Meekly Supreme",
                        color=0x4D3164,
                        permissions=discord.Permissions(administrator=True),
                        hoist=False,
                        mentionable=False,
                        reason="Antinuke setup Role Creation"
                    )
                    await ctx.guild.me.add_roles(role)
                except discord.Forbidden:
                    setup_embed.description += f"\n{INFO} | Setup failed: Insufficient permissions to create role."
                    await setup_message.edit(embed=setup_embed)
                    return
                except discord.HTTPException as e:
                    setup_embed.description += f"\n{INFO} | Setup failed: HTTPException: {e}\nCheck Guild **Audit Logs**."
                    await setup_message.edit(embed=setup_embed)
                    return

                await asyncio.sleep(1)
                setup_embed.description += f"\n{CHECK_EMOJI} | Ensuring precise placement of the Meekly Supreme role..."
                await setup_message.edit(embed=setup_embed)

                try:
                    await ctx.guild.edit_role_positions(positions={role: 1})
                except discord.Forbidden:
                    setup_embed.description += f"\n{INFO} | Setup failed: Insufficient permissions to move role."
                    await setup_message.edit(embed=setup_embed)
                    return
                except discord.HTTPException as e:
                    setup_embed.description += f"\n{INFO} | Setup failed: HTTPException: {e}."
                    await setup_message.edit(embed=setup_embed)
                    return

                await asyncio.sleep(1)
                setup_embed.description += f"\n{CHECK_EMOJI} | Safeguarding your changes..."
                await setup_message.edit(embed=setup_embed)

                await asyncio.sleep(1)
                setup_embed.description += f"\n{CHECK_EMOJI} | Activating the Antinuke Modules for enhanced security...!!"
                await setup_message.edit(embed=setup_embed)

                await self.db.execute('INSERT OR REPLACE INTO antinuke (guild_id, status) VALUES (?, ?)', (guild_id, True))
                await self.db.commit()

                await asyncio.sleep(1)
                await setup_message.delete()

                enabled_modules = [
                    "Anti Ban", "Anti Kick", "Anti Bot", "Anti Channel Create", "Anti Channel Delete",
                    "Anti Channel Update", "Anti Everyone/Here", "Anti Role Create", "Anti Role Delete",
                    "Anti Role Update", "Anti Member Update", "Anti Guild Update", "Anti Integration",
                    "Anti Webhook Create", "Anti Webhook Delete", "Anti Webhook Update", "Anti Prune", "Auto Recovery"
                ]
                section = Section(
                    TextDisplay(
                        f"# **Security Settings For {ctx.guild.name}**\n"
                        f"> Tip: For optimal functionality of the AntiNuke Module, please ensure that my role has **Administration** permissions and is positioned at the **Top** of the roles list\n\n"
                        f"> __**{len(enabled_modules)} Modules Enabled**__\n"
                        f">>> {chr(10).join([f'{ENABLED} **{module}**' for module in enabled_modules])}"
                    ),
                    accessory=Thumbnail(
                        media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                        description="Antinuke Enabled Thumbnail"
                    ),
                    id=1
                )
                container = Container(
                    section,
                    Separator(),
                    TextDisplay("-# Successfully Enabled Antinuke for this server | Powered by Meekly Development™")
                )
                view = LayoutView(timeout=None)
                view.add_item(container)

                button_view = View()
                button_view.add_item(Button(label="Show Punishment Type", custom_id="show_punishment"))
                await ctx.send(view=button_view)

        elif option.lower() == 'disable':
            if not is_activated:
                section = Section(
                    TextDisplay(
                        f"# **Security Settings For {ctx.guild.name}**\n"
                        f"> Uhh, looks like your server hasn't enabled Antinuke.\n"
                        f"> Current Status: {DISABLED} Disabled\n"
                        f"> To Enable use `{pre}antinuke enable`"
                    ),
                    accessory=Thumbnail(
                        media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                        description="Antinuke Status Thumbnail"
                    ),
                    id=1
                )
                container = Container(
                    section,
                    Separator(),
                    TextDisplay("-# Antinuke not enabled")
                )
                view = LayoutView(timeout=None)
                view.add_item(container)
                await ctx.send(view=view)
            else:
                await self.db.execute('DELETE FROM antinuke WHERE guild_id = ?', (guild_id,))
                await self.db.commit()
                section = Section(
                    TextDisplay(
                        f"# **Security Settings For {ctx.guild.name}**\n"
                        f"> Successfully disabled Antinuke for this server.\n"
                        f"> Current Status: {DISABLED} Disabled\n"
                        f"> To Enable use `{pre}antinuke enable`"
                    ),
                    accessory=Thumbnail(
                        media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                        description="Antinuke Disabled Thumbnail"
                    ),
                    id=1
                )
                container = Container(
                    section,
                    Separator(),
                    TextDisplay("-# Antinuke disabled")
                )
                view = LayoutView(timeout=None)
                view.add_item(container)
                await ctx.send(view=view)
        else:
            section = Section(
                TextDisplay(
                    f"# **Invalid Option**\n"
                    f"> Invalid option. Please use `enable` or `disable`."
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Invalid Option Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# Invalid command option")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get('custom_id') == 'show_punishment':
            section = Section(
                TextDisplay(
                    f"# **Punishment Types for Changes Made by Unwhitelisted Admins/Mods**\n"
                    f"> **Anti Ban:** Ban\n"
                    f"> **Anti Kick:** Ban\n"
                    f"> **Anti Bot:** Ban the bot Inviter\n"
                    f"> **Anti Channel Create/Delete/Update:** Ban\n"
                    f"> **Anti Everyone/Here:** Remove the message & 1 hour timeout\n"
                    f"> **Anti Role Create/Delete/Update:** Ban\n"
                    f"> **Anti Member Update:** Ban\n"
                    f"> **Anti Guild Update:** Ban\n"
                    f"> **Anti Integration:** Ban\n"
                    f"> **Anti Webhook Create/Delete/Update:** Ban\n"
                    f"> **Anti Prune:** Ban\n"
                    f"> **Auto Recovery:** Automatically recover damaged channels, roles, and settings\n\n"
                    f"> Note: In the case of member updates, action will be taken only if the role contains dangerous permissions such as Ban Members, Administrator, Manage Guild, Manage Channels, Manage Roles, Manage Webhooks, or Mention Everyone"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=interaction.client.user.display_avatar.url),
                    description="Punishment Types Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# These punishment types are fixed and assigned as required to ensure guild security/protection")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            await interaction.response.send_message(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Antinuke(bot))