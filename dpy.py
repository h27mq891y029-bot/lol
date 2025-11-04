import os
import threading
import aiohttp
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "Bot is alive!"
threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True).start()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TENOR_API_KEY = os.getenv("TENOR_API_KEY")
if not DISCORD_TOKEN or not TENOR_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or TENOR_API_KEY in .env")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TENOR_SHARE_URL = "https://api.tenor.com/v2/share"

async def convert_video_url_to_gif(video_url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                TENOR_SHARE_URL,
                params={"key": TENOR_API_KEY, "media_url": video_url.strip()},
                timeout=30
            ) as response:
                if response.status != 200:
                    return f"Error {response.status}"
                data = await response.json()
                result = data.get("results", [{}])[0]
                if not result:
                    return "No GIF returned"
                return f"https://tenor.com/view/{result['id']}\n(direct: {result['media_formats']['gif']['url']})"
    except:
        return "Conversion failed"

@app_commands.command(name="urltogif", description="Convert up to 3 video URLs to Tenor GIFs")
@app_commands.describe(
    url1="First video URL",
    url2="Second video URL (optional)",
    url3="Third video URL (optional)"
)
async def urltogif(
    interaction: discord.Interaction,
    url1: str,
    url2: str | None = None,
    url3: str | None = None
):
    urls = [u for u in (url1, url2, url3) if u and u.strip()]
    if not urls:
        await interaction.response.send_message("Provide at least one URL.", ephemeral=True)
        return
    await interaction.response.send_message(f"Processing {len(urls)} video(s)...", ephemeral=True)
    results = await asyncio.gather(*(convert_video_url_to_gif(u) for u in urls))
    for result in results:
        await interaction.followup.send(result)

bot.tree.add_command(urltogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Command synced")

bot.run(DISCORD_TOKEN)
