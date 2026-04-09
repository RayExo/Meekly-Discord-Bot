import discord
from discord.ext import commands
import time
import aiosqlite
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail, ActionRow, Button

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/utility.db"

    async def get_db_latency(self):
        """Measure real database latency by performing a simple query."""
        start = time.perf_counter()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
        except Exception:
            return None
        end = time.perf_counter()
        return round((end - start) * 1000, 2)

    def get_status_info(self, ping):
        """Get status text and emoji based on latency."""
        if ping < 150:
            return "Excellent", "🟢"
        elif ping < 350:
            return "Good", "🟡"
        elif ping < 600:
            return "Average", "🟠"
        else:
            return "Poor", "🔴"

    def get_speed_category(self, ping):
        """Determine speed category based on overall ping."""
        if ping <= 50:
            return "Light"
        elif ping <= 100:
            return "Speed"
        elif ping <= 200:
            return "Human"
        elif ping <= 400:
            return "Car"
        elif ping <= 700:
            return "Horse"
        else:
            return "Donkey"

    @commands.command(name="ping", help="Checks the bot's latency and system status.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def ping_command(self, ctx):
        await self.send_ping_ui(ctx)

    async def send_ping_ui(self, target, interaction=None):
        try:
            start_proc = time.perf_counter()
            
            # 1. WebSocket Latency
            ws_latency = round(self.bot.latency * 1000, 2)

            # 2. Database Latency (Real)
            db_latency = await self.get_db_latency()

            # 3. Processing Latency
            proc_latency = round((time.perf_counter() - start_proc) * 1000, 2)

            # Overall Average for Status
            latencies = [ws_latency, proc_latency]
            if db_latency:
                latencies.append(db_latency)
            overall = round(sum(latencies) / len(latencies), 2)

            status_text, status_emoji = self.get_status_info(overall)
            speed_cat = self.get_speed_category(overall)

            # UI Construction
            container = Container()
            
            # Header Section
            container.add_item(TextDisplay(f"#  **Meekly Latency**\n-# Heartbeat monitoring and system latency"))
            
            container.add_item(Separator(spacing=discord.SeparatorSpacing.large))

            # Metrics Section
            db_display = f"`{db_latency}ms`" if db_latency else "*N/A*"
            metrics_text = (
                f"### **Performance Metrics**\n"
                f"> **Gateway**: `{ws_latency}ms`\n"
                f"> **Database**: {db_display}\n"
                f"> **Internal**: `{proc_latency}ms`\n\n"
                f"**Overall Latency**: `{overall}ms`\n"
                f"**Current Status**: `{status_text}`"
            )
            container.add_item(TextDisplay(metrics_text))
            
            container.add_item(Separator())
            
            # Footer Section
            req_by = target.author if isinstance(target, commands.Context) else target.user
            container.add_item(TextDisplay(f"-# Requested by {req_by.display_name}"))

            # Refresh Button Logic
            refresh_btn = Button(label="Refresh", style=discord.ButtonStyle.gray)
            
            async def refresh_callback(inter: discord.Interaction):
                try:
                    if inter.user.id != req_by.id:
                        return await inter.response.send_message("You cannot refresh someone else's ping results.", ephemeral=True)
                    await self.send_ping_ui(inter, interaction=inter)
                except Exception as e:
                    print(f"Error in ping refresh callback: {e}")
                
            refresh_btn.callback = refresh_callback
            container.add_item(ActionRow(refresh_btn))

            view = LayoutView(timeout=60)
            view.add_item(container)
            
            if interaction:
                await interaction.response.edit_message(view=view)
            else:
                await target.send(view=view)
        except Exception as e:
            print(f"Error executing ping command: {e}")

async def setup(bot):
    await bot.add_cog(PingCog(bot))