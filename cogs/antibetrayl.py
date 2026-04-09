import discord
from discord.ext import commands
import aiosqlite
from collections import defaultdict, deque
import time
import asyncio
import re

class AntiBetray(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.action_history = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
        self.last_nuker = {}
        self.db_path = 'db/antibetray.db'
        self.lock = asyncio.Lock()
        self.action_map = {
            'channeldelete': 'limit_channel_delete',
            'categorydelete': 'limit_category_delete',
            'channelpermedit': 'limit_channel_perm_edit',
            'categorypermedit': 'limit_category_perm_edit',
            'categorypermsync': 'limit_category_perm_sync',
            'roledelete': 'limit_role_delete',
            'rolepermedit': 'limit_role_perm_edit',
            'rolepositionedit': 'limit_role_position_edit',
            'memberban': 'limit_member_ban',
            'memberkick': 'limit_member_kick',
            'massmention': 'limit_mass_mention',
            'linkspam': 'limit_link_spam',
            'serverupdate': 'limit_server_update',
        }
        self.default_limits = {
            'time_window': 60,
            'owner_dm': 1,
            'limit_channel_delete': 3,
            'limit_category_delete': 2,
            'limit_channel_perm_edit': 10,
            'limit_category_perm_edit': 5,
            'limit_category_perm_sync': 10,
            'limit_role_delete': 3,
            'limit_role_perm_edit': 5,
            'limit_role_position_edit': 5,
            'limit_member_ban': 3,
            'limit_member_kick': 5,
            'limit_mass_mention': 3,
            'limit_link_spam': 5,
            'limit_server_update': 3,
        }

    async def cog_load(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute('''CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            maintenance INTEGER DEFAULT 0,
            owner_dm INTEGER DEFAULT 1,
            time_window INTEGER DEFAULT 60,
            limit_channel_delete INTEGER DEFAULT 3,
            limit_category_delete INTEGER DEFAULT 2,
            limit_channel_perm_edit INTEGER DEFAULT 10,
            limit_category_perm_edit INTEGER DEFAULT 5,
            limit_category_perm_sync INTEGER DEFAULT 10,
            limit_role_delete INTEGER DEFAULT 3,
            limit_role_perm_edit INTEGER DEFAULT 5,
            limit_role_position_edit INTEGER DEFAULT 5,
            limit_member_ban INTEGER DEFAULT 3,
            limit_member_kick INTEGER DEFAULT 5,
            limit_mass_mention INTEGER DEFAULT 3,
            limit_link_spam INTEGER DEFAULT 5,
            limit_server_update INTEGER DEFAULT 3
        )''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS whitelist (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS extra_owners (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )''')
        await self.db.commit()

    async def cog_unload(self):
        await self.db.close()

    async def get_settings(self, guild_id):
        async with self.lock:
            async with self.db.execute('SELECT * FROM settings WHERE guild_id=?', (guild_id,)) as cursor:
                row = await cursor.fetchone()
            if row is None:
                values = (
                    guild_id, 0, 0, self.default_limits['owner_dm'], self.default_limits['time_window'],
                    self.default_limits['limit_channel_delete'], self.default_limits['limit_category_delete'],
                    self.default_limits['limit_channel_perm_edit'], self.default_limits['limit_category_perm_edit'],
                    self.default_limits['limit_category_perm_sync'], self.default_limits['limit_role_delete'],
                    self.default_limits['limit_role_perm_edit'], self.default_limits['limit_role_position_edit'],
                    self.default_limits['limit_member_ban'], self.default_limits['limit_member_kick'],
                    self.default_limits['limit_mass_mention'], self.default_limits['limit_link_spam'],
                    self.default_limits['limit_server_update']
                )
                await self.db.execute('''INSERT INTO settings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
                await self.db.commit()
                columns = [
                    'guild_id', 'enabled', 'maintenance', 'owner_dm', 'time_window',
                    'limit_channel_delete', 'limit_category_delete', 'limit_channel_perm_edit',
                    'limit_category_perm_edit', 'limit_category_perm_sync', 'limit_role_delete',
                    'limit_role_perm_edit', 'limit_role_position_edit', 'limit_member_ban',
                    'limit_member_kick', 'limit_mass_mention', 'limit_link_spam', 'limit_server_update'
                ]
                row = (guild_id, 0, 0, self.default_limits['owner_dm'], self.default_limits['time_window'],
                       self.default_limits['limit_channel_delete'], self.default_limits['limit_category_delete'],
                       self.default_limits['limit_channel_perm_edit'], self.default_limits['limit_category_perm_edit'],
                       self.default_limits['limit_category_perm_sync'], self.default_limits['limit_role_delete'],
                       self.default_limits['limit_role_perm_edit'], self.default_limits['limit_role_position_edit'],
                       self.default_limits['limit_member_ban'], self.default_limits['limit_member_kick'],
                       self.default_limits['limit_mass_mention'], self.default_limits['limit_link_spam'],
                       self.default_limits['limit_server_update'])
                return dict(zip(columns, row))
            columns = [
                'guild_id', 'enabled', 'maintenance', 'owner_dm', 'time_window',
                'limit_channel_delete', 'limit_category_delete', 'limit_channel_perm_edit',
                'limit_category_perm_edit', 'limit_category_perm_sync', 'limit_role_delete',
                'limit_role_perm_edit', 'limit_role_position_edit', 'limit_member_ban',
                'limit_member_kick', 'limit_mass_mention', 'limit_link_spam', 'limit_server_update'
            ]
            return dict(zip(columns, row))

    async def update_setting(self, guild_id, field, value):
        async with self.lock:
            await self.db.execute(f'UPDATE settings SET {field}=? WHERE guild_id=?', (value, guild_id))
            await self.db.commit()

    async def is_whitelisted(self, guild_id, user_id):
        async with self.lock:
            async with self.db.execute('SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?', (guild_id, user_id)) as cursor:
                return await cursor.fetchone() is not None

    async def add_whitelist(self, guild_id, user_id):
        async with self.lock:
            await self.db.execute('INSERT OR IGNORE INTO whitelist (guild_id, user_id) VALUES (?, ?)', (guild_id, user_id))
            await self.db.commit()

    async def remove_whitelist(self, guild_id, user_id):
        async with self.lock:
            await self.db.execute('DELETE FROM whitelist WHERE guild_id=? AND user_id=?', (guild_id, user_id))
            await self.db.commit()

    async def get_whitelist(self, guild_id):
        async with self.lock:
            async with self.db.execute('SELECT user_id FROM whitelist WHERE guild_id=?', (guild_id,)) as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def is_extra_owner(self, guild_id, user_id):
        async with self.lock:
            async with self.db.execute('SELECT 1 FROM extra_owners WHERE guild_id=? AND user_id=?', (guild_id, user_id)) as cursor:
                return await cursor.fetchone() is not None

    async def add_extra_owner(self, guild_id, user_id):
        async with self.lock:
            await self.db.execute('INSERT OR IGNORE INTO extra_owners (guild_id, user_id) VALUES (?, ?)', (guild_id, user_id))
            await self.db.commit()

    async def remove_extra_owner(self, guild_id, user_id):
        async with self.lock:
            await self.db.execute('DELETE FROM extra_owners WHERE guild_id=? AND user_id=?', (guild_id, user_id))
            await self.db.commit()

    async def get_extra_owners(self, guild_id):
        async with self.lock:
            async with self.db.execute('SELECT user_id FROM extra_owners WHERE guild_id=?', (guild_id,)) as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def handle_action(self, guild, user, action_type, details=None):
        if not user:
            return
        guild_id = guild.id
        user_id = user.id
        if user_id == guild.owner_id:
            return
        settings = await self.get_settings(guild_id)
        if not settings['enabled']:
            return
        if not await self.is_whitelisted(guild_id, user_id):
            return
        now = time.monotonic()
        history = self.action_history[guild_id][user_id][action_type]
        while history and now - history[0][0] > settings['time_window']:
            history.popleft()
        history.append((now, details))
        limit_key = f'limit_{action_type}'
        if len(history) > settings[limit_key]:
            try:
                await guild.ban(user, reason=f"AntiBetray: Betrayal detected - exceeded limit for {action_type}")
                self.last_nuker[guild_id] = user_id
                embed = discord.Embed(title="Betrayal Detected", description=f"{user.mention} has been banned for betrayal (exceeded {action_type} limit).", color=discord.Color.red())
                if settings['owner_dm']:
                    owner = guild.owner
                    try:
                        await owner.send(embed=embed)
                    except:
                        pass
            except:
                pass
            await self.restore_actions(guild, user_id, action_type)
            self.action_history[guild_id][user_id][action_type].clear()
            await self.check_maintenance(guild)

    async def restore_actions(self, guild, user_id, action_type):
        history = self.action_history[guild.id][user_id][action_type]
        sorted_hist = sorted(history, key=lambda x: x[0], reverse=True)
        for t, details in sorted_hist:
            if details is None:
                continue
            try:
                if action_type == 'channel_delete':
                    cat = self.bot.get_channel(details.get('category_id')) if details.get('category_id') else None
                    overwrites = details.get('overwrites', {})
                    position = details.get('position', 0)
                    if details['type'] == 'text':
                        await guild.create_text_channel(
                            name=details['name'],
                            topic=details.get('topic'),
                            nsfw=details.get('nsfw', False),
                            slow_mode_delay=details.get('slow_mode_delay', 0),
                            position=position,
                            category=cat,
                            overwrites=overwrites
                        )
                    elif details['type'] == 'voice':
                        await guild.create_voice_channel(
                            name=details['name'],
                            bitrate=details.get('bitrate', 64000),
                            user_limit=details.get('user_limit', 0),
                            position=position,
                            category=cat,
                            overwrites=overwrites
                        )
                elif action_type == 'category_delete':
                    await guild.create_category(
                        name=details['name'],
                        position=details.get('position', 0),
                        overwrites=details.get('overwrites', {})
                    )
                elif action_type in ['channel_perm_edit', 'category_perm_edit', 'category_perm_sync']:
                    channel = guild.get_channel(details['channel_id'])
                    if channel:
                        await channel.edit(overwrites=details['before_overwrites'])
                elif action_type == 'role_delete':
                    new_role = await guild.create_role(
                        name=details['name'],
                        permissions=details['permissions'],
                        color=details['color'],
                        hoist=details['hoist'],
                        mentionable=details['mentionable']
                    )
                    await new_role.edit(position=details['position'])
                elif action_type == 'role_perm_edit':
                    role = guild.get_role(details['role_id'])
                    if role:
                        await role.edit(permissions=details['before_permissions'])
                elif action_type == 'role_position_edit':
                    role = guild.get_role(details['role_id'])
                    if role:
                        await role.edit(position=details['before_position'])
                elif action_type == 'server_update':
                    edit_kwargs = {}
                    if 'name' in details:
                        edit_kwargs['name'] = details['name']
                    if 'verification_level' in details:
                        edit_kwargs['verification_level'] = details['verification_level']
                    if 'system_channel' in details:
                        edit_kwargs['system_channel'] = details['system_channel']
                    if 'afk_channel' in details:
                        edit_kwargs['afk_channel'] = details['afk_channel']
                    if edit_kwargs:
                        await guild.edit(**edit_kwargs)
            except Exception as e:
                pass

    async def check_maintenance(self, guild):
        settings = await self.get_settings(guild.id)
        if settings['maintenance']:
            return
        if len(guild.channels) >= 10:
            return
        await self.update_setting(guild.id, 'maintenance', 1)
        try:
            cat = await guild.create_category('MAINTENANCE')
            ann = await guild.create_text_channel('maintenance-announcements', category=cat)
            await ann.edit(overwrites={guild.default_role: discord.PermissionOverwrite(send_messages=False)})
            chat = await guild.create_text_channel('maintenance-chat', category=cat)
            staff = await guild.create_text_channel('maintenance-staff', category=cat)
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False)}
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            await staff.edit(overwrites=overwrites)
            description = "The server was nuked.\nRestoration in progress."
            nuker_id = self.last_nuker.get(guild.id)
            if nuker_id:
                description += f"\nNuker: <@{nuker_id}>"
            embed = discord.Embed(title="Server Maintenance", description=description, color=discord.Color.orange())
            await ann.send(embed=embed)
            if settings['owner_dm']:
                try:
                    await guild.owner.send(embed=discord.Embed(title="Maintenance Activated", description="Server entered maintenance mode due to nuke.", color=discord.Color.orange()))
                except:
                    pass
        except:
            pass

    @commands.guild_only()
    @commands.command(name='antibetray')
    async def antibetray_status(self, ctx):
        settings = await self.get_settings(ctx.guild.id)
        embed = discord.Embed(title="AntiBetray Status", color=discord.Color.blue())
        embed.add_field(name="Enabled", value="Yes" if settings['enabled'] else "No", inline=True)
        embed.add_field(name="Maintenance", value="Yes" if settings['maintenance'] else "No", inline=True)
        embed.add_field(name="Owner DM", value="On" if settings['owner_dm'] else "Off", inline=True)
        embed.add_field(name="Time Window", value=f"{settings['time_window']} seconds", inline=True)
        for action, column in self.action_map.items():
            embed.add_field(name=action.capitalize(), value=str(settings[column]), inline=True)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_enable')
    async def antibetray_enable(self, ctx):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        settings = await self.get_settings(ctx.guild.id)
        if settings['enabled']:
            embed = discord.Embed(title="AntiBetray", description="Already enabled.", color=discord.Color.green())
        else:
            await self.update_setting(ctx.guild.id, 'enabled', 1)
            embed = discord.Embed(title="AntiBetray", description="Enabled successfully.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_disable')
    async def antibetray_disable(self, ctx):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        settings = await self.get_settings(ctx.guild.id)
        if not settings['enabled']:
            embed = discord.Embed(title="AntiBetray", description="Already disabled.", color=discord.Color.green())
        else:
            await self.update_setting(ctx.guild.id, 'enabled', 0)
            embed = discord.Embed(title="AntiBetray", description="Disabled successfully.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_config')
    async def antibetray_config(self, ctx):
        await self.antibetray_status(ctx)

    @commands.guild_only()
    @commands.command(name='antibetray_config_window')
    async def antibetray_config_window(self, ctx, seconds: int):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if seconds <= 0:
            embed = discord.Embed(title="Error", description="Time window must be positive.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        await self.update_setting(ctx.guild.id, 'time_window', seconds)
        embed = discord.Embed(title="AntiBetray Config", description=f"Time window set to {seconds} seconds.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_config_ownerdm')
    async def antibetray_config_ownerdm(self, ctx, state: str):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        value = 1 if state.lower() == 'on' else 0 if state.lower() == 'off' else None
        if value is None:
            embed = discord.Embed(title="Error", description="State must be 'on' or 'off'.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        await self.update_setting(ctx.guild.id, 'owner_dm', value)
        embed = discord.Embed(title="AntiBetray Config", description=f"Owner DM set to {'on' if value else 'off'}.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_config_limit')
    async def antibetray_config_limit(self, ctx, action: str, number: int):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        action = action.lower()
        if action not in self.action_map:
            embed = discord.Embed(title="Error", description="Invalid action.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if number < 0:
            embed = discord.Embed(title="Error", description="Limit must be non-negative.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        column = self.action_map[action]
        await self.update_setting(ctx.guild.id, column, number)
        embed = discord.Embed(title="AntiBetray Config", description=f"Limit for {action} set to {number}.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_whitelist_add')
    async def antibetray_whitelist_add(self, ctx, user: discord.User):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if await self.is_whitelisted(ctx.guild.id, user.id):
            embed = discord.Embed(title="AntiBetray Whitelist", description=f"{user.mention} is already whitelisted.", color=discord.Color.orange())
        else:
            await self.add_whitelist(ctx.guild.id, user.id)
            embed = discord.Embed(title="AntiBetray Whitelist", description=f"Added {user.mention} to whitelist.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_whitelist_remove')
    async def antibetray_whitelist_remove(self, ctx, user: discord.User):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if not await self.is_whitelisted(ctx.guild.id, user.id):
            embed = discord.Embed(title="AntiBetray Whitelist", description=f"{user.mention} is not whitelisted.", color=discord.Color.orange())
        else:
            await self.remove_whitelist(ctx.guild.id, user.id)
            embed = discord.Embed(title="AntiBetray Whitelist", description=f"Removed {user.mention} from whitelist.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_whitelist_list')
    async def antibetray_whitelist_list(self, ctx):
        if not (ctx.author == ctx.guild.owner or await self.is_extra_owner(ctx.guild.id, ctx.author.id)):
            embed = discord.Embed(title="Error", description="You don't have permission to use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        uids = await self.get_whitelist(ctx.guild.id)
        if not uids:
            description = "No whitelisted users."
        else:
            description = "\n".join(f"- <@{uid}>" for uid in uids)
        embed = discord.Embed(title="AntiBetray Whitelist", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_extraowner_add')
    async def antibetray_extraowner_add(self, ctx, user: discord.User):
        if ctx.author != ctx.guild.owner:
            embed = discord.Embed(title="Error", description="Only the server owner can use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if await self.is_extra_owner(ctx.guild.id, user.id):
            embed = discord.Embed(title="AntiBetray Extra Owner", description=f"{user.mention} is already an extra owner.", color=discord.Color.orange())
        else:
            await self.add_extra_owner(ctx.guild.id, user.id)
            embed = discord.Embed(title="AntiBetray Extra Owner", description=f"Added {user.mention} as extra owner.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_extraowner_remove')
    async def antibetray_extraowner_remove(self, ctx, user: discord.User):
        if ctx.author != ctx.guild.owner:
            embed = discord.Embed(title="Error", description="Only the server owner can use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if not await self.is_extra_owner(ctx.guild.id, user.id):
            embed = discord.Embed(title="AntiBetray Extra Owner", description=f"{user.mention} is not an extra owner.", color=discord.Color.orange())
        else:
            await self.remove_extra_owner(ctx.guild.id, user.id)
            embed = discord.Embed(title="AntiBetray Extra Owner", description=f"Removed {user.mention} from extra owners.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_extraowner_list')
    async def antibetray_extraowner_list(self, ctx):
        if ctx.author != ctx.guild.owner:
            embed = discord.Embed(title="Error", description="Only the server owner can use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        uids = await self.get_extra_owners(ctx.guild.id)
        if not uids:
            description = "No extra owners."
        else:
            description = "\n".join(f"- <@{uid}>" for uid in uids)
        embed = discord.Embed(title="AntiBetray Extra Owners", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='antibetray_recovery_unlock')
    async def antibetray_recovery_unlock(self, ctx):
        if ctx.author != ctx.guild.owner:
            embed = discord.Embed(title="Error", description="Only the server owner can use this command.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        settings = await self.get_settings(ctx.guild.id)
        if not settings['maintenance']:
            embed = discord.Embed(title="Error", description="Maintenance mode is not active.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        cat = next((c for c in ctx.guild.categories if c.name == 'MAINTENANCE'), None)
        if not cat:
            embed = discord.Embed(title="Error", description="Maintenance category not found.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        for channel in cat.channels:
            await channel.delete()
        await cat.delete()
        await self.update_setting(ctx.guild.id, 'maintenance', 0)
        embed = discord.Embed(title="AntiBetray Recovery", description="Maintenance mode disabled and channels deleted.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                user = entry.user
                if user.bot:
                    return
                details = {}
                if isinstance(channel, discord.CategoryChannel):
                    action = 'category_delete'
                    details = {
                        'name': channel.name,
                        'position': channel.position,
                        'overwrites': channel.overwrites
                    }
                elif isinstance(channel, discord.TextChannel):
                    action = 'channel_delete'
                    details = {
                        'type': 'text',
                        'name': channel.name,
                        'position': channel.position,
                        'category_id': channel.category.id if channel.category else None,
                        'overwrites': channel.overwrites,
                        'topic': channel.topic,
                        'nsfw': channel.is_nsfw(),
                        'slow_mode_delay': channel.slow_mode_delay
                    }
                elif isinstance(channel, discord.VoiceChannel):
                    action = 'channel_delete'
                    details = {
                        'type': 'voice',
                        'name': channel.name,
                        'position': channel.position,
                        'category_id': channel.category.id if channel.category else None,
                        'overwrites': channel.overwrites,
                        'bitrate': channel.bitrate,
                        'user_limit': channel.user_limit
                    }
                else:
                    return
                await self.handle_action(guild, user, action, details)
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.overwrites == after.overwrites:
            return
        guild = before.guild
        try:
            async for entry in guild.audit_logs(limit=1, oldest_first=False):
                if entry.target.id == before.id and 'overwrite' in entry.action.name:
                    user = entry.user
                    if user.bot:
                        return
                    details = {'channel_id': before.id, 'before_overwrites': before.overwrites}
                    if isinstance(before, discord.CategoryChannel):
                        action = 'category_perm_edit'
                    else:
                        if before.category and after.overwrites == before.category.overwrites:
                            action = 'category_perm_sync'
                        else:
                            action = 'channel_perm_edit'
                    await self.handle_action(guild, user, action, details)
                    break
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                user = entry.user
                if user.bot:
                    return
                details = {
                    'name': role.name,
                    'permissions': role.permissions,
                    'color': role.color,
                    'hoist': role.hoist,
                    'mentionable': role.mentionable,
                    'position': role.position
                }
                action = 'role_delete'
                await self.handle_action(guild, user, action, details)
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        perm_changed = before.permissions != after.permissions
        pos_changed = before.position != after.position
        if not (perm_changed or pos_changed):
            return
        guild = before.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
                user = entry.user
                if user.bot:
                    return
                if perm_changed:
                    details = {'role_id': before.id, 'before_permissions': before.permissions}
                    await self.handle_action(guild, user, 'role_perm_edit', details)
                if pos_changed:
                    details = {'role_id': before.id, 'before_position': before.position}
                    await self.handle_action(guild, user, 'role_position_edit', details)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                perpetrator = entry.user
                if perpetrator.bot:
                    return
                action = 'member_ban'
                await self.handle_action(guild, perpetrator, action)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    perpetrator = entry.user
                    if perpetrator.bot:
                        return
                    action = 'member_kick'
                    await self.handle_action(member.guild, perpetrator, action)
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        user = message.author
        did_mention = '@everyone' in message.content or '@here' in message.content
        did_link = re.search(r'(https?://[^\s]+|discord\.gg/[^\s]+)', message.content, re.IGNORECASE)
        if did_mention:
            await self.handle_action(guild, user, 'mass_mention')
        if did_link:
            await self.handle_action(guild, user, 'link_spam')

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        changed = {}
        if before.name != after.name:
            changed['name'] = before.name
        if before.verification_level != after.verification_level:
            changed['verification_level'] = before.verification_level
        if before.system_channel != after.system_channel:
            changed['system_channel'] = before.system_channel
        if before.afk_channel != after.afk_channel:
            changed['afk_channel'] = before.afk_channel
        if not changed:
            return
        try:
            async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
                user = entry.user
                if user.bot:
                    return
                action = 'server_update'
                await self.handle_action(after, user, action, changed)
        except:
            pass

async def setup(bot):
    await bot.add_cog(AntiBetray(bot))