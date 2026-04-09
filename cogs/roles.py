import discord
from discord.ext import commands
from discord import ui
import aiosqlite
import os
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import CHECK, CROSS, INFO

DB_PATH = "db/roles.db"

class RoleSelect(ui.Select):
    def __init__(self, roles_data):
        options = [
            discord.SelectOption(label=role.name, value=str(role.id), description=f"Get the {role.name} role")
            for role in roles_data
        ]
        super().__init__(placeholder="Select your roles...", min_values=0, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        selected_ids = [int(val) for val in self.values]
        all_option_ids = [int(opt.value) for opt in self.options]
        
        to_add = []
        to_remove = []
        
        for role_id in all_option_ids:
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
                
            if role_id in selected_ids:
                if role not in interaction.user.roles:
                    to_add.append(role)
            else:
                if role in interaction.user.roles:
                    to_remove.append(role)
        
        if to_add:
            await interaction.user.add_roles(*to_add, reason="Self-roles selection")
        if to_remove:
            await interaction.user.remove_roles(*to_remove, reason="Self-roles selection")
            
        msg = []
        if to_add:
            msg.append(f"{CHECK} Added: " + ", ".join([r.mention for r in to_add]))
        if to_remove:
            msg.append(f"{CROSS} Removed: " + ", ".join([r.mention for r in to_remove]))
        
        if not msg:
            await interaction.followup.send("No changes were made to your roles.", ephemeral=True)
        else:
            await interaction.followup.send("\n".join(msg), ephemeral=True)

class RoleView(ui.LayoutView):
    def __init__(self, roles_data):
        super().__init__(timeout=None)
        
        container = ui.Container(accent_color=0x4D3164)
        container.add_item(ui.TextDisplay("### Select Roles\nChoose your roles from the menu below!"))
        container.add_item(ui.Separator())
        
        select_row = ui.ActionRow()
        select_row.add_item(RoleSelect(roles_data))
        container.add_item(select_row)
        
        self.add_item(container)

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs("db", exist_ok=True)
        self.bot.loop.create_task(self._init_db())

    async def _init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS role_menus (guild_id INTEGER, message_id INTEGER, roles TEXT, PRIMARY KEY (guild_id, message_id))")
            await db.commit()

    @commands.group(name="roles", help="Setup dropdown-based self-roles.", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def roles(self, ctx):
        await ctx.send_help(ctx.command)

    @roles.command(name="selection", help="Create a self-role menu with a list of roles.")
    @commands.has_permissions(administrator=True)
    async def selection_menu(self, ctx, *, roles_list: str):
        """Usage: +roles selection @Valorant @Minecraft @CSGO"""
        # Parse roles from mentions or IDs
        role_mentions = ctx.message.role_mentions
        if not role_mentions:
            return await ctx.send(f"{CROSS} Please mention the roles you want to include in the menu.")
            
        if len(role_mentions) > 25:
            return await ctx.send(f"{CROSS} You can only have up to 25 roles in a single menu.")

        view = RoleView(role_mentions)
        message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        
        # Save to DB for persistence after bot restart
        roles_ids = ",".join([str(r.id) for r in role_mentions])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO role_menus (guild_id, message_id, roles) VALUES (?, ?, ?)", 
                             (ctx.guild.id, message.id, roles_ids))
            await db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        # Restore views for all active role menus
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT guild_id, message_id, roles FROM role_menus") as cursor:
                async for guild_id, message_id, roles_str in cursor:
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                        
                    role_ids = [int(rid) for rid in roles_str.split(",")]
                    roles_data = []
                    for rid in role_ids:
                        role = guild.get_role(rid)
                        if role:
                            roles_data.append(role)
                    
                    if roles_data:
                        self.bot.add_view(RoleView(roles_data), message_id=message_id)

async def setup(bot):
    await bot.add_cog(Roles(bot))
