import discord
from discord.ext import commands, tasks
import aiosqlite
import os
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import CHECK, CROSS, LOCK, UNLOCK, GHOST, UNGHOST, CROWN

DB_PATH = "db/voicemaster.db"

# Make sure db folder exists
os.makedirs("db", exist_ok=True)

async def init_db():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS voicemaster (
                    guild_id INTEGER PRIMARY KEY,
                    category_id INTEGER,
                    interface_id INTEGER,
                    joinvc_id INTEGER,
                    panel_msg_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS vc_owners (
                    channel_id INTEGER PRIMARY KEY,
                    owner_id INTEGER
                )
            """)
            await db.commit()
    except Exception:
        raise  # Re-raise the exception to ensure the bot doesn't start with a broken database

from discord import ui

class RenameModal(ui.Modal, title="Rename Your Voice Channel"):
    name_input = ui.TextInput(label="Channel Name", placeholder="Enter new name...", min_length=1, max_length=15)
    
    def __init__(self, vc):
        super().__init__()
        self.vc = vc

    async def on_submit(self, interaction: discord.Interaction):
        await self.vc.edit(name=self.name_input.value)
        await interaction.response.send_message(f"{CHECK} Channel renamed to **{self.name_input.value}**.", ephemeral=True)

class LimitModal(ui.Modal, title="Set User Limit"):
    limit_input = ui.TextInput(label="Limit (0-99)", placeholder="0 = No limit", min_length=1, max_length=2)
    
    def __init__(self, vc):
        super().__init__()
        self.vc = vc

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.limit_input.value)
            if 0 <= val <= 99:
                await self.vc.edit(user_limit=val)
                await interaction.response.send_message(f"{CHECK} User limit set to **{val}**.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{CROSS} Please enter a number between 0 and 99.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"{CROSS} Invalid number.", ephemeral=True)

class VoiceMasterView(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        container = ui.Container(accent_color=0x4D3164)
        # Using a fallback if bot.user is not yet available during persistent view registration
        avatar_url = (self.bot.user.avatar.url if self.bot.user and self.bot.user.avatar 
                     else "https://cdn.discordapp.com/embed/avatars/0.png")
        
        section = ui.Section(
            ui.TextDisplay("## VoiceMaster Interface"),
            ui.TextDisplay("Click the buttons below to manage your personal voice channel."),
            accessory=ui.Thumbnail(media=discord.UnfurledMediaItem(url=avatar_url))
        )
        container.add_item(section)
        container.add_item(ui.Separator())
        
        container.add_item(ui.TextDisplay(
            f"Use the buttons below to manage your channel:\n\n"
            f"{LOCK} / {UNLOCK} — **Lock or Unlock** your channel\n"
            f"{GHOST} / {UNGHOST} — **Hide or Reveal** your channel\n"
            f"📝 — **Rename** your channel\n"
            f"👥 — Set a **User Limit**\n"
            f"{CROWN} — **Claim** ownership if owner left"
        ))
        container.add_item(ui.Separator())
        
        # Row 1: Privacy Controls
        row1 = ui.ActionRow()
        lock_btn = ui.Button(emoji=LOCK, style=discord.ButtonStyle.gray, custom_id="vm_lock")
        unlock_btn = ui.Button(emoji=UNLOCK, style=discord.ButtonStyle.gray, custom_id="vm_unlock")
        hide_btn = ui.Button(emoji=GHOST, style=discord.ButtonStyle.gray, custom_id="vm_hide")
        unhide_btn = ui.Button(emoji=UNGHOST, style=discord.ButtonStyle.gray, custom_id="vm_unhide")
        
        lock_btn.callback = self.lock_callback
        unlock_btn.callback = self.unlock_callback
        hide_btn.callback = self.hide_callback
        unhide_btn.callback = self.unhide_callback
        
        row1.add_item(lock_btn)
        row1.add_item(unlock_btn)
        row1.add_item(hide_btn)
        row1.add_item(unhide_btn)
        container.add_item(row1)
        
        # Row 2: Management
        row2 = ui.ActionRow()
        rename_btn = ui.Button(emoji="📝", style=discord.ButtonStyle.gray, custom_id="vm_rename")
        limit_btn = ui.Button(emoji="👥", style=discord.ButtonStyle.gray, custom_id="vm_limit")
        claim_btn = ui.Button(emoji=CROWN, style=discord.ButtonStyle.gray, custom_id="vm_claim")
        
        rename_btn.callback = self.rename_callback
        limit_btn.callback = self.limit_callback
        claim_btn.callback = self.claim_callback
        
        row2.add_item(rename_btn)
        row2.add_item(limit_btn)
        row2.add_item(claim_btn)
        container.add_item(row2)

        self.add_item(container)

    async def interaction_checks(self, interaction: discord.Interaction):
        member = interaction.user
        if not member.voice or not member.voice.channel:
            await interaction.response.send_message(f"{CROSS} You must be in a voice channel.", ephemeral=True)
            return None

        vc = member.voice.channel
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT owner_id FROM vc_owners WHERE channel_id=?", (vc.id,)) as cursor:
                row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(f"{CROSS} This is not a managed VoiceMaster channel.", ephemeral=True)
            return None

        return vc

    async def is_owner(self, interaction: discord.Interaction, vc):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT owner_id FROM vc_owners WHERE channel_id=?", (vc.id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] == interaction.user.id:
                    return True
        return False

    # --- Callbacks ---
    async def lock_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message(f"{LOCK} Channel locked.", ephemeral=True)

    async def unlock_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message(f"{UNLOCK} Channel unlocked.", ephemeral=True)

    async def hide_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message(f"{GHOST} Channel hidden.", ephemeral=True)

    async def unhide_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message(f"{UNGHOST} Channel visible.", ephemeral=True)

    async def rename_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await interaction.response.send_modal(RenameModal(vc))

    async def limit_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        if not await self.is_owner(interaction, vc):
            return await interaction.response.send_message(f"{CROSS} You don't own this channel.", ephemeral=True)
        await interaction.response.send_modal(LimitModal(vc))

    async def claim_callback(self, interaction: discord.Interaction):
        vc = await self.interaction_checks(interaction)
        if not vc: return
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT owner_id FROM vc_owners WHERE channel_id=?", (vc.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    owner_id = row[0]
                    owner = interaction.guild.get_member(owner_id)
                    if owner and owner in vc.members:
                        return await interaction.response.send_message(f"{CROSS} The owner is still in the channel.", ephemeral=True)
                    await db.execute("UPDATE vc_owners SET owner_id=? WHERE channel_id=?", (interaction.user.id, vc.id))
                    await db.commit()
                    await interaction.response.send_message(f"{CROWN} You are now the owner of this voice channel!", ephemeral=True)

  #  @discord.ui.button(emoji="<:delete:1409553551994261504>", style=discord.ButtonStyle.danger, custom_id="vm_delete")
  #  async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
      #  vc, member = await self.interaction_checks(interaction)
      #  if vc:
          #  await interaction.response.send_message(
             #   "Are you sure you want to delete this voice channel? Reply with 'yes' within 10 seconds.",
            #    ephemeral=True
       #     )
         #   def check(m):
             #   return m.author == member and m.channel == interaction.channel and m.content.lower() == "yes"
         #   try:
            #    await self.bot.wait_for("message", check=check, timeout=10.0, delete_after=5)
              #  await vc.delete()
             #   async with aiosqlite.connect(DB_PATH) as db:
                 #   await db.execute("DELETE FROM vc_owners WHERE channel_id=?", (vc.id,))
                   # await db.commit()
              #  await interaction.followup.send("<:delete:1409553551994261504> Channel deleted.", ephemeral=True)
          #  except asyncio.TimeoutError:
              #  await interaction.followup.send("<:cross:1408031235057385564> Deletion cancelled.", ephemeral=True)
          #  except discord.errors.Forbidden:
              #  await interaction.followup.send("<:cross:1408031235057385564> Bot lacks permission to delete the channel.", ephemeral=True)

class VoiceMaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(VoiceMasterView(bot))
        self.cleanup_task.start()

    @commands.group(name="voicemaster", aliases=["vm"], invoke_without_command=True)
    async def voicemaster(self, ctx):
        await ctx.send("Use `vm setup` or `vm remove`.")

    @voicemaster.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        guild = ctx.guild
        bot_member = guild.me
        required_perms = discord.Permissions(manage_channels=True, move_members=True, manage_permissions=True)
        if not bot_member.guild_permissions >= required_perms:
            return await ctx.send(f"{CROSS} Bot lacks required permissions: Manage Channels, Move Members, Manage Permissions.")

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT category_id FROM voicemaster WHERE guild_id=?", (guild.id,)) as cursor:
                if await cursor.fetchone():
                    return await ctx.send(f"{CROSS} VoiceMaster already setup.")
        
        try:
            category = await guild.create_category("Meekly | VoiceMaster")
            joinvc = await category.create_voice_channel("Join 2 Create")
            interface = await category.create_text_channel(
                "interface",
                overwrites={guild.default_role: discord.PermissionOverwrite(send_messages=False)}
            )
            
            view = VoiceMasterView(self.bot)
            msg = await interface.send(view=view)
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT OR REPLACE INTO voicemaster VALUES (?,?,?,?,?)",
                                (guild.id, category.id, interface.id, joinvc.id, msg.id))
                await db.commit()
            await ctx.send(f"{CHECK} VoiceMaster setup complete.")
        except discord.errors.Forbidden:
            await ctx.send(f"{CROSS} Bot lacks permission to create channels or send messages.")
        except Exception:
            await ctx.send(f"{CROSS} An error occurred during setup.")

    @voicemaster.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx):
        guild = ctx.guild
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT category_id, interface_id, joinvc_id FROM voicemaster WHERE guild_id=?", (guild.id,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return await ctx.send(f"{CROSS} VoiceMaster not setup.")
            category_id, interface_id, joinvc_id = row

        try:
            for cid in [category_id, interface_id, joinvc_id]:
                ch = guild.get_channel(cid)
                if ch:
                    await ch.delete()
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM voicemaster WHERE guild_id=?", (guild.id,))
                await db.commit()
            await ctx.send(f"{CHECK} VoiceMaster removed.")
        except discord.errors.Forbidden:
            await ctx.send(f"{CROSS} Bot lacks permission to delete channels.")
        except Exception:
            await ctx.send(f"{CROSS} An error occurred during removal.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return

        if after.channel:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT joinvc_id, category_id FROM voicemaster WHERE guild_id=?", (member.guild.id,)) as cursor:
                    row = await cursor.fetchone()

            if row and after.channel.id == row[0]:
                joinvc_id, category_id = row
                category = member.guild.get_channel(category_id)
                if not category:
                    return

                try:
                    new_vc = await category.create_voice_channel(f"{member.name}'s VC")
                    await member.move_to(new_vc)
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("INSERT OR REPLACE INTO vc_owners VALUES (?,?)", (new_vc.id, member.id))
                        await db.commit()
                except discord.errors.Forbidden:
                    return
                except Exception:
                    return

        if before.channel:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT owner_id FROM vc_owners WHERE channel_id=?", (before.channel.id,)) as cursor:
                    row = await cursor.fetchone()
                if row and len(before.channel.members) == 0:
                    try:
                        await before.channel.delete()
                        await db.execute("DELETE FROM vc_owners WHERE channel_id=?", (before.channel.id,))
                        await db.commit()
                    except discord.errors.Forbidden:
                        pass
                    except Exception:
                        pass

    @tasks.loop(hours=1.0)
    async def cleanup_task(self):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT channel_id FROM vc_owners") as cursor:
                rows = await cursor.fetchall()
            for row in rows:
                channel_id = row[0]
                channel = self.bot.get_channel(channel_id)
                if not channel or len(channel.members) == 0:
                    try:
                        if channel:
                            await channel.delete()
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute("DELETE FROM vc_owners WHERE channel_id=?", (channel_id,))
                            await db.commit()
                    except Exception:
                        pass

    def cog_unload(self):
        self.cleanup_task.stop()

async def setup(bot):
    try:
        await init_db()  # Initialize the database before adding the cog
        await bot.add_cog(VoiceMaster(bot))
    except Exception:
        raise