from discord import app_commands
from discord.ext import commands
import discord
import requests
import os
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask("")

@app.route("/")
def home():
    return "Hi uptimerobot"

def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GIPHY_API = os.getenv("GIPHY_API")

GIPHY_UPLOAD_URL = "https://upload.giphy.com/v1/gifs"



intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=".", intents=intents,
    allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
    allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=True),
    )

@bot.event
async def on_ready():
    print(f"[+] Logged in as {bot.user}")
    await bot.tree.sync()
    print("Commands synced.")

@app_commands.command(name="videotogif", description="Video2Gif conversion")
@app_commands.describe(file="MP4 video file to convert")
async def videotogif(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.send_message("Processing and Uploading.", ephemeral=True)

    try:
        video_bytes = await file.read()

        response = requests.post(
            GIPHY_UPLOAD_URL,
            data={"api_key": GIPHY_API},
            files={"file": (file.filename, video_bytes, "video/mp4")}
        )
        response.raise_for_status()

        gif_id = response.json().get("data", {}).get("id")
        if not gif_id:
            await interaction.followup.send("Failed to create GIF.", ephemeral=True)
            return

        gif_url = f"https://media.giphy.com/media/{gif_id}/giphy.gif"
        await interaction.followup.send(f"{gif_url}")

    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


bot.tree.add_command(videotogif)
bot.run(TOKEN)
