import os
import random
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from aiohttp import web
import aiohttp_cors

# ---------------------------------------------------------
# 環境変数ロード
# ---------------------------------------------------------
load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ---------------------------------------------------------
# Discord Bot セットアップ
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # DM受信に必要

bot = commands.Bot(command_prefix="!", intents=intents)

# 認証待ちユーザー
pending_verifications = {}  
# { user_id: {"code": "1234", "role": role_object} }

# ---------------------------------------------------------
# ロール付与ボタン
# ---------------------------------------------------------
class RoleGiveView(discord.ui.View):
    def __init__(self, roles):
        super().__init__()
        for role in roles:
            self.add_item(RoleGiveButton(role))

class RoleGiveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(label=f"{role.name}", style=discord.ButtonStyle.primary)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await interaction.user.add_roles(self.role)
        await interaction.response.send_message(f"{self.role.name} を付与したよ！", ephemeral=True)

# ---------------------------------------------------------
# ロール剥奪ボタン
# ---------------------------------------------------------
class RoleRemoveView(discord.ui.View):
    def __init__(self, roles):
        super().__init__()
        for role in roles:
            self.add_item(RoleRemoveButton(role))

class RoleRemoveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(label=f"{role.name}", style=discord.ButtonStyle.danger)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await interaction.user.remove_roles(self.role)
        await interaction.response.send_message(f"{self.role.name} を剥奪したよ！", ephemeral=True)

# ---------------------------------------------------------
# 認証ボタン
# ---------------------------------------------------------
class VerifyView(discord.ui.View):
    def __init__(self, role):
        super().__init__()
        self.add_item(VerifyButton(role))

class VerifyButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(label="認証する", style=discord.ButtonStyle.primary)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user

        # ランダム4桁コード生成
        code = str(random.randint(1000, 9999))

        # 保存
        pending_verifications[user.id] = {
            "code": code,
            "role": self.role
        }

        # ephemeral でコードを送る
        await interaction.response.send_message(
            f"あなたの認証コードは **{code}** です。\nこのコードを Bot の DM に送ってください。",
            ephemeral=True
        )

# ---------------------------------------------------------
# Bot Ready
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

# ---------------------------------------------------------
# /sendrole（付与）
# ---------------------------------------------------------
@bot.tree.command(name="sendrole", description="ロール付与ボタンを送信する")
@app_commands.describe(description="説明文", roles="ロール名をスペース区切りで")
async def sendrole(interaction: discord.Interaction, description: str, roles: str):

    # 管理者チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

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


# ---------------------------------------------------------
# /sendderole（剥奪）
# ---------------------------------------------------------
@bot.tree.command(name="sendderole", description="ロール剥奪ボタンを送信する")
@app_commands.describe(description="説明文", roles="ロール名をスペース区切りで")
async def sendderole(interaction: discord.Interaction, description: str, roles: str):

    # 管理者チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

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


# ---------------------------------------------------------
# /sendcer（認証）
# ---------------------------------------------------------
@bot.tree.command(name="sendcer", description="認証ボタンを送信する")
@app_commands.describe(description="説明文", role_name="ロール名")
async def sendcer(interaction: discord.Interaction, description: str, role_name: str):

    # 管理者チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        await interaction.response.send_message("そのロールが見つからないよ。", ephemeral=True)
        return

    embed = discord.Embed(
        title="認証",
        description=description,
        color=discord.Color.blue()
    )
    embed.add_field(name="付与されるロール", value=role.name, inline=False)

    view = VerifyView(role)
    await interaction.response.send_message(embed=embed, view=view)


# ---------------------------------------------------------
# DMで認証コードを受信
# ---------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # DM以外は無視
    if message.guild is not None:
        return

    user_id = message.author.id

    if user_id not in pending_verifications:
        await message.channel.send("認証コードが発行されていないよ。")
        return

    data = pending_verifications[user_id]
    code = data["code"]
    role = data["role"]

    if message.content.strip() == code:
        guild = role.guild
        member = guild.get_member(user_id)
        await member.add_roles(role)

        await message.channel.send(f"認証成功！ロール **{role.name}** を付与したよ！")

        del pending_verifications[user_id]
    else:
        await message.channel.send("コードが違うよ。もう一度送ってね。")

# ---------------------------------------------------------
# Webサーバー（Render用）
# ---------------------------------------------------------
async def handle_ping(request):
    JST = timezone(timedelta(hours=+9), 'JST')
    current_time_jst = datetime.now(JST).strftime("%Y/%m/%d %H:%M:%S %Z")

    print(f"🌐 [Web Ping] {current_time_jst} | Status OK")

    return web.Response(text="Bot is running and ready.")

def setup_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            allow_methods=["GET"],
            allow_headers=("X-Requested-With", "Content-Type"),
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)

    return app

async def start_web_server():
    web_app = setup_web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=PORT)
    print(f"Webサーバー起動: ポート {PORT}")
    await site.start()
    await asyncio.Future()

# ---------------------------------------------------------
# Bot + Webサーバー同時起動
# ---------------------------------------------------------
async def main():
    if not DISCORD_TOKEN:
        print("FATAL ERROR: TOKEN が設定されていません。")
        return

    web_task = asyncio.create_task(start_web_server())
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))

    await asyncio.gather(web_task, bot_task)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot and Web Server stopped.")
