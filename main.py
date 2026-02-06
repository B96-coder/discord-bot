import os
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not set in environment variables!")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🔗 Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game(name="/ping"))

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")

@bot.tree.command(name="hello", description="Say hello!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"👋 Hello, {interaction.user.mention}!")

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
   .run(main())
