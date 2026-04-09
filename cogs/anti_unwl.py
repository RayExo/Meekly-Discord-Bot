import discord
from discord.ext import commands
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import VERIFIED_CHECK, CROSS_MARK, DISABLED
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail

class Unwhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS whitelisted_users (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        await self.db.commit()

    @commands.command(name='unwhitelist', aliases=['unwl'], help="Unwhitelist a user from antinuke")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def unwhitelist(self, ctx, member: discord.Member = None):
        if ctx.guild.member_count < 5:
            section = Section(
                TextDisplay(
                    f"# **Member Count Error**\n"
                    f">  Your Server Doesn't Meet My 5 Member Criteria"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Member Count Error Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# Server does not meet member criteria")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            return await ctx.send(view=view)

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            antinuke = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            section = Section(
                TextDisplay(
                    f"# **{CROSS_MARK} Access Denied**\n"
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
            return await ctx.send(view=view)

        if not antinuke or not antinuke[0]:
            section = Section(
                TextDisplay(
                    f"# **{ctx.guild.name} Security Settings**\n"
                    f"> Ohh NO! looks like your server doesn't enabled security\n\n"
                    f"> Current Status: {DISABLED}\n\n"
                    f"> To enable use `antinuke enable`"
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
            return await ctx.send(view=view)

        if not member:
            section = Section(
                TextDisplay(
                    f"# **__Unwhitelist Commands__**\n"
                    f"> **Removes user from whitelisted users which means that the antinuke module will now take actions on them if they trigger it.**\n\n"
                    f"__**Usage**__\n"
                    f"> `unwhitelist @user/id`\n"
                    f"> `unwl @user`"
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Unwhitelist Usage Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# Unwhitelist command usage information")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            return await ctx.send(view=view)

        async with self.db.execute(
            "SELECT * FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        ) as cursor:
            data = await cursor.fetchone()

        if not data:
            section = Section(
                TextDisplay(
                    f"# **{CROSS_MARK} Error**\n"
                    f"> <@{member.id}> is not a whitelisted member."
                ),
                accessory=Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                    description="Error Thumbnail"
                ),
                id=1
            )
            container = Container(
                section,
                Separator(),
                TextDisplay("-# User not whitelisted")
            )
            view = LayoutView(timeout=None)
            view.add_item(container)
            return await ctx.send(view=view)

        await self.db.execute(
            "DELETE FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        )
        await self.db.commit()

        section = Section(
            TextDisplay(
                f"# **{VERIFIED_CHECK} Success**\n"
                f"> User <@!{member.id}> has been removed from the whitelist."
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Success Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# User successfully unwhitelisted")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

async def setup(bot):
    await bot.add_cog(Unwhitelist(bot))