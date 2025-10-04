import discord
from discord import app_commands
from discord.ext import commands

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Define your help message once
        self.help_message = """
🎵 Music Bot Commands:
/help - Displays this message
/mplay <keywords or URL> - Plays a song from YouTube
/mpause - Pauses the current song
/mresume - Resumes the song
/mskip - Skips the current song
/mqueue - Shows the queue
/mclear - Clears the queue
/mleave - Disconnects from VC
"""

    # Slash command
    @app_commands.command(name="help", description="Displays the help message")
    async def slash_help(self, interaction: discord.Interaction):
        await interaction.response.send_message(self.help_message)

    # Prefix command
    @commands.command(name="help", help="Displays the help message")
    async def prefix_help(self, ctx):
        await ctx.send(self.help_message)
