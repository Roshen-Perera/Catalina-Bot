import discord
from discord.ext import commands
import os
import logging
import asyncio
from dotenv import load_dotenv
from helper_cog import help_cog
from music_cog import music_cog

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot
bot = commands.Bot(command_prefix="/", intents=intents)

# Remove the default help command
bot.remove_command("help")

async def setup():
    # Load Cogs
    await bot.add_cog(help_cog(bot))
    await bot.add_cog(music_cog(bot))

@bot.event
async def on_ready():
    logging.info(f'✅ Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_command_error(ctx, error):
    if ctx.command:  # Only log if the command exists
        logging.error(f'Error in command {ctx.command}: {error}')
    else:
        logging.error(f'Unknown command error: {error}')

# Main function to run the bot
async def main():
    await setup()
    token = os.getenv("TOKEN")
    if token is None:
        logging.error("❌ Token is not set. Please check your .env file.")
        return
    await bot.start(token)

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())
