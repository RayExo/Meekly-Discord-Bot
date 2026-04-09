import discord
from discord.ext import commands
import os
import traceback
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import DEVELOPER_IDS

# 🔧 Custom Emojis
from emojis import (
    CHECK as EMOJI_CHECK,
    CROSS as EMOJI_CROSS
)


def is_dev():
    async def predicate(ctx):
        if ctx.author.id in DEVELOPER_IDS:
            return True
        await ctx.send(f"{EMOJI_CROSS} You are not a developer.")
        return False
    return commands.check(predicate)


class DevTools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ======================
    # 🔄 Reload Command
    # ======================
    @commands.command(name="reload", aliases=["r"])
    @is_dev()
    async def reload_command(self, ctx, target: str = None):
        """Reload a cog/extension by file path or extension name.
        Usage: !reload cogs.help or !reload cogs/help or !reload cogs/help.py or !reload all
        """
        if not target:
            return await ctx.send(
                f"{EMOJI_CROSS} **Usage:** `reload <cog_path>` or `reload all`\n"
                f"Examples: `reload cogs.help`, `reload cogs/help`, `reload events/dev.py`, `reload all`"
            )

        # Handle "reload all" command
        if target.lower() == "all":
            reloaded = []
            failed = []
            
            # Define directories
            dirs = [
                ("cogs", "cogs"),
                ("events", "events"),
                ("automod", "automod"),
                ("antinuke", "antinuke"),
            ]
            
            for dir_name, module_prefix in dirs:
                if not os.path.exists(dir_name):
                    continue
                    
                for file in os.listdir(dir_name):
                    if file.endswith(".py") and not file.startswith("_"):
                        extension_name = f"{module_prefix}.{file[:-3]}"
                        try:
                            await self.bot.reload_extension(extension_name)
                            reloaded.append(extension_name)
                        except Exception as e:
                            failed.append((extension_name, str(e)))
            
            embed = discord.Embed(color=discord.Color.blue(), title="🔄 Reload All Results")
            if reloaded:
                embed.add_field(name=f"Reloaded ({len(reloaded)})", value="\n".join(reloaded), inline=False)
            if failed:
                failed_text = "\n".join([f"`{name}` - {err}" for name, err in failed])
                embed.add_field(name=f"Failed ({len(failed)})", value=failed_text, inline=False)
            
            return await ctx.send(embed=embed)

        # Convert path formats to module name
        # Replace backslash with forward slash for consistency
        target = target.replace("\\", "/")
        
        # Remove .py extension if present
        if target.endswith(".py"):
            target = target[:-3]
        
        # Convert forward slashes to dots
        extension_name = target.replace("/", ".")
        
        try:
            await self.bot.reload_extension(extension_name)
            await ctx.send(f"{EMOJI_CHECK} Successfully reloaded `{extension_name}`")
        except commands.ExtensionNotFound:
            await ctx.send(f"{EMOJI_CROSS} Extension `{extension_name}` not found.\nMake sure the path is correct (e.g., `cogs.help`)")
        except commands.ExtensionNotLoaded:
            # Try to load if not already loaded
            try:
                await self.bot.load_extension(extension_name)
                await ctx.send(f"{EMOJI_CHECK} Extension `{extension_name}` was not loaded. Successfully loaded it now.")
            except Exception as e:
                await ctx.send(f"{EMOJI_CROSS} Failed to load `{extension_name}`: {str(e)}")
        except commands.ExtensionFailed as e:
            error_text = "".join(traceback.format_exception_only(type(e.original), e.original))
            await ctx.send(f"{EMOJI_CROSS} Failed to reload `{extension_name}`:\n```{error_text}```")
        except Exception as e:
            error_text = "".join(traceback.format_exception_only(type(e), e))
            await ctx.send(f"{EMOJI_CROSS} Failed to reload `{extension_name}`:\n```{error_text}```")



async def setup(bot: commands.Bot):
    await bot.add_cog(DevTools(bot))
