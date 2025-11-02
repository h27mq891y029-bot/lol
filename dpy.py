import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask("")
@app.route("/")
def home():
    return "Bot alive"

def run():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run).start()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GIPHY_API = os.getenv("GIPHY_API")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    allowed_contexts=discord.app_commands.AppCommandContext(
        guild=True,
        dm_channel=True,
        private_channel=True
    ),
    allowed_installs=discord.app_commands.AppInstallationType(
        guild=True,
        user=True
    ),
)

GIPHY_UPLOAD_URL = "https://upload.giphy.com/v1/gifs"

async def upload_to_giphy(file: discord.Attachment):
    video_bytes = await file.read()
    filename = file.filename
    data = aiohttp.FormData()
    data.add_field("file", video_bytes, filename=filename, content_type="video/mp4")
    data.add_field("api_key", GIPHY_API)

    async with aiohttp.ClientSession() as session:
        async with session.post(GIPHY_UPLOAD_URL, data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                return f"Upload failed for {filename}: {text}"
            json_resp = await resp.json()
            gif_id = json_resp.get("data", {}).get("id")
            if not gif_id:
                return f"Failed to get GIF URL for {filename}"
            return f"https://media.giphy.com/media/{gif_id}/giphy.gif"

@app_commands.command(name="videotogif", description="Convert video(s) to GIF")
@app_commands.describe(
    file1="Video file 1",
    file2="Video file 2 (optional)",
    file3="Video file 3 (optional)"
)
async def videotogif(interaction: discord.Interaction, file1: discord.Attachment, file2: discord.Attachment=None, file3: discord.Attachment=None):
    await interaction.response.send_message(f"Processing {len([f for f in (file1, file2, file3) if f])} video(s)...", ephemeral=True)
    files = [f for f in (file1, file2, file3) if f]
    results = await asyncio.gather(*[upload_to_giphy(f) for f in files])
    for res in results:
        await interaction.followup.send(res)

bot.tree.add_command(videotogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Commands synced")

bot.run(DISCORD_TOKEN)
