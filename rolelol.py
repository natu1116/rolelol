import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# ボタンビュー（付与 / 剥奪）
# -------------------------
class RoleGiveView(discord.ui.View):
    def __init__(self, roles):
        super().__init__()
        for role in roles:
            self.add_item(RoleGiveButton(role))

class RoleGiveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(label=f"{role.name}", style=discord.ButtonStyle.primary, custom_id=f"give_{role.id}")
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await interaction.user.add_roles(self.role)
        await interaction.response.send_message(f"{self.role.name} を付与したよ！", ephemeral=True)

class RoleRemoveView(discord.ui.View):
    def __init__(self, roles):
        super().__init__()
        for role in roles:
            self.add_item(RoleRemoveButton(role))

class RoleRemoveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(label=f"{role.name}", style=discord.ButtonStyle.danger, custom_id=f"remove_{role.id}")
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await interaction.user.remove_roles(self.role)
        await interaction.response.send_message(f"{self.role.name} を剥奪したよ！", ephemeral=True)

# -------------------------
# Bot Ready
# -------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(e)

# -------------------------
# /sendrole（付与）
# -------------------------
@bot.tree.command(name="sendrole", description="ロール付与ボタンを送信する")
@app_commands.describe(description="説明文", roles="ロール名をスペース区切りで")
async def sendrole(interaction: discord.Interaction, description: str, roles: str):
    role_names = roles.split()
    guild_roles = []

    for name in role_names:
        role = discord.utils.get(interaction.guild.roles, name=name)
        if role:
            guild_roles.append(role)

    embed = discord.Embed(
        title="ロール付与",
        description=description,
        color=discord.Color.green()
    )

    for role in guild_roles:
        embed.add_field(name=role.name, value=f"ID: `{role.id}`", inline=False)

    view = RoleGiveView(guild_roles)
    await interaction.response.send_message(embed=embed, view=view)

# -------------------------
# /sendderole（剥奪）
# -------------------------
@bot.tree.command(name="sendderole", description="ロール剥奪ボタンを送信する")
@app_commands.describe(description="説明文", roles="ロール名をスペース区切りで")
async def sendderole(interaction: discord.Interaction, description: str, roles: str):
    role_names = roles.split()
    guild_roles = []

    for name in role_names:
        role = discord.utils.get(interaction.guild.roles, name=name)
        if role:
            guild_roles.append(role)

    embed = discord.Embed(
        title="ロール剥奪",
        description=description,
        color=discord.Color.red()
    )

    for role in guild_roles:
        embed.add_field(name=role.name, value=f"ID: `{role.id}`", inline=False)

    view = RoleRemoveView(guild_roles)
    await interaction.response.send_message(embed=embed, view=view)

# -------------------------
# Run
# -------------------------
bot.run(TOKEN)
