import discord
from discord.ext import commands
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import ENABLED, DISABLED, CROSS_MARK, ERROR_X, TICK, VERIFIED_CHECK


class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    
    #@commands.Cog.listener()
    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS whitelisted_users (
                guild_id INTEGER,
                user_id INTEGER,
                ban BOOLEAN DEFAULT FALSE,
                kick BOOLEAN DEFAULT FALSE,
                prune BOOLEAN DEFAULT FALSE,
                botadd BOOLEAN DEFAULT FALSE,
                serverup BOOLEAN DEFAULT FALSE,
                memup BOOLEAN DEFAULT FALSE,
                chcr BOOLEAN DEFAULT FALSE,
                chdl BOOLEAN DEFAULT FALSE,
                chup BOOLEAN DEFAULT FALSE,
                rlcr BOOLEAN DEFAULT FALSE,
                rlup BOOLEAN DEFAULT FALSE,
                rldl BOOLEAN DEFAULT FALSE,
                meneve BOOLEAN DEFAULT FALSE,
                mngweb BOOLEAN DEFAULT FALSE,
                mngstemo BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        await self.db.commit()

    @commands.command(name='whitelist', aliases=['wl'], help="Whitelists a user from antinuke for a specific action.")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)

    async def whitelist(self, ctx, member: discord.Member = None):
        if ctx.guild.member_count < 5:
            embed = discord.Embed(
                color=0x000000,
                description="Your Server Doesn't Meet My 5 Member Criteria"
            )
            return await ctx.send(embed=embed)

        prefix=ctx.prefix

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
            embed = discord.Embed(title=f"{CROSS_MARK} Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} Security Settings\n"
                    "Ohh No! looks like your server doesn't enabled Antinuke\n\n"
                    f"Current Status : {DISABLED}\n\n"
                    f"To enable use `{prefix}antinuke enable` **"
                )
            )
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            return await ctx.send(embed=embed)

        if not member:
            embed = discord.Embed(
                color=0x000000,
                title="__**Whitelist Commands**__",
                description="**Adding a user to the whitelist means that no actions will be taken against them if they trigger the Anti-Nuke Module.**"
            )
            embed.add_field(name="__**Usage**__", value=f"`{prefix}whitelist @user/id`\n`{prefix}wl @user`")
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT * FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        ) as cursor:
            data = await cursor.fetchone()

        if data:
            embed = discord.Embed(title=f"{CROSS_MARK} Error",
                color=0x000000,
                description=f"<@{member.id}> is already a whitelisted member, **Unwhitelist** the user and try again."
            )
            return await ctx.send(embed=embed)

        await self.db.execute(
            "INSERT INTO whitelisted_users (guild_id, user_id) VALUES (?, ?)",
            (ctx.guild.id, member.id)
        )
        await self.db.commit()

        options = [
            discord.SelectOption(label="Ban", description="Whitelist a member with ban permission", value="ban"),
            discord.SelectOption(label="Kick", description="Whitelist a member with kick permission", value="kick"),
            discord.SelectOption(label="Prune", description="Whitelist a member with prune permission", value="prune"),
            discord.SelectOption(label="Bot Add", description="Whitelist a member with bot add permission", value="botadd"),
            discord.SelectOption(label="Server Update", description="Whitelist a member with server update permission", value="serverup"),
            discord.SelectOption(label="Member Update", description="Whitelist a member with member update permission", value="memup"),
            discord.SelectOption(label="Channel Create", description="Whitelist a member with channel create permission", value="chcr"),
            discord.SelectOption(label="Channel Delete", description="Whitelist a member with channel delete permission", value="chdl"),
            discord.SelectOption(label="Channel Update", description="Whitelist a member with channel update permission", value="chup"),
            discord.SelectOption(label="Role Create", description="Whitelist a member with role create permission", value="rlcr"),
            discord.SelectOption(label="Role Update", description="Whitelist a member with role update permission", value="rlup"),
            discord.SelectOption(label="Role Delete", description="Whitelist a member with role delete permission", value="rldl"),
            discord.SelectOption(label="Mention Everyone", description="Whitelist a member with mention everyone permission", value="meneve"),
            discord.SelectOption(label="Manage Webhook", description="Whitelist a member with manage webhook permission", value="mngweb")
        ]

        select = discord.ui.Select(placeholder="Choose Your Options", min_values=1, max_values=len(options), options=options, custom_id="wl")
        button = discord.ui.Button(label="Add This User To All Categories", style=discord.ButtonStyle.primary, custom_id="catWl")

        view = discord.ui.View()
        view.add_item(select)
        view.add_item(button)

        embed = discord.Embed(
            title=ctx.guild.name,
            color=0x000000,
            description=(
                f"{DISABLED} : **Ban**\n"
                f"{DISABLED} : **Kick**\n"
                f"{DISABLED} : **Prune**\n"
                f"{DISABLED} : **Bot Add**\n"
                f"{DISABLED} : **Server Update**\n"
                f"{DISABLED} : **Member Update**\n"
                f"{DISABLED} : **Channel Create**\n"
                f"{DISABLED} : **Channel Delete**\n"
                f"{DISABLED} : **Channel Update**\n"
                f"{DISABLED} : **Role Create**\n"
                f"{DISABLED} : **Role Delete**\n"
                f"{DISABLED} : **Role Update**\n"
                f"{DISABLED} : **Mention** @everyone\n"
                f"{DISABLED} : **Webhook Management**"
                
            )
        )
        embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
        embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"Developed by Meekly Development™")

        msg = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            if interaction.data["custom_id"] == "catWl":
                
                await self.db.execute(
                    "UPDATE whitelisted_users SET ban = ?, kick = ?, prune = ?, botadd = ?, serverup = ?, memup = ?, chcr = ?, chdl = ?, chup = ?, rlcr = ?, rldl = ?, rlup = ?, meneve = ?, mngweb = ?, mngstemo = ? WHERE guild_id = ? AND user_id = ?",
                    (True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, ctx.guild.id, member.id)
                )
                await self.db.commit()

                
                embed = discord.Embed(
                    title=ctx.guild.name,
                    color=0x000000,
                    description=(
                        f"{ENABLED} : **Ban**\n"
                        f"{ENABLED} : **Kick**\n"
                        f"{ENABLED} : **Prune**\n"
                        f"{ENABLED} : **Bot Add**\n"
                        f"{ENABLED} : **Server Update**\n"
                        f"{ENABLED} : **Member Update**\n"
                        f"{ENABLED} : **Channel Create**\n"
                        f"{ENABLED} : **Channel Delete**\n"
                        f"{ENABLED} : **Channel Update**\n"
                        f"{ENABLED} : **Role Create**\n"
                        f"{ENABLED} : **Role Delete**\n"
                        f"{ENABLED} : **Role Update**\n"
                        f"{ENABLED} : **Mention** @everyone\n"
                        f"{ENABLED} : **Webhook Management**"
                        
                    )
                )
                embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
                embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
                embed.set_thumbnail(url=self.bot.user.avatar.url)
                embed.set_footer(text=f"Developed by Meekly Development™")

                await interaction.response.edit_message(embed=embed, view=None)
            else:
                
                fields = {
                    'ban': 'Ban',
                    'kick': 'Kick',
                    'prune': 'Prune',
                    'botadd': 'Bot Add',
                    'serverup': 'Server Update',
                    'memup': 'Member Update',
                    'chcr': 'Channel Create',
                    'chdl': 'Channel Delete',
                    'chup': 'Channel Update',
                    'rlcr': 'Role Create',
                    'rldl': 'Role Delete',
                    'rlup': 'Role Update',
                    'meneve': 'Mention Everyone',
                    'mngweb': 'Manage Webhooks'
                }

                embed_description = "\n".join(f"{DISABLED} : **{name}**" for key, name in fields.items())

                
                for value in interaction.data["values"]:
                    await self.db.execute(
                        f"UPDATE whitelisted_users SET {value} = ? WHERE guild_id = ? AND user_id = ?",
                        (True, ctx.guild.id, member.id)
                    )
                    embed_description = embed_description.replace(f"{ENABLED} : **{fields[value]}**", f"{ENABLED} : **{fields[value]}**")

                await self.db.commit()

                
                embed = discord.Embed(
                    title=ctx.guild.name,
                    color=0x000000,
                    description=embed_description
                )
                embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
                embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
                embed.set_thumbnail(url=self.bot.user.avatar.url)
                embed.set_footer(text=f"Developed by Meekly Development™")

                await interaction.response.edit_message(embed=embed, view=None)
        except TimeoutError:
            await msg.edit(view=None)


    @commands.command(name='whitelisted', aliases=['wlist'], help="Shows the list of whitelisted users.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def whitelisted(self, ctx):
        if ctx.guild.member_count < 5:
            embed = discord.Embed(
                color=0x000000,
                description="Your Server Doesn't Meet My 5 Member Criteria"
            )
            return await ctx.send(embed=embed)

        pre=ctx.prefix

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
            embed = discord.Embed(title=f"{CROSS_MARK} Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} security settings\n"
                    "Ohh NO! looks like your server doesn't enabled security\n\n"
                    "Current Status : {DISABLED}\n\n"
                    f"To enable use `{pre}antinuke enable` **"
                )
            )
            return await ctx.send(embed=embed)


        async with self.db.execute(
            "SELECT user_id FROM whitelisted_users WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            data = await cursor.fetchall()

        if not data:
            embed = discord.Embed(title=f"{CROSS_MARK} Error",
                color=0x000000,
                description="No whitelisted users found."
            )
            return await ctx.send(embed=embed)

        whitelisted_users = [self.bot.get_user(user_id[0]) for user_id in data]
        whitelisted_users_str = ", ".join(f"<@!{user.id}>" for user in whitelisted_users if user)

        embed = discord.Embed(
            color=0x000000,
            title=f"__Whitelisted Users for {ctx.guild.name}__",
            description=whitelisted_users_str
        )
        await ctx.send(embed=embed)


    @commands.command(name="whitelistreset", aliases=['wlreset'], help="Resets the whitelisted users.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def whitelistreset(self, ctx):
        if ctx.guild.member_count < 5:
            embed = discord.Embed(
                color=0x000000,
                description="Your Server Doesn't Meet My 5 Member Criteria"
            )
            return await ctx.send(embed=embed)

        pre=ctx.prefix

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
            embed = discord.Embed(title=f"{CROSS_MARK} Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} Security Settings\n"
                    "Ohh NO! looks like your server doesn't enabled security\n\n"
                    "Current Status : {DISABLED}\n\n"
                    f"To enable use `{pre}antinuke enable` **"
                )
            )
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT user_id FROM whitelisted_users WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            data = await cursor.fetchall()


        if not data:
            embed = discord.Embed(title=f"{CROSS_MARK} Error",
                color=0x000000,
                description="No whitelisted users found."
            )
            return await ctx.send(embed=embed)

        await self.db.execute("DELETE FROM whitelisted_users WHERE guild_id = ?", (ctx.guild.id,))
        await self.db.commit()
        embed = discord.Embed(title=f"{VERIFIED_CHECK} Success",
            color=0x000000,
            description=f"Removed all whitelisted members from {ctx.guild.name}"
        )
        await ctx.send(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Whitelist(bot))