import os
import json
import random
import asyncio
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands

# ===== CONFIGURATION =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not set in environment variables!")

# Economy settings
STARTING_BALANCE = 1000
DAILY_MIN = 100
DAILY_MAX = 500
WORK_MIN = 50
WORK_MAX = 200
ROB_SUCCESS_RATE = 0.7  # 70% chance to succeed
ROB_LOSS_RATE = 0.5     # Lose 50% of attempt if failed
SLOTS_PAYOUTS = {
    "🎉🎉🎉": 10,
    "💎💎💎": 8,
    "💰💰💰": 6,
    "🍎🍎🍎": 4,
    "🍒🍒🍒": 3,
    "🍒🍒": 2,
    "🍒": 1.5
}

# File paths
USERS_FILE = "users.json"
BANK_FILE = "bank.json"

# ===== DATA MANAGEMENT =====
def load_json(filename, default):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        save_json(filename, default)
        return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize data files
users = load_json(USERS_FILE, {})
bank = load_json(BANK_FILE, {"total_wealth": 0, "transactions": []})

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            "cash": STARTING_BALANCE,
            "bank": 0,
            "last_daily": None,
            "last_work": None,
            "inventory": {}
        }
        save_json(USERS_FILE, users)
    return users[user_id]

def save_user(user_id, data):
    users[str(user_id)] = data
    save_json(USERS_FILE, users)

