import os
import json
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
# JSON 読み書き
# -------------------------
def load_ids():
    if not os.path.exists("roleids.json"):
        with open("roleids.json", "w") as f:
            json.dump({"ids": []}, f)
    with open("roleids.json", "r") as f:
        return json.load(f)

def save_ids(data):
    with open("roleids.json", "w") as f:
        json.dump(data, f, indent=4)

# -------------------------
# ボタンビュー（付与 / 剥奪）
# -------------------------
class RoleGiveView(discord.ui.View):
    def __init__(self, role_ids):
        super().__init__()
        for rid in role_ids:
            self.add_item(RoleGiveButton(rid))

class RoleGiveButton(discord.ui.Button):
    def __init__(self, role_id):
        super().__init__(label=f"付与: {role_id}", style=discord.ButtonStyle.primary, custom_id=f"give_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.role_id))
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"{role.name} を付与したよ！", ephemeral=True)

class RoleRemoveView(discord.ui.View):
    def __init__(self, role_ids):
        super().__init__()
        for rid in role_ids:
            self.add_item(RoleRemoveButton(rid))

class RoleRemoveButton(discord.ui.Button):
    def __init__(self, role_id):
        super().__init__(label=f"剥奪: {role_id}", style=discord.ButtonStyle.danger, custom_id=f"remove_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.role_id))
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"{role.name} を剥奪したよ！", ephemeral=True)

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
# /roleid add / remove
# -------------------------
@bot.tree.command(name="roleid", description="ロールIDを管理する")
@app_commands.describe(mode="add or remove", role_id="ロールID")
async def roleid(interaction: discord.Interaction, mode: str, role_id: str):
    data = load_ids()

    if mode == "add":
        if role_id not in data["ids"]:
            data["ids"].append(role_id)
            save_ids(data)
            await interaction.response.send_message(f"ロールID {role_id} を追加したよ！")
        else:
            await interaction.response.send_message("そのIDはすでに登録されてるよ。")

    elif mode == "remove":
        if role_id in data["ids"]:
            data["ids"].remove(role_id)
            save_ids(data)
            await interaction.response.send_message(f"ロールID {role_id} を削除したよ！")
        else:
            await interaction.response.send_message("そのIDは登録されてないよ。")

# -------------------------
# /sendrole（付与）
# -------------------------
@bot.tree.command(name="sendrole", description="ロール付与ボタンを送信する")
@app_commands.describe(description="説明文", ids="ロールIDをスペース区切りで")
async def sendrole(interaction: discord.Interaction, description: str, ids: str):
    role_ids = ids.split()

    embed = discord.Embed(
        title="ロール付与",
        description=description,
        color=discord.Color.green()
    )

    for rid in role_ids:
        role = interaction.guild.get_role(int(rid))
        embed.add_field(name=role.name, value=f"ID: `{rid}`", inline=False)

    view = RoleGiveView(role_ids)
    await interaction.response.send_message(embed=embed, view=view)

# -------------------------
# /sendderole（剥奪）
# -------------------------
@bot.tree.command(name="sendderole", description="ロール剥奪ボタンを送信する")
@app_commands.describe(description="説明文", ids="ロールIDをスペース区切りで")
async def sendderole(interaction: discord.Interaction, description: str, ids: str):
    role_ids = ids.split()

    embed = discord.Embed(
        title="ロール剥奪",
        description=description,
        color=discord.Color.red()
    )

    for rid in role_ids:
        role = interaction.guild.get_role(int(rid))
        embed.add_field(name=role.name, value=f"ID: `{rid}`", inline=False)

    view = RoleRemoveView(role_ids)
    await interaction.response.send_message(embed=embed, view=view)

# -------------------------
# Run
# -------------------------
bot.run(TOKEN)
