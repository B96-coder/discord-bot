import os
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not set!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.tree.command(name="ping", description="Test command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
