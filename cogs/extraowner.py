import discord
from discord.ext import commands
from discord.ui import View, Button
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import TICK, ERROR_X, CROSS_MARK, TIMER, LOADING

class Extraowner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS extraowners (
                guild_id INTEGER PRIMARY KEY,
                owner_id INTEGER
            )
        ''')
        await self.db.commit()

    @commands.command(name='extraowner', aliases=["owner"], help="Adds Extraowner to the server")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def extraowner(self, ctx, option: str = None, user: discord.Member = None):
        guild_id = ctx.guild.id

        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                description=f"{CROSS_MARK} | Your Server Doesn't Meet My 30 Member Criteria",
                color=0x000000
            )
            await ctx.send(embed=embed)
            return

        Olympus = ['1070619070468214824', '677952614390038559']
        if ctx.author.id != ctx.guild.owner_id and str(ctx.author.id) not in Olympus:
            embed = discord.Embed(title=f"{ERROR_X} Access Denied",
                                  description="Only Server Owner Can Run This Command",
                                  color=0x000000
            )
            await ctx.send(embed=embed)
            return

        if option is None:
            pre = ctx.prefix
            embed = discord.Embed(
                title="__**Extra Owner**__",
                description="Extraowners can adjust server antinuke settings & manage whitelist events, so careful consideration is essential before assigning it to someone.",
                color=0x000000
            )
            embed.add_field(name="__**Extraowner Set**__", value=f"To Set Extra Owner, Use - **{pre}extraowner set @user**")
            embed.add_field(name="__**Extraowner Reset**__", value=f"To Reset Extra Owner, Use - **{pre}extraowner reset**")
            embed.add_field(name="__**Extraowner View**__", value=f"To View Extra Owner, Use - **{pre}extraowner view**")
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            await ctx.reply(embed=embed)
            return

        
        if option.lower() == 'set':
            if user is None or user.bot:
                embed = discord.Embed(title=f"{ERROR_X} Error",
                    description="Please Provide a Valid User Mention or ID to Set as Extra Owner!",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
                return

            
            view = ConfirmView(ctx)
            embed = discord.Embed(
                title="Confirm Action",
                description=f"**Are you sure you want to set {user.mention} as the Extra Owner?**",
                color=0x000000
            )
            message = await ctx.reply(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                await message.edit(content=f"{TIMER} Confirmation timed out.", embed=None, view=None)
            elif view.value:
                await self.db.execute('INSERT OR REPLACE INTO extraowners (guild_id, owner_id) VALUES (?, ?)', (guild_id, user.id))
                await self.db.commit()
                embed = discord.Embed(title=f"{TICK} Success",
                    description=f"Added {user.mention} As Extraowner",
                    color=0x000000
                )
                await message.edit(embed=embed, view=None)
            else:
                await message.edit(content=f"{CROSS_MARK} Action cancelled.", embed=None, view=None)

        
        elif option.lower() == 'reset':
            async with self.db.execute('SELECT owner_id FROM extraowners WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                embed = discord.Embed(title=f"{ERROR_X} Error",
                    description="No extra owner has been designated for this guild.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                
                view = ConfirmView(ctx)
                embed = discord.Embed(
                    title="Confirm Action",
                    description="**Are you sure you want to reset the Extra Owner?**",
                    color=0x000000
                )
                message = await ctx.reply(embed=embed, view=view)
                await view.wait()

                if view.value is None:
                    await message.edit(content=f"{TIMER} Confirmation timed out.", embed=None, view=None)
                elif view.value:
                    await self.db.execute('DELETE FROM extraowners WHERE guild_id = ?', (guild_id,))
                    await self.db.commit()
                    embed = discord.Embed(title=f"{TICK} Success",
                        description="Disabled Extraowner Configuration!",
                        color=0x000000
                    )
                    await message.edit(embed=embed, view=None)
                else:
                    await message.edit(content=f"{CROSS_MARK} Action canceled.", embed=None, view=None)

        elif option.lower() == 'view':
            async with self.db.execute('SELECT owner_id FROM extraowners WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                embed = discord.Embed(title=f"{ERROR_X} Error",
                    description="No extra owner is currently assigned.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                embed = discord.Embed(
                    description=f"Current Extraowner is <@{row[0]}>",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

class ConfirmView(View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()

async def setup(bot):
    await bot.add_cog(Extraowner(bot))