def add_transaction(description, amount):
    bank["transactions"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "description": description,
        "amount": amount
    })
    bank["total_wealth"] += amount
    save_json(BANK_FILE, bank)

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== ECONOMY COMMANDS =====
@bot.tree.command(name="balance", description="Check your bank balance")
async def balance(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    total = user["cash"] + user["bank"]
    
    embed = discord.Embed(
        title=f"🏦 {interaction.user.name}'s Bank Statement",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="💰 Cash", value=f"`${user['cash']:,}`", inline=True)
    embed.add_field(name="🏦 Bank", value=f"`${user['bank']:,}`", inline=True)
    embed.add_field(name="💎 Total", value=f"`${total:,}`", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    now = datetime.utcnow()
    
    if user["last_daily"]:
        last_daily = datetime.fromisoformat(user["last_daily"])
        if (now - last_daily) < timedelta(days=1):
            next_claim = last_daily + timedelta(days=1)
            wait_time = next_claim - now
            hours = int(wait_time.total_seconds() // 3600)
            minutes = int((wait_time.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"⏳ You already claimed your daily reward! Come back in {hours}h {minutes}m",
                ephemeral=True
            )
            return
    
    amount = random.randint(DAILY_MIN, DAILY_MAX)
    user["cash"] += amount
    user["last_daily"] = now.isoformat()
    save_user(interaction.user.id, user)
    add_transaction(f"Daily reward for {interaction.user.name}", amount)
    
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received `${amount:,}`!",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 New Cash Balance", value=f"`${user['cash']:,}`")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2945/2945333.png")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Work to earn money")
async def work(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    now = datetime.utcnow()
    
    if user["last_work"]:
        last_work = datetime.fromisoformat(user["last_work"])
        if (now - last_work) < timedelta(hours=2):
            next_work = last_work + timedelta(hours=2)
            wait_time = next_work - now
            minutes = int(wait_time.total_seconds() // 60)
            await interaction.response.send_message(
                f"⏳ You're tired from work! Rest for {minutes} more minutes",
                ephemeral=True
            )
            return
    
    jobs = [
        "Software Developer", "Chef", "Teacher", "Artist", "Streamer",
        "Doctor", "Engineer", "Barista", "Gamer", "Musician"
    ]
    job = random.choice(jobs)
    amount = random.randint(WORK_MIN, WORK_MAX)
    user["cash"] += amount
    user["last_work"] = now.isoformat()
    save_user(interaction.user.id, user)
    add_transaction(f"{job} work by {interaction.user.name}", amount)
    
    embed = discord.Embed(
        title=f"💼 You worked as a {job}!",
        description=f"You earned `${amount:,}` for your hard work!",
        color=discord.Color.blue()
    )
    embed.add_field(name="💰 New Cash Balance", value=f"`${user['cash']:,}`")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3159/3159647.png")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="Deposit cash into your bank account")
@app_commands.describe(amount="Amount to deposit (use 'all' for everything)")
async def deposit(interaction: discord.Interaction, amount: str):
    user = get_user(interaction.user.id)
    
    if amount.lower() == "all":
        amount = user["cash"]
    else:
        try:
            amount = int(amount)
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount! Use a number or 'all'", ephemeral=True)
            return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    if amount > user["cash"]:
        await interaction.response.send_message(f"❌ You only have `${user['cash']:,}` in cash!", ephemeral=True)
        return
    
    user["cash"] -= amount
    user["bank"] += amount
    save_user(interaction.user.id, user)
    add_transaction(f"Deposit by {interaction.user.name}", amount)
    
    embed = discord.Embed(
        title="🏦 Deposit Successful",
        description=f"Deposited `${amount:,}` into your bank account",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Cash", value=f"`${user['cash']:,}`", inline=True)
    embed.add_field(name="🏦 Bank", value=f"`${user['bank']:,}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="Withdraw cash from your bank account")
@app_commands.describe(amount="Amount to withdraw (use 'all' for everything)")
async def withdraw(interaction: discord.Interaction, amount: str):
    user = get_user(interaction.user.id)
    
    if amount.lower() == "all":
        amount = user["bank"]
    else:
        try:
            amount = int(amount)
        except ValueError:
            await interaction.response.send_message("❌ Invalid amount! Use a number or 'all'", ephemeral=True)
            return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    if amount > user["bank"]:
        await interaction.response.send_message(f"❌ You only have `${user['bank']:,}` in your bank!", ephemeral=True)
        return
    
    user["bank"] -= amount
    user["cash"] += amount
    save_user(interaction.user.id, user)
    add_transaction(f"Withdrawal by {interaction.user.name}", -amount)
    
    embed = discord.Embed(
        title="🏧 Withdrawal Successful",
        description=f"Withdrew `${amount:,}` from your bank account",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Cash", value=f"`${user['cash']:,}`", inline=True)
    embed.add_field(name="🏦 Bank", value=f"`${user['bank']:,}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Send money to another user")
@app_commands.describe(user="User to pay", amount="Amount to send")
async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't pay yourself!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    
    sender = get_user(interaction.user.id)
    if amount > sender["cash"]:
        await interaction.response.send_message(f"❌ You only have `${sender['cash']:,}` in cash!", ephemeral=True)
        return
    
    receiver = get_user(user.id)
    sender["cash"] -= amount
    receiver["cash"] += amount
    save_user(interaction.user.id, sender)
    save_user(user.id, receiver)
    add_transaction(f"Payment from {interaction.user.name} to {user.name}", 0)  # Net zero for economy
    
    embed = discord.Embed(
        title="💸 Payment Sent!",
        description=f"Sent `${amount:,}` to {user.mention}",
        color=discord.Color.purple()
    )
    embed.add_field(name="💰 Your New Balance", value=f"`${sender['cash']:,}`")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rob", description="Rob another user (risky!)")
@app_commands.describe(user="User to rob")
async def rob(interaction: discord.Interaction, user: discord.User):
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't rob yourself!", ephemeral=True)
        return
    
    target = get_user(user.id)
    robber = get_user(interaction.user.id)
    
    if target["cash"] < 100:
        await interaction.response.send_message(f"❌ {user.mention} doesn't have enough cash to rob!", ephemeral=True)
        return
    
    if robber["cash"] < 100:
        await interaction.response.send_message("❌ You need at least $100 to attempt a robbery!", ephemeral=True)
        return
    
    # 70% success chance
    if random.random() < ROB_SUCCESS_RATE:
        # Steal 10-30% of target's cash
        amount = random.randint(int(target["cash"] * 0.1), int(target["cash"] * 0.3))
        amount = min(amount, 5000)  # Max steal $5,000
        
        target["cash"] -= amount
        robber["cash"] += amount
        save_user(user.id, target)
        save_user(interaction.user.id, robber)
        
        embed = discord.Embed(
            title="🚨 Robbery Successful!",
            description=f"You stole `${amount:,}` from {user.mention}!",
            color=discord.Color.red()
        )
        embed.add_field(name="💰 Your New Balance", value=f"`${robber['cash']:,}`")
        await interaction.response.send_message(embed=embed)
    else:
        # Failed robbery - lose 50% of attempt amount
        loss = int(robber["cash"] * ROB_LOSS_RATE)
        loss = min(loss, 1000)  # Max loss $1,000
        
        robber["cash"] -= loss
        save_user(interaction.user.id, robber)
        
        embed = discord.Embed(
            title="👮 Robbery Failed!",
            description=f"You were caught trying to rob {user.mention}!\nYou lost `${loss:,}` in fines!",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="💰 Your New Balance", value=f"`${robber['cash']:,}`")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="View the richest players")
async def leaderboard(interaction: discord.Interaction):
    # Sort users by total wealth
    sorted_users = sorted(
        [(uid, u) for uid, u in users.items() if u["cash"] + u["bank"] > 0],
        key=lambda x: x[1]["cash"] + x[1]["bank"],
        reverse=True
    )[:10]
    
    embed = discord.Embed(
        title="🏆 Top 10 Richest Players",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    
    for i, (uid, user_data) in enumerate(sorted_users, 1):
        total = user_data["cash"] + user_data["bank"]
        try:
            member = await interaction.guild.fetch_member(int(uid))
            name = member.name
        except:
            name = f"User {uid[:5]}..."
        
        embed.add_field(
            name=f"{i}. {name}",
            value=f"`${total:,}` (💰${user_data['cash']:,} 🏦${user_data['bank']:,})",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ===== GAMES =====
@bot.tree.command(name="coinflip", description="Flip a coin to double your money")
@app_commands.describe(choice="Heads or tails", amount="Amount to bet")
async def coinflip(interaction: discord.Interaction, choice: str, amount: int):
    choice = choice.lower()
    if choice not in ["heads", "tails", "h", "t"]:
        await interaction.response.send_message("❌ Choose 'heads' or 'tails'!", ephemeral=True)
        return
    
    choice = "heads" if choice in ["heads", "h"] else "tails"
    user = get_user(interaction.user.id)
    
    if amount <= 0:
        await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
        return
    if amount > user["cash"]:
        await interaction.response.send_message(f"❌ You only have `${user['cash']:,}`!", ephemeral=True)
        return
    
    result = random.choice(["heads", "tails"])
    win = (result == choice)
    
    if win:
        user["cash"] += amount
        color = discord.Color.green()
        title = "✅ You Won!"
        description = f"The coin landed on **{result}**! You won `${amount:,}`!"
    else:
        user["cash"] -= amount
        color = discord.Color.red()
        title = "❌ You Lost!"
        description = f"The coin landed on **{result}**! You lost `${amount:,}`!"
    
    save_user(interaction.user.id, user)
    add_transaction(f"Coinflip by {interaction.user.name}", amount if win else -amount)
    
    embed = discord.Embed(title=title, description=description, color=color)
    embed.add_field(name="💰 New Balance", value=f"`${user['cash']:,}`")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3144/3144457.png")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="slots", description="Play the slot machine")
@app_commands.describe(amount="Amount to bet")
async def slots(interaction: discord.Interaction, amount: int):
    user = get_user(interaction.user.id)
    
    if amount <= 0:
        await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
        return
    if amount > user["cash"]:
        await interaction.response.send_message(f"❌ You only have `${user['cash']:,}`!", ephemeral=True)
        return
    
    # Generate slots
    emojis = ["🍒", "🍎", "💎", "💰", "🎉"]
    slot1 = random.choice(emojis)
    slot2 = random.choice(emojis)
    slot3 = random.choice(emojis)
    result = f"{slot1} | {slot2} | {slot3}"
    
    # Determine win
    win_amount = 0
    if slot1 == slot2 == slot3:
        if slot1 == "🎉":
            win_amount = amount * 10
        elif slot1 == "💎":
            win_amount = amount * 8
        elif slot1 == "💰":
            win_amount = amount * 6
        elif slot1 == "🍎":
            win_amount = amount * 4
        elif slot1 == "🍒":
            win_amount = amount * 3
    elif slot1 == slot2 == "🍒" or slot2 == slot3 == "🍒" or slot1 == slot3 == "🍒":
        win_amount = amount * 2
    elif slot1 == "🍒" or slot2 == "🍒" or slot3 == "🍒":
        win_amount = int(amount * 1.5)
    
    if win_amount > 0:
        user["cash"] += win_amount - amount  # Net gain
        color = discord.Color.green()
        title = "🎰 JACKPOT!"
        description = f"You won `${win_amount:,}`!"
    else:
        user["cash"] -= amount
        color = discord.Color.red()
        title = "🎰 Better Luck Next Time"
        description = f"You lost `${amount:,}`"
    
    save_user(interaction.user.id, user)
    add_transaction(f"Slots by {interaction.user.name}", win_amount - amount if win_amount > 0 else -amount)
    
    embed = discord.Embed(title=title, description=description, color=color)
    embed.add_field(name="Result", value=result, inline=False)
    embed.add_field(name="💰 New Balance", value=f"`${user['cash']:,}`")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2798/2798020.png")
    await interaction.response.send_message(embed=embed)

# ===== ADMIN COMMANDS =====
@bot.tree.command(name="give", description="ADMIN: Give money to a user")
@app_commands.describe(user="User to give money to", amount="Amount to give", location="cash or bank")
@app_commands.choices(location=[
    app_commands.Choice(name="cash", value="cash"),
    app_commands.Choice(name="bank", value="bank")
])
async def give(interaction: discord.Interaction, user: discord.User, amount: int, location: str = "cash"):
    # Only allow server owners or users with Manage Server permission
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    
    target = get_user(user.id)
    if location == "cash":
        target["cash"] += amount
    else:
        target["bank"] += amount
    
    save_user(user.id, target)
    add_transaction(f"Admin gift to {user.name} by {interaction.user.name}", amount)
    
    await interaction.response.send_message(
        f"✅ Gave `${amount:,}` to {user.mention} ({location})",
        ephemeral=True
    )

@bot.tree.command(name="take", description="ADMIN: Take money from a user")
@app_commands.describe(user="User to take money from", amount="Amount to take", location="cash or bank")
@app_commands.choices(location=[
    app_commands.Choice(name="cash", value="cash"),
    app_commands.Choice(name="bank", value="bank"),
    app_commands.Choice(name="all", value="all")
])
async def take(interaction: discord.Interaction, user: discord.User, amount: int, location: str = "cash"):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command!", ephemeral=True)
        return
    
    target = get_user(user.id)
    
    if location == "all":
        total = target["cash"] + target["bank"]
        target["cash"] = 0
        target["bank"] = 0
        amount_taken = total
    else:
        if location == "cash":
            amount_taken = min(amount, target["cash"])
            target["cash"] -= amount_taken
        else:
            amount_taken = min(amount, target["bank"])
            target["bank"] -= amount_taken
    
    save_user(user.id, target)
    add_transaction(f"Admin take from {user.name} by {interaction.user.name}", -amount_taken)
    
    await interaction.response.send_message(
        f"✅ Took `${amount_taken:,}` from {user.mention} ({location})",
        ephemeral=True
    )

# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🔗 Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game(name="/balance | Central Bank"))
    
    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ===== START BOT =====
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
