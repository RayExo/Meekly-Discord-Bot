import discord
from discord.ext import commands
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import EMOJIES, ENABLED, DISABLED, DISABLED_OFF, VERIFIED_CHECK, CHECK as CHECK_EMOJI, CROSS as CROSS_EMOJI

class ShowRules(discord.ui.View):
    def __init__(self, author, selected_events):
        super().__init__(timeout=60)
        self.author = author
        self.selected_events = selected_events

    @discord.ui.button(label="Show Rules", style=discord.ButtonStyle.secondary)
    async def show_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return

        rules = {
            "Anti NSFW link": "__**Anti NSFW Link**__:\n• Takes action if the message contains a NSFW link.\n• Default punishment: Block message (unchangeable)",
            "Anti caps": "__**Anti Caps**__:\n• Takes action if the message contains >70% caps.\n• Messages under 45 characters are bypassed\n• Default punishment: Mute (1 minutes)",
            "Anti link": "__**Anti Link**__:\n• Takes action if the message contains a link.\n• Server invites, Spotify Music and GIF links are bypassed\n• Default punishment: Mute (7 minutes)",
            "Anti invites": "__**Anti Invites**__:\n• Takes action if the message contains a Discord server invite.\n• Invites from the current server are bypassed\n• Default punishment: Mute (12 minutes)",
            "Anti emoji spam": "__**Anti Emoji Spam**__:\n• Takes action if a message contains more than 5 emojis.\n• Default punishment: Mute (1 minute)",
            "Anti mass mention": "__**Anti Mass Mention**__:\n• Takes action if a message contains more than 4 mentions.\n• Default punishment: Mute (3 minutes)",
            "Anti spam": "__**Anti Spam**__:\n• Takes action if more than 5 messages are sent rapidly in a short time.\n• Default punishment: Mute (12 minutes)",
        }

        enabled_rules = "\n\n".join([rules[event] for event in self.selected_events])

        embed = discord.Embed(title="Enabled Automod Rules", description=enabled_rules, color=0x4D3164)
        embed.set_footer(text="Punishment type of each event is changeable except for Anti NSFW.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        

class ConfirmDisable(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=30)
        self.author = author
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return
        self.value = True
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return
        self.value = False
        self.stop()


        
class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_punishment = "Mute"
        self.bot.loop.create_task(self.init_db())

    async def get_exempt_roles_channels(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            roles_cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'role'", (guild_id,))
            channels_cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'channel'", (guild_id,))
            
            exempt_roles = [discord.Object(id) for (id,) in await roles_cursor.fetchall()]
            exempt_channels = [discord.Object(id) for (id,) in await channels_cursor.fetchall()]
            
            return exempt_roles, exempt_channels
            

    async def is_automod_enabled(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT enabled FROM automod WHERE guild_id = ?", (guild_id,))
            result = await cursor.fetchone()
            return result is not None and result[0] == 1

    async def update_punishments(self, guild_id, event, punishment):
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod_punishments (guild_id, event, punishment) VALUES (?, ?, ?)", (guild_id, event, punishment))
            await db.commit()

    async def get_current_punishments(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            async with db.execute(
                "SELECT event, punishment FROM automod_punishments WHERE guild_id = ? AND event != 'Anti NSFW link'", 
                (guild_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def is_anti_nsfw_enabled(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT punishment FROM automod_punishments WHERE guild_id = ? AND event = 'Anti NSFW link'", (guild_id,))
            result = await cursor.fetchone()
            return result is not None

                

    async def init_db(self):
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_punishments (
                    guild_id INTEGER,
                    event TEXT,
                    punishment TEXT,
                    PRIMARY KEY (guild_id, event)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_ignored (
                    guild_id INTEGER,
                    type TEXT,
                    id INTEGER,
                    PRIMARY KEY (guild_id, type, id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_logging (
                    guild_id INTEGER,
                    log_channel INTEGER,
                    PRIMARY KEY (guild_id)
                )
            """)
            await db.commit()

    @commands.hybrid_group(invoke_without_command=True)
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def automod(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @automod.command(name="enable", help="Enable Automod on the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def enable(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"**{DISABLED} Your Server already has Automoderation Enabled.**\n\nCurrent Status: {ENABLED} Enabled\nTo Disable use `{ctx.prefix}automod disable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        events = [
            "Anti spam",
            "Anti caps",
            "Anti link",
            "Anti invites",
            "Anti mass mention",
            "Anti emoji spam",
            "Anti NSFW link",
        ]

        embed = discord.Embed(title=f"{ctx.guild.name}'s Automod Setup", color=0x000000)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.description = "\n".join([f"{DISABLED} : {event}" for event in events])

        select_menu = discord.ui.Select(placeholder="Select events to enable", min_values=1, max_values=len(events), options=[
            discord.SelectOption(label=event, value=event) for event in events
        ])

        async def select_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this menu.", ephemeral=True)
                return
            selected_events = select_menu.values
            await self.enable_automod(ctx, guild_id, selected_events, interaction)
        select_menu.callback = select_callback

        enable_all_button = discord.ui.Button(label="Enable for All Events", style=discord.ButtonStyle.primary)

        async def enable_all_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return
                
            await self.enable_automod(ctx, guild_id, events, interaction)

        enable_all_button.callback = enable_all_callback

        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)

        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return
                
            select_menu.disabled = True
            enable_all_button.disabled = True
            cancel_button.disabled = True
            await interaction.response.edit_message(content="Automod Setup Cancelled", embed=embed, view=view)

        cancel_button.callback = cancel_callback

        view = discord.ui.View()
        view.add_item(select_menu)
        view.add_item(enable_all_button)
        view.add_item(cancel_button)

        await ctx.send(embed=embed, view=view)
        

    async def enable_automod(self, ctx, guild_id, selected_events, interaction):

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod (guild_id, enabled) VALUES (?, 1)", (guild_id,))
            for event in selected_events:
                await db.execute("INSERT OR REPLACE INTO automod_punishments (guild_id, event, punishment) VALUES (?, ?, ?)", (guild_id, event, self.default_punishment))
            await db.commit()

        
        if "Anti NSFW link" in selected_events:
            exempt_roles, exempt_channels = await self.get_exempt_roles_channels(guild_id)
            nsfw_keywords = ["porn", "xxx", "adult", "sex", "nsfw", "xnxx", "onlyfans", "brazzers", "xhamster", "xvideos", "pornhub", "redtube", "livejasmin", "youporn" , "tube8", "pornhat", "swxvid", "ixxx", "pornhat"]

            try:
                await interaction.guild.create_automod_rule(
                    name="Anti NSFW Links",
                    event_type=discord.AutoModRuleEventType.message_send,
                    trigger=discord.AutoModTrigger(
                        type=discord.AutoModRuleTriggerType.keyword,
                        keyword_filter=nsfw_keywords,
                    ),
                    actions=[
                        discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message),
                    ],
                    enabled=True,
                    exempt_roles=exempt_roles,
                    exempt_channels=exempt_channels,
                    reason="Automod - Anti NSFW Link setup"
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                print(f"Automod rule-create error: {e}")

        embed = discord.Embed(title="Automod Enabled Successfully", color=0x000000)
        embed.description = "\n".join([f"{ENABLED} : {event}" for event in selected_events] +
                                       [f"{ENABLED} : {event}" for event in ["Anti spam", "Anti caps", "Anti link", "Anti invites", "Anti mass mention", "Anti emoji spam", "Anti NSFW link"] if event not in selected_events])

        enable_logging_button = discord.ui.Button(label="Enable Automod Logging", style=discord.ButtonStyle.success)

        async def enable_logging_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return

            if not interaction.guild.me.guild_permissions.manage_channels:
                await interaction.response.send_message("I do not have permission to create channels.", ephemeral=True)
                return

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
            }

            try:
                for channel in interaction.guild.channels:
                    if channel.name == "automod-logs":
                        await interaction.response.send_message(f"A logging channel with the name \"automod-logs\" already exists.", ephemeral=True)
                        return
                log_channel = await interaction.guild.create_text_channel("automod-logs", overwrites=overwrites)
                guild_id = interaction.guild.id

                async with aiosqlite.connect("db/automod.db") as db:
                    await db.execute("INSERT OR REPLACE INTO automod_logging (guild_id, log_channel) VALUES (?, ?)", (guild_id, log_channel.id))
                    await db.commit()

                await interaction.response.send_message(f"Logging channel {log_channel.mention} created and set successfully.", ephemeral=True)

            except discord.HTTPException as e:
                await interaction.response.send_message(f"Failed to create logging channel: {e}", ephemeral=True)

        enable_logging_button.callback = enable_logging_callback


        view = ShowRules(ctx.author, selected_events)
        view.add_item(enable_logging_button)

        
        await interaction.response.edit_message(content="Setup Completed.", embed=embed, view=view)


    

    @automod.command(name="punishment", aliases=["punish"], help="Set the punishment for automod events.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def punishment(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        current_punishments = await self.get_current_punishments(guild_id)
        embed = discord.Embed(title=f"Current Automod Punishments for {ctx.guild.name}", color=0x000000)
        punishment_map = {}
        for event, punishment in current_punishments:
            punishment_map[event] = punishment or "None"
            embed.add_field(name=event, value=punishment or "None", inline=False)
            embed.set_footer(text="Keep the default punishment (Mute) to prevent server raids without kicking or banning raiders", icon_url=self.bot.user.avatar.url)
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        events = [event for event, _ in current_punishments]
        select = discord.ui.Select(placeholder="Select events to update punishment", options=[
            discord.SelectOption(label=event) for event in events
        ], min_values=1, max_values=len(events))

        async def select_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
                return

            selected_events = select.values
            await interaction.response.send_message("You selected: " + ", ".join(selected_events))

            punishment_buttons = discord.ui.View()
            for punishment in ["Mute", "Kick", "Ban"]:
                button = discord.ui.Button(label=punishment, style=discord.ButtonStyle.danger)

                async def punishment_callback(button_interaction, selected_events=selected_events, punishment=punishment):
                    if button_interaction.user != ctx.author:
                        await button_interaction.response.send_message("You cannot interact with this button.", ephemeral=True)
                        return

                    
                    for event in selected_events:
                        await self.update_punishments(guild_id, event, punishment)

                    updated_punishments = await self.get_current_punishments(guild_id)
                    updated_embed = discord.Embed(title=f"Updated Automod Punishments for {ctx.guild.name}", color=0x000000)
                    for event, punishment in updated_punishments:
                        updated_embed.add_field(name=event, value=punishment or "None", inline=False)
                        updated_embed.set_footer(text="You can modify the punishments by running the command again.", icon_url=self.bot.user.avatar.url)
                        updated_embed.set_thumbnail(url=self.bot.user.avatar.url)

                    
                    await button_interaction.response.edit_message(embed=updated_embed, view=None)

                button.callback = punishment_callback
                punishment_buttons.add_item(button)

            await interaction.edit_original_response(view=punishment_buttons)

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)

        await ctx.send(embed=embed, view=view)




    @automod.group(name="ignore", aliases=["exempt", "whitelist", "wl"], help="Manage whitelisted roles and channels for Automod.")
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def ignore(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            

    @ignore.command(name="channel", help="Add a channel to the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_channel(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT 1 FROM automod_ignored WHERE guild_id = ? AND type = 'channel' AND id = ?", (guild_id, channel.id))
            if await cursor.fetchone() is not None:
                embed = discord.Embed(title="__Channel Already Whitelisted!__", description=f"{DISABLED} The channel {channel.mention} is already in the ignore list.\n\n➜ Use **{ctx.prefix}automod unignore channel {channel.mention}** to remove it.", color=0x000000)
                
                embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=embed)
                return
                
            count_cursor = await db.execute("SELECT COUNT(*) FROM automod_ignored WHERE guild_id = ? AND type = 'channel'", (guild_id,))
            count = await count_cursor.fetchone()

            if count[0] >= 10:
                await ctx.send("You can only ignore up to 10 channels.")
                return

            await db.execute("INSERT OR REPLACE INTO automod_ignored (guild_id, type, id) VALUES (?, 'channel', ?)", (guild_id, channel.id))
            await db.commit()
            
            if await self.is_anti_nsfw_enabled(guild_id):
                try:
                    rules = await ctx.guild.fetch_automod_rules()
                    for rule in rules:
                        if rule.name == "Anti NSFW Links":
                            exempt_channels = list(rule.exempt_channels)  
                            exempt_channels.append(channel) 
                            await rule.edit(
                                exempt_channels=exempt_channels,
                                reason="Channel exempted from Anti NSFW Links via automod ignore command"
                            )
                            break
                except discord.HTTPException:
                    pass

                    
            success = discord.Embed(title=f"{CHECK_EMOJI} Channel Whitelisted", description=f"The channel {channel.mention} has been added to the ignore list \n\n➜ Use `{ctx.prefix}automod ignore show` to view the ignore list.", color=0x000000)
            success.set_thumbnail(url=self.bot.user.avatar.url)
            success.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        await ctx.send(embed=success)

    @ignore.command(name="role", help="Add a role to the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_role(self, ctx, role: discord.Role):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT 1 FROM automod_ignored WHERE guild_id = ? AND type = 'role' AND id = ?", (guild_id, role.id))
            
            if await cursor.fetchone() is not None:
                embed = discord.Embed(title="__Role Already Whitelisted!__", description=f"{DISABLED} The role {role.mention} is already in the ignore list.\n\n➜ Use **{ctx.prefix}automod unignore role {role.mention}** to remove it.", color=0x000000)
                embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=embed)
                return
                
            count_cursor = await db.execute("SELECT COUNT(*) FROM automod_ignored WHERE guild_id = ? AND type = 'role'", (guild_id,))
            count = await count_cursor.fetchone()


            if count[0] >= 10:
                await ctx.send("You can only ignore up to 10 roles.")
                return

            await db.execute("INSERT OR REPLACE INTO automod_ignored (guild_id, type, id) VALUES (?, 'role', ?)", (guild_id, role.id))
            await db.commit()

            if await self.is_anti_nsfw_enabled(guild_id):
                try:
                    rules = await ctx.guild.fetch_automod_rules()
                    for rule in rules:
                        if rule.name == "Anti NSFW Links":
                            exempt_roles = list(rule.exempt_roles)  
                            exempt_roles.append(role) 
                            await rule.edit(
                                exempt_roles=exempt_roles,
                                reason="Role exempted from Anti NSFW Links via automod ignore command"
                            )
                            break
                except discord.HTTPException:
                    pass
                    
                    
            success = discord.Embed(title=f"{CHECK_EMOJI} Role Whitelisted", description=f"The role {role.mention} has been added to the ignore list \n\n➜ Use `{ctx.prefix}automod ignore show` to view the ignore list.", color=0x000000)
            success.set_thumbnail(url=self.bot.user.avatar.url)
            success.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        await ctx.send(embed=success)

    @ignore.command(name="show", aliases=["view", "list", "config"], help="Show the whitelisted roles and channels.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_show(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT type, id FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            ignored_items = await cursor.fetchall()

        if not ignored_items:
            await ctx.reply("No ignored channels or roles found.")
            return

        ignored_channels = []
        ignored_roles = []

        for item_type, item_id in ignored_items:
            if item_type == "channel":
                channel = ctx.guild.get_channel(item_id)
                if channel:
                    ignored_channels.append(f"{channel.mention} (ID: {channel.id})")
                else:
                    ignored_channels.append(f"Deleted Channel (ID: {item_id})")
            elif item_type == "role":
                role = ctx.guild.get_role(item_id)
                if role:
                    ignored_roles.append(f"{role.mention} (ID: {role.id})")
                else:
                    ignored_roles.append(f"Deleted Role (ID: {item_id})")

        embed = discord.Embed(title="Ignored Channels & Roles for Automod", color=0x000000)

        if ignored_channels:
            embed.add_field(name="__Ignored Channels:__", value="\n".join(ignored_channels), inline=False)
        else:
            embed.add_field(name="__Ignored Channels:__", value="None", inline=False)

        if ignored_roles:
            embed.add_field(name="__Ignored Roles:__", value="\n".join(ignored_roles), inline=False)
        else:
            embed.add_field(name="__Ignored Roles:__", value="None", inline=False)

        await ctx.send(embed=embed)


    @ignore.command(name="reset", help="Reset the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_reset(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            await db.commit()
        embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"** {CHECK_EMOJI} | All ignored channels and roles have been reset!**\n\nTo view current Automod settings use `{ctx.prefix}automod config`", color=0x4D3164)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)
        

    @automod.group(name="unignore", aliases=["unwhitelist", "unwl"], invoke_without_command=True, help="Remove channels and roles from the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unignore(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @unignore.command(name="channel", help="Remove a channel from the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unignore_channel(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED_OFF} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if await self.is_anti_nsfw_enabled(guild_id):
            try:
                rules = await ctx.guild.fetch_automod_rules()
                for rule in rules:
                    if rule.name == "Anti NSFW Links":
                        exempt_channels = list(rule.exempt_channels)  
                        exempt_channels = [ch for ch in exempt_channels if ch.id != channel.id]
                        await rule.edit(
                            exempt_channels=exempt_channels,
                            reason="Channel removed from Anti NSFW Links exemption via automod unignore command"
                        )
                        break
            except discord.HTTPException:
                pass
        
        async with aiosqlite.connect("db/automod.db") as db:
            result = await db.execute("DELETE FROM automod_ignored WHERE guild_id = ? AND type = 'channel' AND id = ?", (guild_id, channel.id))
            await db.commit()

        if result.rowcount > 0:
            embed = discord.Embed(title=f"{CHECK_EMOJI} Success", description=f"{channel.mention} has been removed from the automod ignore list.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title=f"{CROSS_EMOJI} Error", description=f"{channel.mention} is not in the automod ignore list.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            

    @unignore.command(name="role", help="Remove a role from the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unignore_role(self, ctx, role: discord.Role):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED_OFF} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if await self.is_anti_nsfw_enabled(guild_id):
            try:
                rules = await ctx.guild.fetch_automod_rules()
                for rule in rules:
                    if rule.name == "Anti NSFW Links":
                        exempt_roles = list(rule.exempt_roles)  
                        exempt_roles = [ch for ch in exempt_roles if ch.id != role.id]
                        await rule.edit(
                            exempt_roles=exempt_roles,
                            reason="Role removed from Anti NSFW Links exemption via automod unignore command"
                        )
                        break
            except discord.HTTPException:
                pass

        
        async with aiosqlite.connect("db/automod.db") as db:
            result = await db.execute("DELETE FROM automod_ignored WHERE guild_id = ? AND type = 'role' AND id = ?", (guild_id, role.id))
            await db.commit()

        if result.rowcount > 0:
            embed = discord.Embed(title=f"{CHECK_EMOJI} Success", description=f"{role.mention} has been removed from the automod ignore list.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title=f"{CROSS_EMOJI} Error", description=f"{role.mention} is not in the automod ignore list.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
    

    @automod.command(name="disable", help="Disable Automod in the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED_OFF} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="Disable Automod Confirmation",
            description="**Are you sure you want to disable Automod?**\n\nThis will remove all custom event settings, punishments, ignored roles/channels, & logging channel data.",
            color=0x4D3164
        )
        embed.set_footer(text="Click 'Yes' to disable Automod or 'No' to cancel.")
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        view = ConfirmDisable(ctx.author)
        message = await ctx.send(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            embed.title = "Automod Disable Cancelled"
            embed.description = "You took too long to respond. Automod disable process has been canceled."
            embed.color = 0x4D3164
            
            await message.edit(embed=embed, view=None)

        elif view.value:
            
            async with aiosqlite.connect("db/automod.db") as db:
                await db.execute("DELETE FROM automod WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_punishments WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_logging WHERE guild_id = ?", (guild_id,))
                await db.commit()

            rules = await ctx.guild.fetch_automod_rules()
            for rule in rules:
                if rule.name == "Anti NSFW Links":
                    try:
                        await rule.delete(reason="Automod disabled - removing Anti NSFW Link rule")
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass


            embed.title = f"{CHECK_EMOJI} Automod Disabled"
            embed.description = f"Automod has been successfully disabled for **{ctx.guild.name}.** \nAll settings, punishments, and logs have been removed.\n\nCurrent Status: {DISABLED} Disabled\n➜ To Re-enable use `{ctx.prefix}automod enable`."
            embed.color = 0x4D3164
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await message.edit(embed=embed, view=None)
            

        else:
            embed.title = "Automod Disable Cancelled"
            embed.description = "Automod disable process has been canceled."
            embed.color = 0x4D3164
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await message.edit(embed=embed, view=None)

        

    @automod.command(name="config", aliases=["settings", "show", "view"], help="View Automod settings.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED_OFF} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        current_punishments = await self.get_current_punishments(guild_id)
        embed = discord.Embed(title=f"Enabled Automod Events & their punishment type for {ctx.guild.name}", color=0x4D3164)
        embed.set_footer(text="Manage punishment type for events by executing “automod punishment” command.", icon_url=self.bot.user.avatar.url)

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        else:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        for event, punishment in current_punishments:
            embed.add_field(name=event, value=punishment or "None", inline=False)

        if await self.is_anti_nsfw_enabled(guild_id):
            embed.add_field(name="Anti NSFW Links", value="Block Message", inline=False)

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT log_channel FROM automod_logging WHERE guild_id = ?", (guild_id,))
            log_channel_id = await cursor.fetchone()

        if log_channel_id and log_channel_id[0]:
            log_channel = ctx.guild.get_channel(log_channel_id[0])
            if log_channel:
                embed.add_field(name="Logging Channel", value=f"{log_channel.mention}", inline=False)
            else:
                embed.add_field(name="Logging Channel", value="Deleted Channel", inline=False)
        else:
            embed.add_field(name="Logging Channel", value="No logging channel", inline=False)

        await ctx.send(embed=embed)


    @automod.command(name="logging", help="Set the logging channel for Automod events.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def logging(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title=f"{DISABLED} Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: {DISABLED_OFF} Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x4D3164)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod_logging (guild_id, log_channel) VALUES (?, ?)", (guild_id, channel.id))
            await db.commit()
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"**{VERIFIED_CHECK} | Automoderation Logging channel set to {channel.mention}.**\n\n➜ Use `{ctx.prefix}automod config` to view current Automod settings.", color=0x4D3164)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        guild_id = guild.id

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("DELETE FROM automod WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_punishments WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_logging WHERE guild_id = ?", (guild_id,))
            await db.commit()
async def setup(bot):
    await bot.add_cog(AutoMod(bot))
