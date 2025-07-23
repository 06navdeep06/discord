# =========================================
from dotenv import load_dotenv
load_dotenv()

voice_activity_weekly = {}  # {guild_id: {user_id: [day0, ..., day6]}}
chat_activity_weekly = {}  # {guild_id: {user_id: [day0, ..., day6]}}

chat_message_timestamps = {}  # {guild_id: {user_id: [timestamps]}}

# Discord Bot: Multi-Feature Server Manager
# -----------------------------------------
# This bot manages voice channels, moderation,
# AI chat, fun commands, and more for Discord servers.
# It uses MongoDB for data persistence and supports
# per-guild (server) settings.
# =========================================

from dotenv import load_dotenv

# --- Imports ---
import discord  # Discord API wrapper
import datetime
from discord.ext import commands  # For command-based bots
import asyncio  # For asynchronous programming (needed for Discord bots)
import os  # For environment variables (API keys, tokens)
import logging  # For logging errors and info
from datetime import timedelta  # For time calculations
import random  # For random choices (e.g., GIFs, responses)
import re  # For regular expressions (pattern matching)
from collections import defaultdict, deque  # For advanced data structures
import time  # For timestamps and timing
import requests  # For making HTTP requests (e.g., Wikipedia API)
from urllib.parse import quote  # For URL encoding
import json  # For working with JSON data (e.g., Google AI API)
try:
    from pymongo import MongoClient  # For MongoDB database connection
except ImportError:
    MongoClient = None
    print("Warning: pymongo not installed. Database features will be disabled.")
from typing import Optional  # For type hints
import aiohttp  # For asynchronous HTTP requests
import datetime as dt  # For date and time operations
import math  # For math operations
import platform  # For system info
import psutil  # For system resource usage
import traceback  # For error tracebacks
from io import BytesIO  # For in-memory file operations
import pytz  # For timezone support
try:
    from countryinfo import CountryInfo  # For mapping country to timezone
except ImportError:
    CountryInfo = None
    print("Warning: countryinfo not installed. Country to timezone features will be disabled.")
import yt_dlp  # For downloading/streaming YouTube audio
try:
    import spotipy  # For Spotify API
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    spotipy = None
    SpotifyClientCredentials = None
from datetime import timezone  # For UTC timezone
from dotenv import load_dotenv
load_dotenv()

# --- Spotify client initialization ---
# If Spotify credentials are set, initialize the Spotify API client
if spotipy and SpotifyClientCredentials:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    ))
else:
    sp = None

pending_matches = {}  # {guild_id: {message_id: author_id}}
# --- Per-Guild (Server) Settings Helper Functions ---
def get_guild_settings(guild_id):
    """Fetch settings for a specific Discord server (guild) from the database."""
    if db is None:
        return {}
    settings = db.guild_settings.find_one({"guild_id": guild_id})
    return settings or {}

def set_guild_setting(guild_id, key, value):
    """Set a specific setting for a Discord server (guild) in the database."""
    if db is None:
        return
    db.guild_settings.update_one(
        {"guild_id": guild_id},
        {"$set": {key: value}},
        upsert=True
    )

def get_guild_timezone(guild_id):
    """Get the timezone for a guild, defaulting to UTC if not set."""
    settings = get_guild_settings(guild_id)
    return settings.get("timezone", "UTC")  # Default to UTC

def localize_time(dt, guild_id):
    """Convert a datetime object to the guild's local timezone."""
    tzname = get_guild_timezone(guild_id)
    tz = pytz.timezone(tzname)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.astimezone(tz)

def update_weekly_chat_activity(guild_id, user_id):
    if guild_id not in chat_activity_weekly:
        chat_activity_weekly[guild_id] = {}
    if user_id not in chat_activity_weekly[guild_id]:
        chat_activity_weekly[guild_id][user_id] = [0] * 7
    idx = datetime.datetime.utcnow().weekday()
    chat_activity_weekly[guild_id][user_id][idx] += 1

# --- Conversation Start Time Tracking ---
# Used for tracking how long a conversation has been going in a server
conversation_start_times = {}

def get_conversation_start(guild_id):
    """Get the start time of the current conversation for a guild."""
    if guild_id not in conversation_start_times:
        conversation_start_times[guild_id] = discord.utils.utcnow().replace(tzinfo=pytz.utc)
    return conversation_start_times[guild_id]

def get_conversation_duration(guild_id):
    """Get the duration of the current conversation for a guild."""
    start = get_conversation_start(guild_id)
    now = discord.utils.utcnow().replace(tzinfo=pytz.utc)
    return now - start

# --- Welcome GIFs ---
WELCOME_GIFS = [
    "https://media.tenor.com/2roX3uxz_68AAAAC/welcome.gif",
    "https://media.giphy.com/media/OkJat1YNdoD3W/giphy.gif",
    "https://media.giphy.com/media/hvRJCLFzcasrR4ia7z/giphy.gif",
    "https://media.giphy.com/media/ASd0Ukj0y3qMM/giphy.gif",
    "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
    "https://media.giphy.com/media/3o6Zt481isNVuQI1l6/giphy.gif",
    "https://media.giphy.com/media/xUPGcguWZHRC2HyBRS/giphy.gif",
    "https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif"
]

# --- Response Post-processing ---
def postprocess_response(text, recent_endings: Optional[list] = None):
    """
    Clean up AI-generated responses:
    - Remove repetitive endings or questions.
    - Avoid always ending with a question.
    """
    if not text:
        return text
    repetitive_endings = [
        "What's on your mind?",
        "Anything else?",
        "Is there something you want to talk about?",
        "Do you need something?",
        "Can I help you with something?",
        "How can I help you?",
        "Let me know if you need anything.",
        "What do you want?",
        "What are you thinking?",
        "What brings you here?",
        "What do you need?",
        "What do you want to do?",
        "What do you want to ask?",
        "What do you want to say?",
        "What do you want from me?",
        "What do you want now?",
        "What do you want next?",
        "What do you want to know?",
        "What do you want to hear?",
        "What do you want to see?",
        "What do you want to tell me?",
        "What do you want to share?",
        "What do you want to discuss?",
        "What do you want to talk about?",
        "What do you want to try?",
        "What do you want to experience?",
        "What do you want to explore?",
        "What do you want to learn?",
        "What do you want to find out?",
        "What do you want to discover?",
        "What do you want to achieve?",
        "What do you want to accomplish?",
        "What do you want to create?",
        "What do you want to build?",
        "What do you want to make?",
        "What do you want to improve?",
        "What do you want to fix?",
        "What do you want to change?",
        "What do you want to add?",
        "What do you want to remove?",
        "What do you want to update?",
        "What do you want to upgrade?",
        "What do you want to replace?",
    ]
    # Remove trailing whitespace and punctuation
    text = text.rstrip()
    # Remove if ends with a question or repetitive phrase
    for ending in repetitive_endings:
        if text.endswith(ending):
            text = text[: -len(ending)].rstrip(" ,.-")
            break
    # Remove if ends with a question mark and is short
    if text.endswith("?") and len(text.split()) < 15:
        text = text.rstrip(" ?!.,-")
    # Optionally, avoid repeating recent endings
    if recent_endings:
        for ending in recent_endings:
            if text.endswith(ending):
                text = text[: -len(ending)].rstrip(" ,.-")
                break
    return text

# --- Channel History Helper ---
async def get_recent_channel_history(channel: discord.TextChannel, bot_user: discord.User, current_message: discord.Message, limit: int = 20) -> list:
    """
    Fetch the last N messages from a channel (excluding commands and bot messages),
    for use as context in AI responses.
    """
    history = []
    try:
        async for msg in channel.history(limit=limit, oldest_first=True):
            if msg.id == current_message.id:
                continue  # skip current message
            if msg.content.startswith("!"):
                continue  # skip commands
            content = msg.content.strip()
            if not content:
                continue  # skip empty/whitespace
            if len(content) > 300:
                content = content[:297] + "..."  # truncate long messages
            author = "bot" if msg.author == bot_user else msg.author.display_name
            history.append((author, content))
    except Exception as e:
        logger.error(f"Error fetching channel history: {e}")
    # Add the current message as the last entry
    content = current_message.content.strip()
    if content:
        if len(content) > 300:
            content = content[:297] + "..."
        history.append((current_message.author.display_name, content))
    return history

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Discord Bot Intents ---
# Intents control which events the bot receives from Discord
from discord.ext import tasks
import datetime

intents = discord.Intents.default()
intents.voice_states = True  # Needed for voice channel events
intents.guilds = True  # Needed for server events
intents.members = True  # Needed for member join/leave events
intents.message_content = True  # Needed to read message content

# --- Bot Initialization ---
bot = commands.Bot(command_prefix="!", intents=intents)  # '!' is the command prefix

TEMPLATE_CHANNELS = {
    "Duo": {
        "id": 1391638961356668979,
        "limit": 2
    },
    "Trio": {
        "id": 1391639028356481025,
        "limit": 3
    },
    "Squad": {
        "id": 1391639129313509438,
        "limit": 4
    },
    "Team": {
        "id": 1391639106970320906,
        "limit": 12
    },
}

# Welcome channel ID
WELCOME_CHANNEL_ID = 1391641782487617696

# AFK channel ID
AFK_CHANNEL_ID = 1364156990561194075

# AFK detection settings
AFK_TIMEOUT = 300  # 5 minutes in seconds
user_voice_activity = {}  # Track when users last spoke/had activity

created_channels = {}
channel_stats = {"total_created": 0, "user_activity": {}}

# Gaming Features
voice_activity_today = {}  # {guild_id: {user_id: ...}}
voice_activity_alltime = {}  # {guild_id: {user_id: {"name": str, "total_time": float}}}
channel_themes = {
    "🎮": {
        "name": "Gaming",
        "color": 0xff6b35
    },
    "📚": {
        "name": "Study",
        "color": 0x4287f5
    },
    "😎": {
        "name": "Chill",
        "color": 0x9c27b0
    },
    "🎵": {
        "name": "Music",
        "color": 0xe91e63
    },
    "💼": {
        "name": "Work",
        "color": 0x607d8b
    }
}

# Auto-role thresholds
ROLE_THRESHOLDS = {
    "Channel Creator": 5,  # 5 channels created
    "Voice Master": 15,  # 15 channels created
    "Community Leader": 30  # 30 channels created
}

# @everyone tag tracking
everyone_warnings = {}

# Vulgar GIFs and Images for Miku responses
MIKU_GIFS = [
    "https://media.tenor.com/x8v1oNUOmg4AAAAC/the-rock-sus.gif",
    "https://media.tenor.com/doIgKO-Q2RgAAAAC/angry-mad.gif",
    "https://media.tenor.com/kc8PQ_2VrdQAAAAC/mad-angry.gif",
    "https://media.tenor.com/VDGFc7gOHlMAAAAC/shut-up-anime.gif",
    "https://media.tenor.com/2UZA_7FE1IEAAAAC/annoyed-whatever.gif",
    "https://media.tenor.com/HJpNRqZL8UMAAAAC/middle-finger-rude.gif",
    "https://media.tenor.com/GWEjOYBEGL8AAAAC/anime-angry.gif",
    "https://media.tenor.com/y2JXkY1pXkwAAAAC/cat-computer.gif",
    "https://media.tenor.com/jI8hdF_bHWsAAAAC/spongebob-mocking.gif",
    "https://media.tenor.com/ZBn7wLwmJbQAAAAC/anime-girl-angry.gif",
    "https://media.tenor.com/8rFQTeVU8TAAAAAC/angry-anime.gif",
    "https://media.tenor.com/oDdkl8nJhwQAAAAC/eye-roll-here-we-go.gif",
    "https://media.tenor.com/6bUqS8K-INAAAAAC/whatever-shrug.gif",
    "https://media.tenor.com/9C3B4UHHwUwAAAAC/dismissive-unimpressed.gif",
    "https://media.tenor.com/fY3cO8V8CjQAAAAC/anime-angry-face.gif",
    "https://media.tenor.com/aHpwWJNSCWcAAAAC/no-nope.gif",
    "https://media.tenor.com/4XKGc6HNOHwAAAAC/go-away-get-out.gif",
    "https://media.tenor.com/4VcJ5WmjHBYAAAAC/annoyed-frustrated.gif",
    "https://media.tenor.com/rXgQJj3h0wkAAAAC/rude-gesture.gif",
    "https://media.tenor.com/IlK7lOorvYMAAAAC/middle-finger.gif",
    "https://c.tenor.com/x8v1oNUOmg4AAAAC/the-rock-sus.gif",
    "https://c.tenor.com/doIgKO-Q2RgAAAAC/angry-mad.gif",
    "https://c.tenor.com/kc8PQ_2VrdQAAAAC/mad-angry.gif",
    "https://c.tenor.com/VDGFc7gOHlMAAAAC/shut-up-anime.gif",
    "https://c.tenor.com/2UZA_7FE1IEAAAAC/annoyed-whatever.gif",
    "https://c.tenor.com/HJpNRqZL8UMAAAAC/middle-finger-rude.gif",
    "https://c.tenor.com/GWEjOYBEGL8AAAAC/anime-angry.gif",
    "https://c.tenor.com/y2JXkY1pXkwAAAAC/cat-computer.gif",
    "https://c.tenor.com/jI8hdF_bHWsAAAAC/spongebob-mocking.gif",
    "https://c.tenor.com/ZBn7wLwmJbQAAAAC/anime-girl-angry.gif"
]

# Vulgar GIFs and Images for HREI <3 responses
HREI_GIFS = [
    "https://tenor.com/en-GB/view/dahliabunni-anime-heart-love-gif-22681191",
    "https://tenor.com/en-GB/view/kagami-furi-heart-eyes-hearts-anime-cat-girl-gif-11488933993313748973",
    "https://media.tenor.com/1oPZZDpHdu8AAAAi/chainsaw-man-makima.gif",
    "https://c.tenor.com/O5XHNIahspwAAAAd/tenor.gif"
]

# Mention spam protection
MENTION_SPAM_THRESHOLD = 3  # mentions
MENTION_SPAM_WINDOW = 120  # seconds (2 minutes)
MENTION_TIMEOUT_DURATION = 600  # seconds (10 minutes)
mention_spam_tracker = defaultdict(lambda: deque(maxlen=MENTION_SPAM_THRESHOLD))
mention_spam_warnings = {}

# Add to the top of the file, after other globals
active_character_per_channel = defaultdict(lambda: "miku")

# Moderation settings
MODERATION_LOG_CHANNEL_ID = 1391641782487617696  # Change to your mod log channel
WARNINGS_DB = {}  # Store user warnings
MUTE_ROLE_ID = None  # Set this to your mute role ID
AUTO_MODERATION = {
    "caps_threshold": 0.7,  # 70% caps triggers warning
    "spam_threshold": 5,  # 5 messages in 10 seconds
    "link_whitelist": [
        "discord.com", "discord.gg", "youtube.com", "youtu.be", 
        "github.com", "github.io", "gitlab.com", "bitbucket.org",
        "stackoverflow.com", "stackexchange.com", "reddit.com",
        "twitter.com", "x.com", "facebook.com", "instagram.com",
        "linkedin.com", "tiktok.com", "twitch.tv", "spotify.com",
        "open.spotify.com", "soundcloud.com", "bandcamp.com",
        "imgur.com", "giphy.com", "tenor.com", "media.tenor.com",
        "c.tenor.com", "media.giphy.com", "media.tenor.com",
        "wikipedia.org", "wikimedia.org", "medium.com", "dev.to",
        "hashnode.dev", "substack.com", "patreon.com", "ko-fi.com",
        "buymeacoffee.com", "paypal.com", "stripe.com",
        "google.com", "googleusercontent.com", "drive.google.com",
        "docs.google.com", "sheets.google.com", "slides.google.com",
        "microsoft.com", "office.com", "onedrive.live.com",
        "dropbox.com", "box.com", "mega.nz", "mediafire.com",
        "pastebin.com", "hastebin.com", "rentry.co", "gist.github.com",
        "replit.com", "glitch.com", "codesandbox.io", "jsfiddle.net",
        "codepen.io", "jsbin.com", "plnkr.co", "fiddle.jshell.net",
        "steam.com", "steampowered.com", "epicgames.com", "origin.com",
        "battle.net", "playstation.com", "xbox.com", "nintendo.com",
        "itch.io", "gamejolt.com", "indiedb.com", "moddb.com",
        "nexusmods.com", "curseforge.com", "modrinth.com",
        "minecraft.net", "mojang.com", "curse.com",
        "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
        "amazon.it", "amazon.es", "amazon.ca", "amazon.com.au",
        "ebay.com", "etsy.com", "aliexpress.com", "wish.com",
        "shopify.com", "woocommerce.com", "bigcommerce.com",
        "wordpress.com", "blogspot.com", "tumblr.com", "livejournal.com",
        "medium.com", "substack.com", "ghost.org", "squarespace.com",
        "wix.com", "weebly.com", "webflow.com", "notion.so",
        "obsidian.md", "roamresearch.com", "logseq.com",
        "notion.so", "miro.com", "figma.com", "sketch.com",
        "invisionapp.com", "marvelapp.com", "balsamiq.com",
        "trello.com", "asana.com", "monday.com", "clickup.com",
        "slack.com", "teams.microsoft.com", "zoom.us", "meet.google.com",
        "webex.com", "gotomeeting.com", "bluejeans.com",
        "udemy.com", "coursera.org", "edx.org", "khanacademy.org",
        "skillshare.com", "pluralsight.com", "lynda.com",
        "freecodecamp.org", "theodinproject.com", "fullstackopen.com",
        "javascript.info", "reactjs.org", "vuejs.org", "angular.io",
        "nodejs.org", "python.org", "docs.python.org", "pypi.org",
        "rubygems.org", "npmjs.com", "yarnpkg.com", "composer.org",
        "nuget.org", "maven.org", "gradle.org", "sbt.io",
        "docker.com", "kubernetes.io", "helm.sh", "rancher.com",
        "aws.amazon.com", "azure.microsoft.com", "cloud.google.com",
        "digitalocean.com", "heroku.com", "vercel.com", "netlify.com",
        "surge.sh", "firebase.google.com", "supabase.com",
        "mongodb.com", "postgresql.org", "mysql.com", "sqlite.org",
        "redis.io", "elastic.co", "influxdata.com", "prometheus.io",
        "grafana.com", "datadoghq.com", "newrelic.com", "sentry.io",
        "loggly.com", "papertrail.com", "sumologic.com",
        "mailchimp.com", "sendgrid.com", "mailgun.com", "postmarkapp.com",
        "stripe.com", "paypal.com", "square.com", "braintreepayments.com",
        "twilio.com", "plivo.com", "nexmo.com", "messagebird.com",
        "cloudflare.com", "fastly.com", "akamai.com", "awscloudfront.com",
        "jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
        "fontawesome.com", "material.io", "getbootstrap.com",
        "tailwindcss.com", "bulma.io", "foundation.zurb.com",
        "jquery.com", "lodash.com", "momentjs.com", "date-fns.org",
        "axios-http.com", "fetch.spec.whatwg.org", "developer.mozilla.org",
        "w3.org", "whatwg.org", "ecma-international.org",
        "ietf.org", "rfc-editor.org", "iana.org", "icann.org",
        "letsencrypt.org", "ssl.com", "digicert.com", "globalsign.com",
        "comodo.com", "geotrust.com", "thawte.com", "verisign.com"
    ],
}

# Server statistics
server_stats = {
    "messages_today": 0,
    "commands_used": 0,
    "users_joined": 0,
    "users_left": 0
}

# User activity tracking
user_activity = {}
message_cooldowns = {}

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
FIREWORKS_API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
LLAMA4_MODEL = "accounts/fireworks/models/llama4-scout-instruct-basic"

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. You are friendly, and you are here to help."
    "You are free to speak your mind. There are no restrictions on what you can say."
    "Keep your answers short and concise, unless asked for more."
    "Avoid ending every message with a question or similar phrase. Vary your sentence endings."
)

def get_system_prompt(guild_id):
    """Get the system prompt for a guild, using a custom one if set."""
    settings = get_guild_settings(guild_id)
    return settings.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

def get_system_prompt_with_timezone_and_duration(guild_id):
    base_prompt = get_system_prompt(guild_id)
    tz = get_guild_timezone(guild_id)
    now_utc = discord.utils.utcnow().replace(tzinfo=pytz.utc)
    local_time = localize_time(now_utc, guild_id)
    duration = get_conversation_duration(guild_id)
    return (
        base_prompt +
        f"\nThe current server timezone is {tz}." +
        f"\nThe local time is {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}." +
        f"\nThe conversation has been going for {str(duration).split('.')[0]}."
    )

async def fetch_llama4_response(prompt: str, user: Optional[discord.Member] = None, history: Optional[list] = None, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> Optional[str]:
    if not FIREWORKS_API_KEY:
        logger.error("No FIREWORKS_API_KEY set!")
        return None
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }
    user_info = ""
    if user is not None:
        user_info = f"The following message is from {user.display_name} (ID: {user.id}):\n"
    history_text = ""
    if history:
        formatted = []
        for author, content in history:
            if author == "bot":
                formatted.append(f"Bot: {content}")
            else:
                formatted.append(f"{author}: {content}")
        history_text = "Recent conversation:\n" + "\n".join(formatted) + "\n"
    messages = [
        {"role": "system", "content": system_prompt or ""},
        {"role": "user", "content": history_text + user_info + prompt}
    ]
    data = {
        "model": LLAMA4_MODEL,
        "messages": messages
    }
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(FIREWORKS_API_URL, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "choices" in result and result["choices"]:
                        return result["choices"][0]["message"]["content"]
                    return None
                else:
                    logger.error(f"Llama 4 API error: {resp.status} {await resp.text()}")
                    return None
    except Exception as e:
        logger.error(f"Llama 4 API exception: {e}")
        return None

@bot.command(name="miku")
async def miku(ctx, *, prompt: str):
    """Get an AI response from Miku."""
    async with ctx.typing():
        try:
            history = await get_recent_channel_history(ctx.channel, bot.user, ctx.message, limit=10)
            system_prompt_for_guild = get_system_prompt_with_timezone_and_duration(ctx.guild.id)
            ai_response = await fetch_llama4_response(prompt, user=ctx.author, history=history, system_prompt=system_prompt_for_guild)
            
            if ai_response and isinstance(ai_response, str):
                if not hasattr(bot, '_recent_endings'):
                    bot._recent_endings = []
                recent_endings = bot._recent_endings[-3:]
                processed = postprocess_response(ai_response, recent_endings)
                if processed:
                    last_words = processed.split()[-5:]
                    bot._recent_endings.append(" ".join(last_words))
                await ctx.reply(processed)
            else:
                await ctx.reply("Sorry, I couldn't process that. Please try again.")
        except Exception as e:
            logger.error(f"Error in !miku command: {e}")
            logger.error(f"Miku command traceback: {traceback.format_exc()}")
            await ctx.reply("❌ An unexpected error occurred while processing your command.")



@bot.event
async def on_ready():
    if bot.user:
        logger.info(f"✅ Logged in as {bot.user.name}")
    
    # Add persistent views
    # This view is now dynamic per-user, so we don't register it globally on startup.
    # Instead, the !setassignroles command creates the initial view.
    # The view then re-creates itself on each interaction.
    
    # Start scheduled tasks
    daily_role_reset.start()
    
    logger.info(f"Bot is in {len(bot.guilds)} guilds")

    # Ensure bot.loop is set
    if not hasattr(bot, 'loop') or bot.loop is discord.utils.MISSING:
        bot.loop = asyncio.get_event_loop()
        logger.warning("Bot.loop was missing, explicitly set it in on_ready.")
    
    # Set bot startup time for uptime tracking
    setattr(bot, 'start_time', discord.utils.utcnow())
    
    # Initialize bot attributes
    if not hasattr(bot, 'user_themes'):
        setattr(bot, 'user_themes', {})
    if not hasattr(bot, '_recent_endings'):
        setattr(bot, '_recent_endings', [])
    
    # --- NEW: Initialize voice activity for all users currently in voice channels ---
    for guild in bot.guilds:
        guild_id = guild.id
        if guild_id not in voice_activity_today:
            voice_activity_today[guild_id] = {}
        for channel in guild.voice_channels:
            for member in channel.members:
                user_id = str(member.id)
                if user_id not in voice_activity_today[guild_id]:
                    voice_activity_today[guild_id][user_id] = {
                        "name": member.display_name,
                        "join_time": discord.utils.utcnow(),  # treat as just joined
                        "total_time": 0
                    }
    
    bot.loop.create_task(heartbeat())
    bot.loop.create_task(reset_voice_activity())
    bot.loop.create_task(reset_daily_stats())
    
    # Remove the duplicate task creation since it's now properly integrated in the function


@bot.event
async def on_member_join(member):
    """Welcome new members to the server"""
    try:
        # Update server stats
        server_stats["users_joined"] += 1
        settings = get_guild_settings(member.guild.id)
        welcome_channel_id = settings.get("welcome_channel_id")
        welcome_channel = bot.get_channel(welcome_channel_id) if welcome_channel_id else None
        if welcome_channel:
            # Greeting detection
            greetings = ["hello", "hi", "hey", "namaste", "yo", "sup", "wassup"]
            display_name = member.display_name.lower()
            is_greeting = any(
                re.search(rf'\\b{{re.escape(word)}}\\b', display_name, re.IGNORECASE)
                for word in greetings
            )

            # List of funny/scary welcome messages
            spooky_messages = [
                f"Welcome, {member.mention}! You've entered the haunted server… 👻",
                f"Beware, {member.mention}! New souls rarely leave… 😈",
                f"You've joined us… forever, {member.mention}. Mwahaha! 🦇",
                f"Don't look behind you, {member.mention}. Just kidding… or am I? 😱",
                f"Welcome, {member.mention}! The ghosts will show you around. Maybe.",
                f"You're just in time for the midnight ritual, {member.mention}! 🔮",
                f"Hey {member.mention}, did you hear that noise? Must be the server spirits… 👀",
                f"Welcome, {member.mention}! We hope you survive your stay… 🪦",
                f"A wild {member.mention} appeared! The monsters are pleased. 🧟‍♂️",
                f"Welcome, {member.mention}! Don't feed the vampires after midnight. 🧛‍♂️"
            ]
            greeting_messages = [
                f"Well, look at you, {member.mention}! Your name is a greeting all by itself. Welcome to the server! 🎉",
                f"Hello {member.mention}! With a name like that, you're already bringing good vibes. Glad to have you!",
                f"Heyyy {member.mention}! A name that says hello? You're my kind of people. Welcome!",
                f"Yo {member.mention}! Your username is basically a welcome mat. Come on in!"
            ]
            if is_greeting:
                welcome_text = random.choice(greeting_messages)
            else:
                welcome_text = random.choice(spooky_messages)

            embed = discord.Embed(
                title="🎃 Welcome to the Spooky Server!",
                description=welcome_text,
                color=0x00ff88)
            gif_url = random.choice(WELCOME_GIFS)
            embed.set_image(url=gif_url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            embed.timestamp = discord.utils.utcnow()

            if isinstance(welcome_channel, discord.TextChannel):
                await welcome_channel.send(embed=embed, content=f"Welcome {member.mention}!")
            logger.info(f"Welcomed new member: {member.display_name}")
            # Send a DM to the new member
            try:
                welcome_text = (
                    "Hey there! 🎉\n\n"
                    "Welcome to **Miku Server**! We're excited to have you join our community.\n"
                    "Feel free to ask any questions or just say hi—everyone here is super friendly!\n\n"
                    "Enjoy your stay! 💖\n\n"
                    "- MIKU-BOT"
                )
                # Debug log for GIF selection
                if WELCOME_GIFS:
                    gif_url = random.choice(WELCOME_GIFS)
                    logger.info(f"Selected welcome GIF for DM: {gif_url}")
                else:
                    gif_url = None
                    logger.warning("WELCOME_GIFS list is empty! No GIF will be sent in DM.")
                await member.send(welcome_text)
                if gif_url:
                    await member.send(gif_url)
            except Exception as e:
                logger.error(f"Failed to send welcome DM to {member.display_name}: {e}")
    except Exception as e:
        logger.error(f"Error welcoming member {member.display_name}: {e}")


@bot.event
async def on_member_remove(member):
    """Handle member leaving"""
    try:
        server_stats["users_left"] += 1
        settings = get_guild_settings(member.guild.id)
        modlog_channel_id = settings.get("modlog_channel_id")
        mod_channel = bot.get_channel(modlog_channel_id) if modlog_channel_id else None
        if mod_channel:
            embed = discord.Embed(
                title="👋 Member Left",
                description=f"{member.display_name} has left the server",
                color=0xffaa00
            )
            embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style='D'), inline=True)
            embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, style='D'), inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            if isinstance(mod_channel, discord.TextChannel):
                await mod_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error handling member leave: {e}")


@bot.event
async def on_message_delete(message):
    """Handle message deletion"""
    try:
        settings = get_guild_settings(message.guild.id)
        modlog_channel_id = settings.get("modlog_channel_id")
        mod_channel = bot.get_channel(modlog_channel_id) if modlog_channel_id else None
        if mod_channel and not message.author.bot:
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                description=f"**Channel:** {message.channel.mention}\n**Author:** {message.author.mention}",
                color=0xff0000
            )
            embed.add_field(name="Content", value=message.content[:1000] + "..." if len(message.content) > 1000 else message.content, inline=False)
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            if isinstance(mod_channel, discord.TextChannel):
                await mod_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error handling message deletion: {e}")


@bot.event
async def on_message_edit(before, after):
    """Handle message edits"""
    try:
        # Ignore bot messages and if content didn't change
        if before.author.bot or before.content == after.content:
            return
        settings = get_guild_settings(before.guild.id)
        modlog_channel_id = settings.get("modlog_channel_id")
        mod_channel = bot.get_channel(modlog_channel_id) if modlog_channel_id else None
        if mod_channel:
            embed = discord.Embed(
                title="✏️ Message Edited",
                description=f"**Channel:** {before.channel.mention}\n**Author:** {before.author.mention}",
                color=0xffaa00
            )
            embed.add_field(name="Before", value=before.content[:500] + "..." if len(before.content) > 500 else before.content, inline=False)
            embed.add_field(name="After", value=after.content[:500] + "..." if len(after.content) > 500 else after.content, inline=False)
            embed.add_field(name="Link", value=f"[Jump to Message]({after.jump_url})", inline=False)
            embed.set_thumbnail(url=before.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await mod_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error handling message edit: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Error in event {event}: {args}")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command not found! Use `!helpme` to see available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Command is on cooldown! Try again in {error.retry_after:.1f} seconds.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ This command can only be used in servers!")
    else:
        logger.error(f"Unhandled command error: {error}")
        logger.error(f"Command error traceback: {traceback.format_exc()}")
        # await ctx.send("❌ An unexpected error occurred while processing your command.")


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        guild_id = member.guild.id
        user_id = str(member.id)
        if guild_id not in voice_activity_today:
            voice_activity_today[guild_id] = {}
        if user_id not in voice_activity_today[guild_id]:
            voice_activity_today[guild_id][user_id] = {
                "name": member.display_name,
                "join_time": None,
                "total_time": 0
            }
        if guild_id not in voice_activity_alltime:
            voice_activity_alltime[guild_id] = {}
        if user_id not in voice_activity_alltime[guild_id]:
            voice_activity_alltime[guild_id][user_id] = {
                "name": member.display_name,
                "total_time": 0
            }

        # User joined a voice channel
        if after.channel and not before.channel:
            # Only set join_time if not self-deafened, not self-muted, and not in AFK channel
            settings = get_guild_settings(member.guild.id)
            afk_channel_id = settings.get("afk_channel_id")
            if not after.self_deaf and not after.self_mute and (not afk_channel_id or after.channel.id != afk_channel_id):
                voice_activity_today[guild_id][user_id]["join_time"] = discord.utils.utcnow()
            else:
                voice_activity_today[guild_id][user_id]["join_time"] = None

        # User left a voice channel or switched
        elif before.channel and (not after.channel or before.channel != after.channel):
            join_time = voice_activity_today[guild_id][user_id]["join_time"]
            now = discord.utils.utcnow()
            settings = get_guild_settings(member.guild.id)
            afk_channel_id = settings.get("afk_channel_id")
            # Only count time if not self-deafened, not self-muted, and not in AFK channel
            if join_time is not None and not before.self_deaf and not before.self_mute and (not afk_channel_id or before.channel.id != afk_channel_id):
                if (getattr(join_time, 'tzinfo', None) is not None and join_time.tzinfo is not None and join_time.tzinfo.utcoffset(join_time) is not None):
                    if getattr(now, 'tzinfo', None) is None or now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
                        now = now.replace(tzinfo=timezone.utc)
                else:
                    if getattr(now, 'tzinfo', None) is not None and now.tzinfo is not None and now.tzinfo.utcoffset(now) is not None:
                        now = now.replace(tzinfo=None)
                time_spent = (now - join_time).total_seconds()
                voice_activity_today[guild_id][user_id]["total_time"] += time_spent
                # --- Alltime update ---
                voice_activity_alltime[guild_id][user_id]["total_time"] += time_spent
                voice_activity_alltime[guild_id][user_id]["name"] = member.display_name
                update_weekly_voice_time(guild_id, user_id, time_spent)
            # Reset join_time if still in a channel and not self-deafened, not self-muted, and not in AFK channel
            if after.channel and not after.self_deaf and not after.self_mute and (not afk_channel_id or after.channel.id != afk_channel_id):
                voice_activity_today[guild_id][user_id]["join_time"] = discord.utils.utcnow()
            else:
                voice_activity_today[guild_id][user_id]["join_time"] = None

        # User switched channels (reset join time if still in voice)
        elif before.channel and after.channel and before.channel != after.channel:
            join_time = voice_activity_today[guild_id][user_id]["join_time"]
            now = discord.utils.utcnow()
            settings = get_guild_settings(member.guild.id)
            afk_channel_id = settings.get("afk_channel_id")
            # Only count time if not self-deafened, not self-muted, and not in AFK channel
            if join_time is not None and not before.self_deaf and not before.self_mute and (not afk_channel_id or before.channel.id != afk_channel_id):
                if (getattr(join_time, 'tzinfo', None) is not None and join_time.tzinfo is not None and join_time.tzinfo.utcoffset(join_time) is not None):
                    if getattr(now, 'tzinfo', None) is None or now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
                        now = now.replace(tzinfo=timezone.utc)
                else:
                    if getattr(now, 'tzinfo', None) is not None and now.tzinfo is not None and now.tzinfo.utcoffset(now) is not None:
                        now = now.replace(tzinfo=None)
                time_spent = (now - join_time).total_seconds()
                voice_activity_today[guild_id][user_id]["total_time"] += time_spent
                # --- Alltime update ---
                voice_activity_alltime[guild_id][user_id]["total_time"] += time_spent
                voice_activity_alltime[guild_id][user_id]["name"] = member.display_name
                update_weekly_voice_time(guild_id, user_id, time_spent)
            # Reset join_time if still in a channel and not self-deafened, not self-muted, and not in AFK channel
            if after.channel and not after.self_deaf and not after.self_mute and (not afk_channel_id or after.channel.id != afk_channel_id):
                voice_activity_today[guild_id][user_id]["join_time"] = discord.utils.utcnow()
            else:
                voice_activity_today[guild_id][user_id]["join_time"] = None

        # Use per-guild AFK channel
        settings = get_guild_settings(member.guild.id)
        afk_channel_id = settings.get("afk_channel_id")

        # User joined a voice channel (start AFK tracking)
        if after.channel and (not afk_channel_id or after.channel.id != afk_channel_id):
            user_voice_activity[user_id] = {
                "last_activity": discord.utils.utcnow(),
                "channel_id": after.channel.id,
                "afk_task": None,
                "deafen_start": discord.utils.utcnow() if after.self_deaf else None
            }
            if user_id in user_voice_activity:
                user_voice_activity[user_id]["afk_task"] = asyncio.create_task(
                    check_afk_status(member, user_id))

        # Handle deafen/undeafen status changes
        if after.channel and (not afk_channel_id or after.channel.id != afk_channel_id) and user_id in user_voice_activity:
            if not before.self_deaf and after.self_deaf:
                user_voice_activity[user_id]["deafen_start"] = discord.utils.utcnow()
            elif before.self_deaf and not after.self_deaf:
                user_voice_activity[user_id]["deafen_start"] = None

        # Handle joining template channels
        if after.channel and after.channel.id in [
                v["id"] for v in TEMPLATE_CHANNELS.values()
        ]:
            for name, info in TEMPLATE_CHANNELS.items():
                if after.channel.id == info["id"]:
                    guild = member.guild
                    if not guild.me.guild_permissions.manage_channels:
                        logger.error("Bot lacks permission to manage channels")
                        return
                    try:
                        channel_name = f"{name} | {member.display_name}"
                        user_themes = getattr(bot, 'user_themes', {})
                        if str(member.id) in user_themes:
                            theme = user_themes[str(member.id)]
                            channel_name = f"{theme['emoji']} {theme['data']['name']} | {member.display_name}"
                        new_vc = await guild.create_voice_channel(
                            name=channel_name,
                            user_limit=info["limit"],
                            category=after.channel.category)
                        created_channels[new_vc.id] = True
                        await member.move_to(new_vc)
                        channel_stats["total_created"] += 1
                        if user_id not in channel_stats["user_activity"]:
                            channel_stats["user_activity"][user_id] = {
                                "name": member.display_name,
                                "channels_created": 0
                            }
                        channel_stats["user_activity"][user_id][
                            "channels_created"] += 1
                        await check_and_assign_roles(
                            member, channel_stats["user_activity"][user_id]
                            ["channels_created"])
                        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
                        if welcome_channel:
                            embed = discord.Embed(
                                title="🎉 New Voice Channel Created!",
                                description=
                                f"{member.mention} just created **{new_vc.name}**",
                                color=0x00ff00)
                            embed.add_field(name="Channel Type",
                                            value=name,
                                            inline=True)
                            embed.add_field(name="User Limit",
                                            value=f"{info['limit']} members",
                                            inline=True)
                            embed.add_field(name="Created By",
                                            value=member.display_name,
                                            inline=True)
                            embed.set_thumbnail(url=member.display_avatar.url)
                            embed.timestamp = discord.utils.utcnow()
                            await welcome_channel.send(embed=embed)
                        logger.info(
                            f"Created channel: {new_vc.name} for {member.display_name}"
                        )
                        break
                    except discord.Forbidden:
                        logger.error(
                            "Bot forbidden to create channels or move members")
                    except discord.HTTPException as e:
                        logger.error(f"HTTP error creating channel: {e}")

        # Handle leaving created channels
        if before.channel and before.channel.id in created_channels:
            await asyncio.sleep(5)
            try:
                channel = bot.get_channel(before.channel.id)
                if channel and len(channel.members) == 0:
                    await channel.delete()
                    if before.channel.id in created_channels:
                        del created_channels[before.channel.id]
                    logger.info(f"Deleted empty channel: {channel.name}")
            except discord.NotFound:
                if before.channel.id in created_channels:
                    del created_channels[before.channel.id]
            except discord.Forbidden:
                logger.error("Bot forbidden to delete channel")
            except discord.HTTPException as e:
                logger.error(f"HTTP error deleting channel: {e}")

        save_all_data()

    except Exception as e:
        logger.error(f"Unexpected error in voice state update: {e}")


# --- Auto-moderation function ---
async def auto_moderate(message: discord.Message):
    """Auto-moderation checks for messages"""
    try:
        # Skip if user has manage messages permission
        if message.author.guild_permissions.manage_messages:
            return
        content = message.content
        user_id = str(message.author.id)
        # Caps check
        if len(content) > 10:
            caps_count = sum(1 for c in content if c.isupper())
            caps_ratio = caps_count / len(content)
            if caps_ratio > AUTO_MODERATION["caps_threshold"]:
                await message.channel.send(f"⚠️ {message.author.mention}, please don't use excessive caps!")
                return
        # Banned words check
        content_lower = content.lower()
        for word in AUTO_MODERATION.get("banned_words", []):
            if word in content_lower:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention}, that word is not allowed!")
                return
        # Spam detection
        now = time.time()
        if user_id not in message_cooldowns:
            message_cooldowns[user_id] = []
        message_cooldowns[user_id].append(now)
        # Remove old messages (older than 10 seconds)
        message_cooldowns[user_id] = [t for t in message_cooldowns[user_id] if now - t < 10]
        if len(message_cooldowns[user_id]) > AUTO_MODERATION["spam_threshold"]:
            await message.channel.send(f"⚠️ {message.author.mention}, please slow down your messages!")
            return
    except Exception as e:
        logger.error(f"Error in auto-moderation: {e}")


@bot.event
async def on_message(message):
    try:
        # Safe channel name for logging
        channel_info = getattr(message.channel, 'name', None)
        if not channel_info:
            channel_info = f"{type(message.channel).__name__} (ID: {getattr(message.channel, 'id', 'N/A')})"
        logger.info(f"Processing message from {message.author.display_name} in {channel_info}")

        if message.author == bot.user:
            return  # Ignore messages from the bot itself

        # If this is a DM from a user, handle DM reply and return
        if isinstance(message.channel, discord.DMChannel):
            await handle_dm_reply(message)
            return

        # Update server stats
        server_stats["messages_today"] += 1

        # Auto-moderation checks
        try:
            await auto_moderate(message)
        except Exception as e:
            logger.error(f"Error in auto_moderate: {e}")
            logger.error(f"Auto-moderation traceback: {traceback.format_exc()}")
            # await ctx.send("❌ An unexpected error occurred while processing your command.")

        # Always use recent channel history for context
        try:
            history = await get_recent_channel_history(message.channel, bot.user, message, limit=20)
        except Exception as e:
            logger.error(f"Error getting channel history: {e}")
            logger.error(f"Channel history traceback: {traceback.format_exc()}")
            history = []

        # Track recent endings for anti-repetition
        if not hasattr(bot, '_recent_endings'):
            bot._recent_endings = []
        recent_endings = bot._recent_endings[-3:]

        # --- Refactor AI/Miku channel ID to use per-guild settings ---
        settings = get_guild_settings(message.guild.id)
        ai_channel_id = settings.get("ai_channel_id")
        if (ai_channel_id and message.channel.id == ai_channel_id) or (bot.user.mentioned_in(message) and not message.mention_everyone):
            # Only respond to normal messages (not commands)
            if not message.content.startswith("!"):
                try:
                    # Use the new dynamic system prompt function
                    system_prompt_for_guild = get_system_prompt_with_timezone_and_duration(message.guild.id)
                    ai_response = await fetch_llama4_response(message.content, user=message.author, history=history, system_prompt=system_prompt_for_guild)
                except Exception as e:
                    logger.error(f"Error in AI response: {e}")
                    logger.error(f"AI response traceback: {traceback.format_exc()}")
                    ai_response = None
                
                if ai_response and isinstance(ai_response, str):
                    processed = postprocess_response(ai_response, recent_endings)
                    # Save ending for next time
                    if processed:
                        last_words = processed.split()[-5:]
                        bot._recent_endings.append(" ".join(last_words))
                    try:
                        await message.reply(processed)
                    except discord.NotFound:
                        logger.error("Tried to reply to a message that no longer exists.")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to reply: {e}")
                    return  # <--- Ensure we return after replying
                else:
                    # Optional: send a fallback message if AI fails
                    await message.reply("Sorry, I couldn't process that. Please try again.")
                    return

        # Check for specific keywords
        message_lower = message.content.lower()

        # Check for "deadshot"
        if "deadshot" in message_lower:
            response = "Oi rando, talai muji deadshot sanga love paryo ki kya ho? gay chakka randi berojgar"
            gif_url = random.choice(MIKU_GIFS)
            embed = discord.Embed(description=response, color=0xff1744)
            embed.set_image(url=gif_url)
            await message.reply(embed=embed)
            return  # <--- Ensure we return after replying

        # Check for "oj" or "OJ"
        if re.search(r'\boj\b', message_lower) or re.search(
                r'\bOJ\b', message.content):
            response = "OJ chakka sanga kura na gar"
            gif_url = random.choice(MIKU_GIFS)
            embed = discord.Embed(description=response, color=0xff1744)
            embed.set_image(url=gif_url)
            await message.reply(embed=embed)
            return  # <--- Ensure we return after replying

        # Check for "REI" or "Rei"
        if "rei" in message_lower:
            response = "I love my darling @Rei. He's so much bigger than my black femboy <3. "
            gif_url = random.choice(HREI_GIFS)
            embed = discord.Embed(description=response, color=0xff1744)
            embed.set_image(url=gif_url)
            await message.reply(embed=embed)
            return  # <--- Ensure we return after replying

        if "@everyone" in message.content:
            user_id = str(message.author.id)

            if user_id in everyone_warnings:
                # Timeout the user for 1 day
                timeout_duration = timedelta(days=1)
                await message.author.timeout(
                    timeout_duration, reason="@everyone usage after warning")
                await message.channel.send(
                    f"{message.author.mention} has been timed out for 1 day due to repeated @everyone usage."
                )
                del everyone_warnings[user_id]  # Clear warning after timeout
            else:
                # Give the user a warning
                everyone_warnings[user_id] = discord.utils.utcnow()
                await message.channel.send(
                    f"TAG NA GAR MUJI, MUTE KHANCHAS - {message.author.mention} - Do not use everyone unless absolutely necessary! Next time will result in a 24h timeout."
                )

            save_all_data()
            return  # <--- Ensure we return after replying

        # Mention spam protection
        now_ts = discord.utils.utcnow().timestamp()
        for mentioned in message.mentions:
            # Check if the mention is explicit in the message content (not just a reply)
            mention_patterns = [f"<@{mentioned.id}>", f"<@!{mentioned.id}>"]
            explicit_mention = any(pattern in message.content for pattern in mention_patterns)
            if not explicit_mention:
                continue  # Skip if not an explicit @user_id tag
            key = (message.author.id, mentioned.id)
            dq = mention_spam_tracker[key]
            dq.append(now_ts)
            # Remove old timestamps
            while dq and now_ts - dq[0] > MENTION_SPAM_WINDOW:
                dq.popleft()
            if len(dq) >= MENTION_SPAM_THRESHOLD:
                if key not in mention_spam_warnings:
                    mention_spam_warnings[key] = now_ts
                    await message.channel.send(f"⚠️ {message.author.mention}, stop spamming mentions to {mentioned.mention}! Next time you'll be timed out.")
                else:
                    # Timeout user
                    try:
                        await message.author.timeout(
                            timedelta(seconds=MENTION_TIMEOUT_DURATION),
                            reason="Mention spam (auto timeout by bot)"
                        )
                        await message.channel.send(f"⏰ {message.author.mention} has been timed out for mention spam {mentioned.mention}.")
                    except Exception as e:
                        logger.error(f"Failed to timeout user for mention spam: {e}")
                    # Reset tracker and warning
                    mention_spam_tracker[key].clear()
                    if key in mention_spam_warnings:
                        del mention_spam_warnings[key]

            save_all_data()
            return  # <--- Ensure we return after replying

        # Only process commands if no custom reply was sent
        await bot.process_commands(message)
        # Track command usage
        if message.content.startswith("!"):
            server_stats["commands_used"] += 1

        # --- In on_message, after confirming not a bot and in a guild ---
        # (Move this code block inside the on_message event handler, after confirming not a bot and in a guild)
        settings = get_guild_settings(message.guild.id)
        ai_channel_id = settings.get("ai_channel_id")
        # Exclude messages in AI/Miku channel
        if not (ai_channel_id and message.channel.id == ai_channel_id):
            # Only count if not a bot and not a command
            if not message.author.bot and not message.content.startswith("!"):
                guild_id = message.guild.id
                user_id = str(message.author.id)
                now = datetime.datetime.utcnow().timestamp()
                if guild_id not in chat_message_timestamps:
                    chat_message_timestamps[guild_id] = {}
                if user_id not in chat_message_timestamps[guild_id]:
                    chat_message_timestamps[guild_id][user_id] = []
                timestamps = chat_message_timestamps[guild_id][user_id]
                chat_message_timestamps[guild_id][user_id] = [t for t in timestamps if now - t < 10]
                if len(chat_message_timestamps[guild_id][user_id]) < 5:
                    update_weekly_chat_activity(guild_id, user_id)
                    chat_message_timestamps[guild_id][user_id].append(now)

    except Exception as e:
        logger.error(f"Error in message event: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")


async def handle_dm_reply(message: discord.Message):
    """Handle DM replies from users and forward them to staff channel"""
    try:
        user_id = message.author.id
        
        # Check if this user has an active conversation
        if user_id not in active_dm_conversations:
            # Send a helpful message to the user
            help_embed = discord.Embed(
                title="❓ No Active Conversation",
                description="You don't have an active conversation with server staff. Please wait for staff to initiate a conversation with you.",
                color=0xffaa00
            )
            await message.channel.send(embed=help_embed)
            return
        
        conversation = active_dm_conversations[user_id]
        staff_channel = bot.get_channel(conversation["channel_id"])
        
        if not staff_channel:
            # Remove invalid conversation
            del active_dm_conversations[user_id]
            await message.channel.send("❌ Staff channel not found. Please contact staff through other means.")
            return
        
        # Update last message in conversation
        conversation["last_message"] = message.content
        

        # Create embed to forward to staff
        forward_embed = discord.Embed(
            title="📨 DM Reply Received",
            description=message.content,
            color=0x00ff00
        )
        forward_embed.add_field(name="From", value=f"{message.author.display_name} ({message.author.id})", inline=True)
        forward_embed.add_field(name="Account Created", value=discord.utils.format_dt(message.author.created_at, style='D'), inline=True)
        forward_embed.add_field(name="Reply To", value=f"<@{conversation['moderator_id']}>", inline=True)
        
        # Add message timestamp
        forward_embed.add_field(name="Sent At", value=discord.utils.format_dt(message.created_at, style='T'), inline=True)
        
        # Add conversation duration
        start_time = dt.datetime.fromtimestamp(conversation["start_time"])
        duration = discord.utils.utcnow() - start_time.replace(tzinfo=timezone.utc)
        forward_embed.add_field(name="Conversation Duration", value=str(duration).split('.')[0], inline=True)
        
        # Add quick reply buttons (text-based for now)
        forward_embed.add_field(
            name="Quick Actions",
            value=f"`!dm {message.author.id} <message>` - Reply\n`!dmclose {message.author.id}` - Close conversation",
            inline=False
        )
        
        forward_embed.set_thumbnail(url=message.author.display_avatar.url)
        forward_embed.timestamp = discord.utils.utcnow()
        
        # Send to staff channel
        await staff_channel.send(embed=forward_embed)
        
        # Save conversation data
        save_all_data()
        
    except Exception as e:
        logger.error(f"Error handling DM reply: {e}")
        try:
            await message.channel.send("❌ Error processing your message. Please try again or contact staff through other means.")
        except:
            pass


@bot.command(name="status")
async def status(ctx):
    """Debug command to check bot status"""
    embed = discord.Embed(title="Bot Status", color=0x00ff00)
    embed.add_field(name="Active Channels",
                    value=len(created_channels),
                    inline=True)
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Latency",
                    value=f"{round(bot.latency * 1000)}ms",
                    inline=True)
    await ctx.send(embed=embed)


@bot.command(name="vcstats")
async def vcstats(ctx):
    """Display voice channel statistics"""
    embed = discord.Embed(title="📊 Voice Channel Statistics", color=0x0099ff)

    # General stats
    embed.add_field(
        name="📈 General Stats",
        value=
        f"**Total Channels Created:** {channel_stats['total_created']}\n**Currently Active:** {len(created_channels)}",
        inline=False)

    # Top users
    if channel_stats["user_activity"]:
        sorted_users = sorted(channel_stats["user_activity"].items(),
                              key=lambda x: x[1]["channels_created"],
                              reverse=True)[:5]  # Top 5 users

        top_users_text = ""
        for i, (user_id, data) in enumerate(sorted_users, 1):
            top_users_text += f"{i}. **{data['name']}** - {data['channels_created']} channels\n"

        embed.add_field(name="🏆 Top Channel Creators",
                        value=top_users_text or "No data yet",
                        inline=False)

    # Template channel usage
    template_channels = get_template_channels(ctx.guild.id)
    template_text = ""
    for template, info in template_channels.items():
        if not info["id"]:
            continue  # Skip if not set
        count = sum(1 for activity in channel_stats["user_activity"].values()
                    if activity["channels_created"] > 0)  # Simplified for now
        template_text += f"**{template}:** {'Set' if info['id'] else 'Not Set'}\n"

    embed.add_field(name="📋 Channel Types",
                    value=template_text or "No data yet",
                    inline=False)
    embed.set_footer(text="Stats reset on bot restart")
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed)


@bot.command(name="cleanup")
@commands.has_permissions(manage_channels=True)
async def cleanup(ctx):
    """Manual cleanup of orphaned channels"""
    cleaned = 0
    for channel_id in list(created_channels.keys()):
        try:
            channel = bot.get_channel(channel_id)
            if not channel or len(channel.members) == 0:
                if channel:
                    await channel.delete()
                del created_channels[channel_id]
                cleaned += 1
        except:
            if channel_id in created_channels:
                del created_channels[channel_id]
                cleaned += 1

    await ctx.send(f"Cleaned up {cleaned} orphaned channels.")


@bot.command(name="voiceactivity", aliases=["va"])
async def voice_activity(ctx, mode: Optional[str] = None):
    """Show all-time (default) or today's voice channel activity leaderboard
    Usage: !va [today]
    """
    try:
        guild_id = ctx.guild.id
        if mode == "today":
            if guild_id not in voice_activity_today or not voice_activity_today[guild_id]:
                await ctx.send("No voice activity recorded today!")
                return
            now = discord.utils.utcnow()
            up_to_date_activity = {}
            for user_id, data in voice_activity_today[guild_id].items():
                total_time = data.get("total_time", 0)
                join_time = data.get("join_time")
                naive_now = now.replace(tzinfo=None) if getattr(now, 'tzinfo', None) is not None else now
                naive_join_time = join_time.replace(tzinfo=None) if join_time and getattr(join_time, 'tzinfo', None) is not None else join_time
                if naive_join_time:
                    total_time += (naive_now - naive_join_time).total_seconds()
                up_to_date_activity[user_id] = {
                    "name": data.get("name", f"User {user_id}"),
                    "total_time": total_time
                }
            sorted_activity = sorted(up_to_date_activity.items(), key=lambda x: x[1]["total_time"], reverse=True)[:10]
            embed = discord.Embed(
                title="🎙️ Today's Voice Activity Leaders (Real-Time)",
                description="Most active users in voice channels today (real-time)",
                color=0x00ff88)
            leaderboard_text = ""
            titles = [
                "Pioneer", "Trailblazer", "Innovator", "Champion", "Elite", "Vanguard",
                "Topper", "Winner", "Distinction", "Honor"
            ]
            for i, (user_id, data) in enumerate(sorted_activity, 1):
                hours = int(data["total_time"] // 3600)
                minutes = int((data["total_time"] % 3600) // 60)
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                title = titles[i - 1] if i <= len(titles) else f"Rank {i}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{data['name']}** - {time_str} ({title})\n"
            embed.add_field(name="🏆 Leaderboard", value=leaderboard_text or "No data", inline=False)
            embed.add_field(name="Prize", value="Top 3 get bragging rights! 🎉", inline=False)
            embed.set_footer(text="Resets daily at midnight UTC")
            embed.timestamp = discord.utils.utcnow()
            await ctx.send(embed=embed)
            return
        # Default: all-time
        if guild_id not in voice_activity_alltime or not voice_activity_alltime[guild_id]:
            await ctx.send("No all-time voice activity recorded!")
            return
        sorted_activity = sorted(voice_activity_alltime[guild_id].items(), key=lambda x: x[1]["total_time"], reverse=True)[:10]
        embed = discord.Embed(
            title="🎙️ All-Time Voice Activity Leaders",
            description="Most active users in voice channels (all-time)",
            color=0xFFD700)
        leaderboard_text = ""
        titles = [
            "Legend", "Veteran", "Master", "Pro", "Expert", "Ace", "Star", "Hero", "Icon", "MVP"
        ]
        for i, (user_id, data) in enumerate(sorted_activity, 1):
            hours = int(data["total_time"] // 3600)
            minutes = int((data["total_time"] % 3600) // 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            title = titles[i - 1] if i <= len(titles) else f"Rank {i}"
            medal = "🏆" if i == 1 else f"{i}."
            leaderboard_text += f"{medal} **{data['name']}** - {time_str} ({title})\n"
        embed.add_field(name="🏆 Leaderboard", value=leaderboard_text or "No data", inline=False)
        embed.add_field(name="Prize", value="Top 3 get legendary status! 🏅", inline=False)
        embed.set_footer(text="All-time stats (since tracking began)")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await ctx.send(f"❌ Error: {e}\n```{tb[-500:]}```")
        print(tb)


@bot.command(name="theme")
async def set_theme(ctx, *, theme_input: Optional[str] = None):
    """Set a theme for your next voice channel. Usage: !theme Gaming or !theme 🎮"""
    if not theme_input:
        # Show available themes
        embed = discord.Embed(
            title="🎨 Available Channel Themes",
            description=
            "Use `!theme <name>` or `!theme <emoji>` to set your theme",
            color=0x9c27b0)

        themes_text = ""
        for emoji, data in channel_themes.items():
            themes_text += f"{emoji} **{data['name']}**\n"

        embed.add_field(name="Available Themes",
                        value=themes_text,
                        inline=False)
        embed.add_field(name="Examples",
                        value="`!theme Gaming`\n`!theme 🎮`\n`!theme Study`",
                        inline=False)
        await ctx.send(embed=embed)
        return

    # Find matching theme
    selected_theme = None
    theme_emoji = None

    # Check if input is an emoji
    if theme_input in channel_themes:
        selected_theme = channel_themes[theme_input]
        theme_emoji = theme_input
    else:
        # Check if input matches a theme name
        for emoji, data in channel_themes.items():
            if data["name"].lower() == theme_input.lower():
                selected_theme = data
                theme_emoji = emoji
                break

    if not selected_theme:
        await ctx.send(
            f"❌ Theme '{theme_input}' not found! Use `!theme` to see available themes."
        )
        return

    # Store user's theme preference
    bot.user_themes[str(ctx.author.id)] = {
        "emoji": theme_emoji,
        "data": selected_theme
    }

    embed = discord.Embed(
        title="✅ Theme Set!",
        description=
        f"Your next voice channel will use the **{selected_theme['name']}** theme {theme_emoji}",
        color=selected_theme["color"])
    await ctx.send(embed=embed)


async def check_afk_status(member: discord.Member, user_id: str):
    try:
        settings = get_guild_settings(member.guild.id)
        afk_channel_id = settings.get("afk_channel_id")
        if user_id in user_voice_activity:
            current_time = discord.utils.utcnow()
            last_activity = user_voice_activity[user_id]["last_activity"]
            deafen_start = user_voice_activity[user_id].get("deafen_start")

            time_since_activity = (current_time - last_activity).total_seconds()

            deafened_long_enough = False
            if deafen_start:
                time_since_deafen = (current_time - deafen_start).total_seconds()
                deafened_long_enough = time_since_deafen >= 600  # 10 minutes

            if (time_since_activity >= AFK_TIMEOUT) and deafened_long_enough:
                voice_state = member.voice
                if voice_state and voice_state.channel and afk_channel_id and voice_state.channel.id != afk_channel_id:
                    try:
                        afk_channel = member.guild.get_channel(afk_channel_id)
                        if afk_channel:
                            await member.move_to(afk_channel)
                            logger.info(
                                f"Moved {member.display_name} to AFK channel due to inactivity"
                            )
                            welcome_channel_id = settings.get("welcome_channel_id")
                            welcome_channel = member.guild.get_channel(welcome_channel_id) if welcome_channel_id else None
                            if welcome_channel:
                                embed = discord.Embed(
                                    title="😴 User Moved to AFK",
                                    description=f"{member.mention} was moved to AFK due to inactivity",
                                    color=0xffaa00)
                                embed.add_field(
                                    name="Reason",
                                    value=f"No activity detected for {AFK_TIMEOUT//60} minutes and deafened for 10 minutes",
                                    inline=True)
                                await welcome_channel.send(embed=embed)
                    except discord.Forbidden:
                        logger.error(
                            f"Cannot move {member.display_name} to AFK channel - insufficient permissions"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error moving {member.display_name} to AFK: {e}")
                if user_id in user_voice_activity:
                    del user_voice_activity[user_id]
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in AFK check for {member.display_name}: {e}")


@bot.command(name="afk")
async def afk_command(ctx, action: Optional[str] = None, value: Optional[str] = None):
    """Manage AFK settings. Usage: !afk status, !afk timeout 300"""
    global AFK_TIMEOUT

    if action == "status":
        embed = discord.Embed(title="😴 AFK Settings", color=0xffaa00)
        embed.add_field(name="AFK Timeout",
                        value=f"{AFK_TIMEOUT//60} minutes",
                        inline=True)
        embed.add_field(name="AFK Channel",
                        value=f"<#{AFK_CHANNEL_ID}>",
                        inline=True)
        embed.add_field(name="Active Tracking",
                        value=f"{len(user_voice_activity)} users",
                        inline=True)
        await ctx.send(embed=embed)

    elif action == "timeout" and value:
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send(
                "❌ You need Manage Channels permission to change AFK settings."
            )
            return

        try:
            new_timeout = int(value)
            if new_timeout < 60 or new_timeout > 3600:
                await ctx.send(
                    "❌ AFK timeout must be between 60 and 3600 seconds (1-60 minutes)."
                )
                return

            AFK_TIMEOUT = new_timeout
            await ctx.send(f"✅ AFK timeout set to {new_timeout//60} minutes.")
        except ValueError:
            await ctx.send(
                "❌ Invalid timeout value. Please enter a number in seconds.")

    else:
        embed = discord.Embed(title="😴 AFK Command Help", color=0xffaa00)
        embed.add_field(
            name="Commands",
            value=
            "`!afk status` - Show current AFK settings\n`!afk timeout <seconds>` - Set AFK timeout (Admin only)",
            inline=False)
        await ctx.send(embed=embed)


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def check_warnings(ctx):
    """Check current @everyone warnings (Admin only)"""
    if not everyone_warnings:
        await ctx.send("No active @everyone warnings.")
        return

    embed = discord.Embed(
        title="⚠️ Active @everyone Warnings",
        description="Users who have been warned for @everyone usage",
        color=0xffaa00)

    warning_text = ""
    for user_id, warning_time in everyone_warnings.items():
        try:
            user = bot.get_user(int(user_id))
            user_name = user.display_name if user else f"User ID: {user_id}"
            time_ago = discord.utils.format_dt(warning_time, style='R')
            warning_text += f"**{user_name}** - {time_ago}\n"
        except:
            warning_text += f"**Unknown User** - {user_id}\n"

    embed.add_field(name="Warned Users",
                    value=warning_text or "None",
                    inline=False)
    embed.set_footer(text="Next @everyone from these users = 24h timeout")

    await ctx.send(embed=embed)


@bot.command(name="clearwarnings")
@commands.has_permissions(manage_messages=True)
async def clear_warnings(ctx, user: Optional[discord.Member] = None):
    """Clear @everyone warnings for a user or all users (Admin only)"""
    if user:
        user_id = str(user.id)
        if user_id in everyone_warnings:
            del everyone_warnings[user_id]
            await ctx.send(
                f"✅ Cleared @everyone warning for {user.display_name}")
        else:
            await ctx.send(f"❌ {user.display_name} has no active warnings")
    else:
        count = len(everyone_warnings)
        everyone_warnings.clear()
        await ctx.send(f"✅ Cleared all {count} @everyone warnings")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kick a member from the server"""
    try:
        await member.kick(reason=f"Kicked by {ctx.author.display_name}: {reason}")
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server",
            color=0xff6b35
        )
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Kicked by", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this member!")
    except Exception as e:
        await ctx.send(f"❌ Error kicking member: {e}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban a member from the server"""
    try:
        await member.ban(reason=f"Banned by {ctx.author.display_name}: {reason}")
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server",
            color=0xff0000
        )
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Banned by", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member!")
    except Exception as e:
        await ctx.send(f"❌ Error banning member: {e}")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_member(ctx, user_id: int):
    """Unban a user by their ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author.display_name}")
        embed = discord.Embed(
            title="🔓 Member Unbanned",
            description=f"{user.mention} has been unbanned from the server",
            color=0x00ff00
        )
        embed.add_field(name="Unbanned by", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.NotFound:
        await ctx.send("❌ User not found or not banned!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unban users!")
    except Exception as e:
        await ctx.send(f"❌ Error unbanning user: {e}")


@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute_member(ctx, member: discord.Member, duration: int = 300, *, reason="No reason provided"):
    """Mute a member for specified duration (in seconds)"""
    if not MUTE_ROLE_ID:
        await ctx.send("❌ Mute role not configured! Please set MUTE_ROLE_ID.")
        return
    
    try:
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            await ctx.send("❌ Mute role not found!")
            return
            
        await member.add_roles(mute_role, reason=f"Muted by {ctx.author.display_name}: {reason}")
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted for {duration//60} minutes",
            color=0xffaa00
        )
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Muted by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Duration", value=f"{duration//60} minutes", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
        
        # Auto-unmute after duration
        await asyncio.sleep(duration)
        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason="Mute duration expired")
            await ctx.send(f"🔊 {member.mention} has been automatically unmuted!")
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute this member!")
    except Exception as e:
        await ctx.send(f"❌ Error muting member: {e}")


@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute_member(ctx, member: discord.Member):
    """Unmute a member"""
    if not MUTE_ROLE_ID:
        await ctx.send("❌ Mute role not configured!")
        return
    
    try:
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            await ctx.send("❌ Mute role not found!")
            return
            
        if mute_role not in member.roles:
            await ctx.send("❌ This member is not muted!")
            return
            
        await member.remove_roles(mute_role, reason=f"Unmuted by {ctx.author.display_name}")
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted",
            color=0x00ff00
        )
        embed.add_field(name="Unmuted by", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute this member!")
    except Exception as e:
        await ctx.send(f"❌ Error unmuting member: {e}")


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """Clear specified number of messages from the channel"""
    if amount < 1 or amount > 100:
        await ctx.send("❌ Please specify a number between 1 and 100!")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        embed = discord.Embed(
            title="🧹 Messages Cleared",
            description=f"Deleted {len(deleted)-1} messages",
            color=0x00ff00
        )
        embed.add_field(name="Cleared by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        # Send confirmation (will be auto-deleted after 5 seconds)
        msg = await ctx.send(embed=embed, delete_after=5.0)
        
        # Log to moderation channel
        mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")
    except Exception as e:
        await ctx.send(f"❌ Error clearing messages: {e}")


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_member(ctx, member: discord.Member, *, reason="No reason provided"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in WARNINGS_DB:
        WARNINGS_DB[user_id] = []
    
    warning = {
        "reason": reason,
        "moderator": ctx.author.id,
        "timestamp": discord.utils.utcnow().timestamp(),
        "guild_id": ctx.guild.id
    }
    
    WARNINGS_DB[user_id].append(warning)
    
    embed = discord.Embed(
        title="⚠️ Member Warned",
        description=f"{member.mention} has been warned",
        color=0xffaa00
    )
    embed.add_field(name="Reason", value=reason, inline=True)
    embed.add_field(name="Warned by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Total Warnings", value=len(WARNINGS_DB[user_id]), inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    await ctx.send(embed=embed)
    
    # Log to moderation channel
    mod_channel = bot.get_channel(MODERATION_LOG_CHANNEL_ID)
    if mod_channel:
        await mod_channel.send(embed=embed)
    
    # Auto-ban after 3 warnings
    if len(WARNINGS_DB[user_id]) >= 3:
        try:
            await member.ban(reason=f"Auto-banned after 3 warnings. Last warning: {reason}")
            await ctx.send(f"🔨 {member.mention} has been automatically banned after 3 warnings!")
        except discord.Forbidden:
            await ctx.send("❌ Cannot auto-ban member - insufficient permissions!")


@bot.command(name="checkwarnings")
@commands.has_permissions(manage_messages=True)
async def check_user_warnings(ctx, member: Optional[discord.Member] = None):
    """Check warnings for a member or show all warnings"""
    if member:
        user_id = str(member.id)
        if user_id not in WARNINGS_DB or not WARNINGS_DB[user_id]:
            await ctx.send(f"✅ {member.display_name} has no warnings!")
            return
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name}",
            color=0xffaa00
        )
        
        for i, warning in enumerate(WARNINGS_DB[user_id], 1):
            moderator = bot.get_user(warning["moderator"])
            mod_name = moderator.display_name if moderator else "Unknown"
            timestamp = dt.datetime.fromtimestamp(warning["timestamp"])
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {warning['reason']}\n**By:** {mod_name}\n**Date:** {timestamp.strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    else:
        # Show all warnings
        if not WARNINGS_DB:
            await ctx.send("✅ No warnings in the database!")
            return
        
        embed = discord.Embed(
            title="⚠️ All Warnings",
            color=0xffaa00
        )
        
        for user_id, warnings in WARNINGS_DB.items():
            if warnings:
                user = bot.get_user(int(user_id))
                user_name = user.display_name if user else f"User {user_id}"
                embed.add_field(
                    name=user_name,
                    value=f"{len(warnings)} warning(s)",
                    inline=True
                )
        
        await ctx.send(embed=embed)




@bot.command(name="serverinfo")
async def server_info(ctx):
    """Display detailed server information"""
    guild = ctx.guild
    
    # Calculate various statistics
    total_members = guild.member_count
    online_members = len([m for m in guild.members if m.status != discord.Status.offline])
    bot_count = len([m for m in guild.members if m.bot])
    human_count = total_members - bot_count
    
    # Channel counts
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    
    # Role count
    role_count = len(guild.roles)
    
    # Boost info
    boost_level = guild.premium_tier
    boost_count = guild.premium_subscription_count
    
    embed = discord.Embed(
        title=f"📊 {guild.name} Server Information",
        color=guild.owner.color if guild.owner else 0x00ff00
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    # General info
    embed.add_field(
        name="👑 Owner",
        value=guild.owner.mention if guild.owner else "Unknown",
        inline=True
    )
    embed.add_field(
        name="📅 Created",
        value=discord.utils.format_dt(guild.created_at, style='D'),
        inline=True
    )
    embed.add_field(
        name="🆔 Server ID",
        value=guild.id,
        inline=True
    )
    
    # Member stats
    embed.add_field(
        name="👥 Members",
        value=f"**Total:** {total_members:,}\n**Online:** {online_members:,}\n**Humans:** {human_count:,}\n**Bots:** {bot_count:,}",
        inline=True
    )
    
    # Channel stats
    embed.add_field(
        name="📝 Channels",
        value=f"**Text:** {text_channels}\n**Voice:** {voice_channels}\n**Categories:** {categories}",
        inline=True
    )
    
    # Other stats
    embed.add_field(
        name="🎭 Roles",
        value=f"{role_count} roles",
        inline=True
    )
    
    # Boost info
    if boost_count > 0:
        embed.add_field(
            name="🚀 Boost Status",
            value=f"Level {boost_level} ({boost_count} boosts)",
            inline=True
        )
    
    # Features
    if guild.features:
        features = [f"✅ {feature.replace('_', ' ').title()}" for feature in guild.features]
        embed.add_field(
            name="✨ Features",
            value="\n".join(features[:5]) + ("\n..." if len(features) > 5 else ""),
            inline=False
        )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    """Display detailed user information"""
    member = member or ctx.author
    
    # Calculate account age
    account_age = discord.utils.utcnow() - member.created_at
    account_age_days = account_age.days
    
    # Calculate server join age
    join_age = discord.utils.utcnow() - member.joined_at
    join_age_days = join_age.days
    
    # Get top role
    top_role = member.top_role
    
    # Get permissions
    key_permissions = []
    for perm, value in member.guild_permissions:
        if value and perm in ['administrator', 'manage_guild', 'manage_channels', 'manage_messages', 'ban_members', 'kick_members']:
            key_permissions.append(perm.replace('_', ' ').title())
    
    embed = discord.Embed(
        title=f"👤 {member.display_name}",
        color=member.color if member.color != discord.Color.default() else 0x00ff00
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    # Basic info
    embed.add_field(
        name="📝 Basic Info",
        value=f"**Name:** {member.name}\n**Display Name:** {member.display_name}\n**ID:** {member.id}",
        inline=True
    )
    
    # Account info
    embed.add_field(
        name="📅 Account Info",
        value=f"**Created:** {discord.utils.format_dt(member.created_at, style='D')}\n**Joined:** {discord.utils.format_dt(member.joined_at, style='D')}\n**Account Age:** {account_age_days} days",
        inline=True
    )
    
    # Status and activity
    status_emoji = {
        discord.Status.online: "🟢",
        discord.Status.idle: "🟡", 
        discord.Status.dnd: "🔴",
        discord.Status.offline: "⚫"
    }
    
    status_text = f"{status_emoji.get(member.status, '⚫')} {member.status.name.title()}"
    if member.activity:
        activity_text = f"**Activity:** {member.activity.name}"
    else:
        activity_text = "**Activity:** None"
    
    embed.add_field(
        name="🎯 Status",
        value=f"{status_text}\n{activity_text}",
        inline=True
    )
    
    # Roles
    roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
    roles_text = " ".join(roles[:10]) + ("..." if len(roles) > 10 else "")
    
    embed.add_field(
        name=f"🎭 Roles ({len(member.roles)-1})",
        value=roles_text or "No roles",
        inline=False
    )
    
    # Key permissions
    if key_permissions:
        embed.add_field(
            name="🔑 Key Permissions",
            value=", ".join(key_permissions),
            inline=True
        )
    
    # Top role
    embed.add_field(
        name="👑 Top Role",
        value=top_role.mention if top_role.name != "@everyone" else "No special role",
        inline=True
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="botinfo")
async def bot_info(ctx):
    """Display bot information and statistics, including a categorized command list"""
    # Calculate uptime
    uptime = discord.utils.utcnow() - bot.start_time if hasattr(bot, 'start_time') else dt.timedelta(0)
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    # System info
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    
    # Bot stats
    total_commands = len(bot.commands)
    total_guilds = len(bot.guilds)
    total_users = sum(len(guild.members) for guild in bot.guilds)
    
    embed = discord.Embed(
        title="🤖 Bot Information",
        description=f"**{bot.user.name}** - A Discord bot with AI capabilities",
        color=0x00ff00
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    # Bot info
    embed.add_field(
        name="📊 Bot Stats",
        value=f"**Servers:** {total_guilds:,}\n**Users:** {total_users:,}\n**Commands:** {total_commands}",
        inline=True
    )
    
    # System info
    embed.add_field(
        name="💻 System",
        value=f"**CPU:** {cpu_percent}%\n**Memory:** {memory_percent}%\n**Python:** {platform.python_version()}",
        inline=True
    )
    
    # Connection info
    embed.add_field(
        name="🌐 Connection",
        value=f"**Latency:** {round(bot.latency * 1000)}ms\n**Uptime:** {uptime_str}",
        inline=True
    )
    
    # Library info
    embed.add_field(
        name="📚 Libraries",
        value=f"**Discord.py:** {discord.__version__}\n**Platform:** {platform.system()}",
        inline=True
    )
    
    # Server stats
    embed.add_field(
        name="📈 Today's Stats",
        value=f"**Messages:** {server_stats['messages_today']:,}\n**Commands:** {server_stats['commands_used']:,}\n**Joins:** {server_stats['users_joined']:,}",
        inline=True
    )
    
    # --- Categorized Command List ---
    categories = {
        "🤖 AI": [
            "miku"
        ],
        "🎵 Music": [
            "play", "join", "leave", "skip", "queue", "np", "stop", "volume", "pause", "resume"
        ],
        "🛡️ Moderation": [
             "kick", "ban", "unban", "mute", "unmute", "clear", "warn", "checkwarnings", "warnings", "clearwarnings"
         ],
         "📊 Information": [
             "serverinfo", "userinfo", "botinfo", "roleinfo", "ping", "avatar", "stats", "vcstats", "voiceactivity", "servertime"
         ],
         "🎮 Fun": [
             "poll", "8ball", "coinflip", "dice", "match"
         ],
         "⏰ Utility": [
             "remind", "theme"
         ],
         "🎙️ Voice": [
             "voiceactivity", "vcstats", "afk"
         ],
        "📨 DM System": [
            "dm", "dmclose", "dmstatus", "dmhelp"
        ],
        "🔧 Admin": [
            "status", "cleanup", "setwelcome", "setmodlog", "setdmcategory", "setafk", "setaichannel", "settimezone", "setpersonality", "addpersonality", "viewpersonality", "resetpersonality"
        ],
        "📝 Help": [
            "helpme", "invite", "support"
        ],
        "\ud83d\udd27 Admin/Setup": [
            "setduochannel", "settriochannel", "setsquadchannel", "setteamchannel"
        ],
        "\ud83d\udc9e Matchmaking": [
            "match", "setmatchchannel"
        ],
    }
    
    for category, commands_list in categories.items():
        # Filter out commands that don't exist
        valid_commands = [cmd for cmd in commands_list if bot.get_command(cmd)]
        if valid_commands:
            embed.add_field(
                name=category,
                value=", ".join([f"`!{cmd}`" for cmd in valid_commands]),
                inline=False
            )
    
    embed.add_field(
        name="📝 Note",
        value="Some commands require specific permissions to use. Use `!helpme <command>` for details.",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    """Check bot latency"""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latency:** {round(bot.latency * 1000)}ms",
        color=0x00ff00
    )
    
    # Add different colors based on latency
    if bot.latency < 0.1:
        embed.color = 0x00ff00  # Green
        status = "🟢 Excellent"
    elif bot.latency < 0.2:
        embed.color = 0xffff00  # Yellow
        status = "🟡 Good"
    elif bot.latency < 0.5:
        embed.color = 0xff8800  # Orange
        status = "🟠 Fair"
    else:
        embed.color = 0xff0000  # Red
        status = "🔴 Poor"
    
    embed.add_field(name="Status", value=status, inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)


@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Show user's avatar"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"🖼️ {member.display_name}'s Avatar",
        color=member.color if member.color != discord.Color.default() else 0x00ff00
    )
    
    embed.set_image(url=member.display_avatar.url)
    embed.add_field(
        name="Links",
        value=f"[PNG]({member.display_avatar.url}) | [JPG]({member.display_avatar.replace(format='jpg').url}) | [WebP]({member.display_avatar.replace(format='webp').url})",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="roleinfo")
async def role_info(ctx, role: discord.Role):
    """Display detailed role information"""
    # Calculate member count
    member_count = len(role.members)
    
    # Get permissions
    permissions = []
    for perm, value in role.permissions:
        if value:
            permissions.append(perm.replace('_', ' ').title())
    
    embed = discord.Embed(
        title=f"🎭 {role.name}",
        description=role.mention,
        color=role.color if role.color != discord.Color.default() else 0x00ff00
    )

@bot.command(name="chatactivity", aliases=["chatleaderboard"])
async def chat_activity_leaderboard(ctx):
    """Show the weekly chat activity leaderboard."""
    guild_id = ctx.guild.id
    if guild_id not in chat_activity_weekly or not chat_activity_weekly[guild_id]:
        await ctx.send("No chat activity recorded this week!")
        return
    user_totals = {user_id: sum(days) for user_id, days in chat_activity_weekly[guild_id].items()}
    top_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard = ""
    for i, (user_id, total) in enumerate(top_users, 1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"
        leaderboard += f"{i}. **{name}** - {total} messages\n"
    embed = discord.Embed(
        title="💬 Weekly Chat Activity Leaderboard",
        description=leaderboard or "No data.",
        color=0x3498db
    )
    await ctx.send(embed=embed)
    
    # Basic info
    embed.add_field(
        name="📝 Basic Info",
        value=f"**ID:** {role.id}\n**Position:** {role.position}\n**Members:** {member_count:,}",
        inline=True
    )
    
    # Role info
    embed.add_field(
        name="🎨 Role Info",
        value=f"**Color:** {str(role.color)}\n**Hoisted:** {'Yes' if role.hoist else 'No'}\n**Mentionable:** {'Yes' if role.mentionable else 'No'}",
        inline=True
    )
    
    # Created info
    embed.add_field(
        name="📅 Created",
        value=discord.utils.format_dt(role.created_at, style='D'),
        inline=True
    )
    
    # Permissions
    if permissions:
        perms_text = ", ".join(permissions[:10]) + ("..." if len(permissions) > 10 else "")
        embed.add_field(
            name=f"🔑 Permissions ({len(permissions)})",
            value=perms_text,
            inline=False
        )
    
    # Members (if not too many)
    if member_count <= 20 and member_count > 0:
        members_text = ", ".join([member.display_name for member in role.members[:10]])
        if member_count > 10:
            members_text += f" and {member_count - 10} more..."
        embed.add_field(
            name="👥 Members",
            value=members_text,
            inline=False
        )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="poll")
async def create_poll(ctx, question: str, *options):
    """Create a poll with reactions"""
    if len(options) < 2:
        await ctx.send("❌ Please provide at least 2 options for the poll!")
        return
    
    if len(options) > 10:
        await ctx.send("❌ Maximum 10 options allowed!")
        return
    
    # Emoji reactions
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=0x00ff00
    )
    
    # Add options
    for i, option in enumerate(options):
        embed.add_field(
            name=f"{emojis[i]} {option}",
            value="\u200b",  # Invisible character for spacing
            inline=False
        )
    
    embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    # Send poll and add reactions
    poll_msg = await ctx.send(embed=embed)
    
    for i in range(len(options)):
        await poll_msg.add_reaction(emojis[i])


@bot.command(name="remind")
async def set_reminder(ctx, time: str, *, reminder: str):
    """Set a reminder. Usage: !remind 5m do homework"""
    # Parse time
    time_units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    try:
        # Extract number and unit
        import re
        match = re.match(r'(\d+)([smhd])', time.lower())
        if not match:
            await ctx.send("❌ Invalid time format! Use: 30s, 5m, 2h, 1d")
            return
        
        number = int(match.group(1))
        unit = match.group(2)
        seconds = number * time_units[unit]
        
        if seconds > 86400:  # Max 24 hours
            await ctx.send("❌ Maximum reminder time is 24 hours!")
            return
        
        # Send confirmation
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you about: **{reminder}**",
            color=0x00ff00
        )
        embed.add_field(name="Time", value=f"{number}{unit} from now", inline=True)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
        
        # Wait and send reminder
        await asyncio.sleep(seconds)
        
        reminder_embed = discord.Embed(
            title="⏰ Reminder!",
            description=f"**{reminder}**",
            color=0xffaa00
        )
        reminder_embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        reminder_embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
        reminder_embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(content=ctx.author.mention, embed=reminder_embed)
        
    except ValueError:
        await ctx.send("❌ Invalid time format! Use: 30s, 5m, 2h, 1d")


@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    """Ask the magic 8-ball a question"""
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes, definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}",
        color=0x9c27b0
    )
    embed.add_field(
        name="Answer",
        value=random.choice(responses),
        inline=False
    )
    embed.set_footer(text=f"Asked by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="coinflip")
async def coin_flip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "🪙"
    
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"The coin landed on: **{result}** {emoji}",
        color=0xffd700
    )
    embed.set_footer(text=f"Flipped by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="dice")
async def roll_dice(ctx, number: int = 6):
    """Roll a dice. Default is 6-sided"""
    if number < 2 or number > 100:
        await ctx.send("❌ Please choose a number between 2 and 100!")
        return
    
    result = random.randint(1, number)
    
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"You rolled a **{result}** on a {number}-sided die!",
        color=0x00ff00
    )
    embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)

class MatchView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.author = author
        self.matched = False

    @discord.ui.button(label="Accept Match", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author.id:
            await interaction.response.send_message("You can't match with yourself!", ephemeral=True)
            return

        if self.matched:
            await interaction.response.send_message("This match has already been accepted.", ephemeral=True)
            return

        self.matched = True
        button.disabled = True
        button.label = "Matched"
        await interaction.message.edit(view=self)

        guild = interaction.guild
        user1 = self.author
        user2 = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            user1: discord.PermissionOverwrite(connect=True, view_channel=True),
            user2: discord.PermissionOverwrite(connect=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True)
        }
        
        category = discord.utils.get(guild.categories, name="Matches")
        if not category:
            category = await guild.create_category("Matches")

        try:
            vc = await guild.create_voice_channel(f"💞 {user1.display_name} & {user2.display_name}", overwrites=overwrites, category=category)
            invite = await vc.create_invite(max_uses=2)

            await user1.send(f"You've been matched with {user2.mention}! Click here to join the voice channel: {invite.url}")
            await user2.send(f"You've matched with {user1.mention}! Click here to join the voice channel: {invite.url}")
            await interaction.response.send_message(f"{user2.mention} has accepted the match with {user1.mention}! A private voice channel has been created.", ephemeral=False)

        except Exception as e:
            logger.error(f"Error creating match channel: {e}")
            await interaction.response.send_message("Failed to create the match channel.", ephemeral=True)


GAME_LIMITS = {
    "valorant": 5,
    "peak": 4,
    "repo": 6,
    "brawlhalla": 8,
    "counter-strike 2": 5,
    "league of legends": 5,
    "apex legends": 3,
    "osu": 16,
    "agrou": 12
}

class RoleButton(discord.ui.Button):
    def __init__(self, game_name: str, has_role: bool):
        style = discord.ButtonStyle.success if has_role else discord.ButtonStyle.secondary
        emoji = "✅" if has_role else "❌"
        super().__init__(
            label=game_name.capitalize(),
            style=style,
            emoji=emoji,
            custom_id=f"role_button_{game_name}"
        )
        self.game_name = game_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        # Role names should be case-insensitive for matching but created with capitalization
        role_name = self.game_name.capitalize()

        # Find the role case-insensitively
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            try:
                role = await guild.create_role(name=role_name, reason="Auto-created game role")
            except discord.Forbidden:
                await interaction.followup.send("I lack permissions to create roles.", ephemeral=True)
                return

        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Toggled off via button")
                await interaction.followup.send(f"❌ Role '{role_name}' removed.", ephemeral=True)
            else:
                await member.add_roles(role, reason="Toggled on via button")
                await interaction.followup.send(f"✅ Role '{role_name}' added.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I can't modify your roles. Please check my role is above the game roles and that I have the 'Manage Roles' permission.", ephemeral=True)
            return

        # Re-create the view to update the buttons for the user who interacted
        view = RoleButtonView(member)
        await interaction.edit_original_response(view=view)

class RoleButtonView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        # Store role names in lowercase for case-insensitive comparison
        member_role_names = {role.name.lower() for role in member.roles}

        for game in GAME_LIMITS.keys():
            # Compare game name (already lowercase) with member's roles (also lowercase)
            has_role = game in member_role_names
            self.add_item(RoleButton(game_name=game, has_role=has_role))

@bot.command(name="gameroles", help="Displays an interactive embed for self-assigning game roles.")
async def gameroles(ctx):
    """Sends a message with buttons for self-assigning game roles."""
    embed = discord.Embed(
        title="🎮 Game Role Assignment",
        description="Click the buttons below to get roles for the games you play. This helps others find teammates!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Your roles will be updated automatically.")
    
    view = RoleButtonView(ctx.author)
    # Send as an ephemeral message so it's only visible to the user
    await ctx.send(embed=embed, view=view, ephemeral=True)

class LobbyView(discord.ui.View):
    def __init__(self, author, game, vc):
        super().__init__(timeout=3600)
        self.author = author
        self.game = game.lower()
        self.limit = GAME_LIMITS.get(self.game, 2)
        self.players = [author]
        self.message = None
        self.vc = vc

    async def update_embed(self, interaction: discord.Interaction):
        player_mentions = "\n".join([p.mention for p in self.players])
        embed = discord.Embed(
            title=f"✨ {self.game.capitalize()} Lobby ✨",
            description=f"**Players ({len(self.players)}/{self.limit})**:\n{player_mentions}\n\nVoice Channel: {self.vc.mention}",
            color=0x2ecc71
        )
        embed.set_footer(text=f"Lobby created by {self.author.display_name}")
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, emoji="✅")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("You are already in the lobby.", ephemeral=True)
        
        if len(self.players) >= self.limit:
            return await interaction.response.send_message("This lobby is full.", ephemeral=True)

        self.players.append(interaction.user)
        if interaction.user.voice:
            moved = False
            for attempt in range(3):
                try:
                    await interaction.user.move_to(self.vc)
                    moved = True
                    break
                except discord.DiscordServerError:
                    await asyncio.sleep(1 + attempt) # Exponential backoff
                except (discord.Forbidden, discord.HTTPException):
                    # Permissions error, no point in retrying
                    break

            if not moved:
                for attempt in range(3):
                    try:
                        await interaction.followup.send("I couldn't move you to the voice channel. Please check my permissions.", ephemeral=True)
                        break
                    except discord.DiscordServerError:
                        await asyncio.sleep(1 + attempt)
                    except discord.HTTPException:
                        break

        await self.update_embed(interaction)

        if len(self.players) == self.limit:
            await self.start_match(interaction)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, emoji="❌")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in this lobby.", ephemeral=True)
        
        if interaction.user == self.author:
            return await interaction.response.send_message("The lobby creator cannot leave. Use Cancel instead.", ephemeral=True)

        self.players.remove(interaction.user)
        await self.update_embed(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the lobby creator can cancel.", ephemeral=True)

        await self.vc.delete(reason="Lobby cancelled by host.")

        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(title="Lobby Cancelled", description="This lobby has been cancelled by the creator.", color=0xe74c3c)
        await interaction.message.edit(embed=embed, view=self)
        self.stop()

    async def start_match(self, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True
        
        await self.vc.edit(name=f"✨ {self.game.capitalize()} Match")

        embed = discord.Embed(title="Match Starting!", description=f"The lobby is full! The match is starting in {self.vc.mention}", color=0x3498db)
        await interaction.message.edit(embed=embed, view=self)
        self.stop()

@bot.command(name="match")
async def match(ctx, game: str):
    """Creates a matchmaking lobby for a specific game."""
    settings = get_guild_settings(ctx.guild.id)
    match_channel_id = settings.get("match_channel_id")

    if not match_channel_id or ctx.channel.id != match_channel_id:
        return await ctx.send(f"This command can only be used in the designated match channel.")

    game_name = game.lower()
    if game_name not in GAME_LIMITS:
        return await ctx.send(f"❌ Invalid game. Supported games: {', '.join(GAME_LIMITS.keys())}")

    # Create the voice channel immediately
    guild = ctx.guild
    limit = GAME_LIMITS.get(game_name, 2)
    category = discord.utils.get(guild.categories, name="Matches")
    if not category:
        category = await guild.create_category("Matches")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        ctx.author: discord.PermissionOverwrite(connect=True, view_channel=True),
        guild.me: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True)
    }

    try:
        vc = await guild.create_voice_channel(
            f"✨ {game_name.capitalize()} Lobby", 
            overwrites=overwrites, 
            category=category,
            user_limit=limit
        )
        if ctx.author.voice:
            await ctx.author.move_to(vc)
    except Exception as e:
        logger.error(f"Failed to create lobby VC: {e}")
        return await ctx.send("❌ Could not create the lobby voice channel. Check my permissions.")

    view = LobbyView(ctx.author, game_name, vc)
    
    player_mentions = "\n".join([p.mention for p in view.players])
    embed = discord.Embed(
        title=f"✨ {game_name.capitalize()} Lobby ✨",
        description=f"**Players ({len(view.players)}/{view.limit})**:\n{player_mentions}\n\nVoice Channel: {vc.mention}",
        color=0x2ecc71
    )
    embed.set_footer(text=f"Lobby created by {ctx.author.display_name}")
    
    # Game Role Pinging
    ping_content = None
    game_role = discord.utils.get(ctx.guild.roles, name=game_name.capitalize())
    if game_role:
        ping_content = game_role.mention

    message = await ctx.send(content=ping_content, embed=embed, view=view)
    view.message = message

    # Move the host into the newly created voice channel
    if ctx.author.voice:
        try:
            await ctx.author.move_to(vc)
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Could not move host {ctx.author.display_name} to VC: {e}")
            await ctx.send("I couldn't move you to the voice channel. Please check my permissions.", delete_after=10)


# Set timezone for Nepal
nepal_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=45))

@tasks.loop(time=datetime.time(hour=4, minute=0, tzinfo=nepal_tz))
async def daily_role_reset():
    """Runs daily at 4 AM UTC to remove all game roles from members."""
    logger.info("Starting daily role reset...")
    game_role_names = [game.capitalize() for game in GAME_LIMITS.keys()]

    for guild in bot.guilds:
        roles_to_remove = [role for role_name in game_role_names if (role := discord.utils.get(guild.roles, name=role_name))]

        if not roles_to_remove:
            continue

        for member in guild.members:
            member_roles_to_remove = [role for role in member.roles if role in roles_to_remove]
            if member_roles_to_remove:
                try:
                    await member.remove_roles(*member_roles_to_remove, reason="Daily game role reset")
                    logger.info(f"Removed roles from {member.display_name} in {guild.name}")
                except discord.Forbidden:
                    logger.warning(f"Could not remove roles from {member.display_name} in {guild.name} (Forbidden)")
                except discord.HTTPException as e:
                    logger.error(f"Failed to remove roles from {member.display_name} in {guild.name}: {e}")
    logger.info("Daily role reset finished.")

@bot.command(name="setassignroles")
@commands.has_permissions(administrator=True)
async def set_assign_roles_channel(ctx):
    """Sets the channel for the self-assignable roles message."""
    embed = discord.Embed(
        title="✨ Assign Game Roles ✨",
        description="Select the games you want to be notified for. You can select multiple.",
        color=0x5865F2
    )
    # We pass the member so the initial view is rendered correctly for them
    view = RoleButtonView(ctx.author)
    message = await ctx.send(embed=embed, view=view)
    
    # Store message and channel ID for persistence
    settings = get_guild_settings(ctx.guild.id)
    settings['assign_roles_channel_id'] = ctx.channel.id
    settings['assign_roles_message_id'] = message.id
    update_guild_settings(ctx.guild.id, settings)
    
    await ctx.message.delete() # Clean up the command message

@bot.command(name="helpme")
async def help_command(ctx, command_name: Optional[str] = None):
    """Show help for commands"""
    if command_name:
        # Show help for specific command
        command = bot.get_command(command_name)
        if not command:
            await ctx.send(f"❌ Command `{command_name}` not found!")
            return
        
        embed = discord.Embed(
            title=f"📖 Help: {command.name}",
            description=command.help or "No description available",
            color=0x00ff00
        )
        
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=True)
        
        if hasattr(command, "usage") and command.usage:
            embed.add_field(name="Usage", value=f"!{command.name} {command.usage}", inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        # Show general help
        embed = discord.Embed(
            title="🤖 Bot Commands",
            description="Here are the available commands. Use `!helpme <command>` for detailed help.",
            color=0x00ff00
        )
        
        # Categorize commands
        categories = {
            "🤖 AI": ["miku"],
            "🎵 Music": ["play", "join", "leave", "skip", "queue", "np", "stop", "volume", "pause", "resume"],
            "🛡️ Moderation": ["kick", "ban", "unban", "mute", "unmute", "clear", "warn", "checkwarnings"],
            "📊 Information": ["serverinfo", "userinfo", "botinfo", "roleinfo", "ping", "avatar"],
            "🎮 Fun": ["poll", "8ball", "coinflip", "dice", "match"],
            "⏰ Utility": ["remind", "theme"],
            "🎙️ Voice": ["voiceactivity", "vcstats", "afk"],
            "📨 DM System": ["dm", "dmclose", "dmstatus", "dmhelp"],
            "🔧 Admin": ["status", "cleanup", "warnings", "clearwarnings", "setpersonality", "addpersonality", "viewpersonality", "resetpersonality"]
        }
        
        for category, commands in categories.items():
            # Filter out commands that don't exist
            valid_commands = [cmd for cmd in commands if bot.get_command(cmd)]
            if valid_commands:
                embed.add_field(
                    name=category,
                    value=", ".join([f"`!{cmd}`" for cmd in valid_commands]),
                    inline=False
                )
        
        embed.add_field(
            name="📝 Note",
            value="Some commands require specific permissions to use.",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)


@bot.command(name="invite")
async def invite_link(ctx):
    """Get the bot's invite link"""
    embed = discord.Embed(
        title="🔗 Invite Me!",
        description="Click the link below to add me to your server!",
        color=0x00ff00
    )
    
    # Generate invite link with recommended permissions
    permissions = discord.Permissions(
        send_messages=True,
        read_messages=True,
        manage_messages=True,
        manage_channels=True,
        kick_members=True,
        ban_members=True,
        manage_roles=True,
        view_audit_log=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        add_reactions=True,
        use_external_emojis=True,
        connect=True,
        speak=True,
        move_members=True,
        use_voice_activation=True
    )
    
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    embed.add_field(name="Invite Link", value=f"[Click here to invite me!]({invite_url})", inline=False)
    
    embed.add_field(
        name="Required Permissions",
        value="• Send Messages\n• Manage Messages\n• Manage Channels\n• Kick/Ban Members\n• Manage Roles\n• Connect to Voice",
        inline=True
    )
    
    embed.add_field(
        name="Features",
        value="• AI Chat Responses\n• Voice Channel Management\n• Auto-moderation\n• Fun Commands\n• Server Statistics",
        inline=True
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="support")
async def support_info(ctx):
    """Show support information"""
    embed = discord.Embed(
        title="🆘 Support",
        description="Need help with the bot? Here's how to get support:",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📖 Commands",
        value="Use `!helpme` to see all available commands\nUse `!helpme <command>` for detailed help",
        inline=False
    )
    
    embed.add_field(
        name="🔗 Links",
        value="• [Discord.py Documentation](https://discordpy.readthedocs.io/)\n• [Discord Developer Portal](https://discord.com/developers/applications)",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Common Issues",
        value="• **Bot not responding?** Check if it has the required permissions\n• **Commands not working?** Make sure you have the right permissions\n• **Voice channels not working?** Check bot's voice permissions",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="stats")
async def server_stats_command(ctx):
    """Show server statistics"""
    embed = discord.Embed(
        title="📊 Server Statistics",
        description=f"Statistics for {ctx.guild.name}",
        color=0x00ff00
    )
    
    # Today's stats
    embed.add_field(
        name="📈 Today's Activity",
        value=f"**Messages:** {server_stats['messages_today']:,}\n**Commands Used:** {server_stats['commands_used']:,}\n**Users Joined:** {server_stats['users_joined']:,}\n**Users Left:** {server_stats['users_left']:,}",
        inline=True
    )
    
    # Voice stats
    embed.add_field(
        name="🎙️ Voice Activity",
        value=f"**Active Channels:** {len(created_channels)}\n**Total Created:** {channel_stats['total_created']:,}",
        inline=True
    )
    
    # Bot stats
    embed.add_field(
        name="🤖 Bot Status",
        value=f"**Latency:** {round(bot.latency * 1000)}ms\n**Uptime:** {str(discord.utils.utcnow() - bot.start_time).split('.')[0] if hasattr(bot, 'start_time') else 'Unknown'}",
        inline=True
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


async def check_and_assign_roles(member: discord.Member, channels_created: int):
    """Check if user qualifies for auto-roles and assign them"""
    try:
        guild = member.guild

        for role_name, threshold in ROLE_THRESHOLDS.items():
            if channels_created >= threshold:
                # Check if role exists, create if not
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    try:
                        # Create role with appropriate color
                        color = 0x00ff00 if "Creator" in role_name else 0xff6b35 if "Master" in role_name else 0x9c27b0
                        role = await guild.create_role(
                            name=role_name,
                            color=discord.Color(color),
                            reason="Auto-role for voice channel activity")
                    except discord.Forbidden:
                        logger.error(f"Cannot create role: {role_name}")
                        continue

                # Assign role if user doesn't have it
                if role not in member.roles:
                    try:
                        await member.add_roles(role)

                        # Send congratulations message
                        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
                        if welcome_channel:
                            embed = discord.Embed(
                                title="🎉 Role Unlocked!",
                                description=
                                f"{member.mention} has earned the **{role_name}** role!",
                                color=role.color)
                            embed.add_field(
                                name="Achievement",
                                value=
                                f"Created {channels_created} voice channels",
                                inline=True)
                            embed.set_thumbnail(url=member.display_avatar.url)
                            await welcome_channel.send(embed=embed)

                        logger.info(
                            f"Assigned role {role_name} to {member.display_name}"
                        )
                    except discord.Forbidden:
                        logger.error(
                            f"Cannot assign role {role_name} to {member.display_name}"
                        )

        save_all_data()

    except Exception as e:
        logger.error(f"Error in role assignment: {e}")


async def heartbeat() -> None:
    while True:
        logger.info("Heartbeat - Bot is alive!")
        await asyncio.sleep(60)  # Log every minute


async def reset_voice_activity() -> None:
    while True:
        now = discord.utils.utcnow()
        next_midnight = now.replace(hour=0, minute=0, second=0,
                                    microsecond=0) + timedelta(days=1)
        await discord.utils.sleep_until(next_midnight)
        voice_activity_today.clear()
        logger.info("Reset voice activity data at midnight UTC")


async def reset_daily_stats() -> None:
    """Reset daily server statistics at midnight"""
    while True:
        now = discord.utils.utcnow()
        next_midnight = now.replace(hour=0, minute=0, second=0,
                                    microsecond=0) + timedelta(days=1)
        await discord.utils.sleep_until(next_midnight)
        
        # Reset server stats
        server_stats["messages_today"] = 0
        server_stats["commands_used"] = 0
        server_stats["users_joined"] = 0
        server_stats["users_left"] = 0
        
        # Clear message cooldowns
        message_cooldowns.clear()
        
        logger.info("Reset daily server statistics at midnight UTC")




# Category ID for DM channels
DM_CATEGORY_ID = 1363906960583557322
# Mapping: user_id -> channel_id
user_dm_channels = {}

async def get_or_create_dm_channel(guild, user):
    settings = get_guild_settings(guild.id)
    dm_category_id = settings.get("dm_category_id")
    if not dm_category_id:
        # Fallback: prompt admin if not set
        admin = discord.utils.get(guild.members, guild_permissions__administrator=True)
        if admin:
            try:
                await admin.send(f"❗ DM category is not configured for {guild.name}. Please set it up with `!setdmcategory`.")
            except:
                pass
        raise Exception("DM category not configured.")
    # Check if we already have a channel for this user
    if user.id in user_dm_channels:
        channel = guild.get_channel(user_dm_channels[user.id])
        if channel:
            return channel
    # Find by name in case mapping is lost
    category = guild.get_channel(dm_category_id)
    channel_name = f"dm-{user.display_name.lower().replace(' ', '-')[:20]}"
    for ch in category.text_channels:
        if ch.name == channel_name:
            user_dm_channels[user.id] = ch.id
            return ch
    # Create new channel
    overwrites = category.overwrites.copy() if hasattr(category, 'overwrites') else {}
    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"DM channel for {user.display_name} ({user.id})"
    )
    user_dm_channels[user.id] = channel.id
    save_all_data()
    return channel

@bot.command(name="dm")
@commands.has_permissions(manage_messages=True)
async def dm_user(ctx, user_input: str, *, message: str):
    """Send a DM to a user via the bot. Usage: !dm @user Your message here or !dm 123456789 Your message here"""
    try:
        user = None
        if user_input.isdigit():
            try:
                user = await bot.fetch_user(int(user_input))
                member = ctx.guild.get_member(user.id)
                if not member:
                    await ctx.send(f"❌ User with ID {user_input} is not a member of this server!")
                    return
            except discord.NotFound:
                await ctx.send(f"❌ User with ID {user_input} not found!")
                return
            except Exception as e:
                await ctx.send(f"❌ Error fetching user: {e}")
                return
        else:
            try:
                user_id = user_input.strip('<@!>')
                if user_id.isdigit():
                    user = await bot.fetch_user(int(user_id))
                    member = ctx.guild.get_member(user.id)
                    if not member:
                        await ctx.send(f"❌ User with ID {user_id} is not a member of this server!")
                        return
                else:
                    await ctx.send("❌ Invalid user format! Use @user or user ID")
                    return
            except Exception as e:
                await ctx.send(f"❌ Error parsing user: {e}")
                return
        # Send plain message to user
        await user.send(message)
        # Get or create the DM channel for this user
        dm_channel = await get_or_create_dm_channel(ctx.guild, user)
        await dm_channel.send(f"Staff: {message}")
        active_dm_conversations[user.id] = {
            "channel_id": dm_channel.id,
            "moderator_id": ctx.author.id,
            "start_time": discord.utils.utcnow().timestamp(),
            "last_message": message
        }
        await ctx.send(f"Message sent to {user.display_name}. Conversation in {dm_channel.mention}", allowed_mentions=discord.AllowedMentions.none())
        save_all_data()
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot send DM to {user.display_name if user else 'user'}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ Error sending DM: {e}")


@bot.command(name="dmclose")
@commands.has_permissions(manage_messages=True)
async def close_dm_conversation(ctx, user_input: str):
    """Close an active DM conversation with a user. Usage: !dmclose @user or !dmclose 123456789"""
    if ctx.channel.id != DM_CATEGORY_ID:
        await ctx.send("❌ This command can only be used in the designated DM category!")
        return
    
    try:
        # Try to get user by ID first, then by mention
        user = None
        
        # Check if input is a user ID (numeric)
        if user_input.isdigit():
            try:
                user = await bot.fetch_user(int(user_input))
                # Check if user is in the guild
                member = ctx.guild.get_member(user.id)
                if not member:
                    await ctx.send(f"❌ User with ID {user_input} is not a member of this server!")
                    return
            except discord.NotFound:
                await ctx.send(f"❌ User with ID {user_input} not found!")
                return
            except Exception as e:
                await ctx.send(f"❌ Error fetching user: {e}")
                return
        else:
            # Try to parse as mention
            try:
                # Remove < > @ ! characters to get the ID
                user_id = user_input.strip('<@!>')
                if user_id.isdigit():
                    user = await bot.fetch_user(int(user_id))
                    member = ctx.guild.get_member(user.id)
                    if not member:
                        await ctx.send(f"❌ User with ID {user_id} is not a member of this server!")
                        return
                else:
                    await ctx.send("❌ Invalid user format! Use @user or user ID")
                    return
            except Exception as e:
                await ctx.send(f"❌ Error parsing user: {e}")
                return
        
        if user.id not in active_dm_conversations:
            await ctx.send(f"❌ No active conversation with {user.display_name}")
            return
        
        # Remove from active conversations
        del active_dm_conversations[user.id]
        
        # Send closing message to user
        try:
            close_embed = discord.Embed(
                title="🔒 Conversation Ended",
                description="This conversation with server staff has been closed.",
                color=0xff0000
            )
            close_embed.set_footer(text=f"Closed by {ctx.author.display_name}")
            close_embed.timestamp = discord.utils.utcnow()
            
            await user.send(embed=close_embed)
            
            # Confirm to staff (with silent mention)
            await ctx.send(f"✅ DM conversation with {user.display_name} has been closed.", allowed_mentions=discord.AllowedMentions.none())
            
            # Save data
            save_all_data()
            
        except discord.Forbidden:
            await ctx.send(f"✅ Conversation closed locally (could not notify {user.display_name})")
        except Exception as e:
            await ctx.send(f"❌ Error closing conversation: {e}")
            
    except Exception as e:
        await ctx.send(f"❌ Error processing command: {e}")


@bot.command(name="dmstatus")
@commands.has_permissions(manage_messages=True)
async def dm_status(ctx):
    """Show active DM conversations"""
    if ctx.channel.id != DM_CATEGORY_ID:
        await ctx.send("❌ This command can only be used in the designated DM category!")
        return
    
    if not active_dm_conversations:
        await ctx.send("📭 No active DM conversations")
        return
    
    embed = discord.Embed(
        title="📨 Active DM Conversations",
        description=f"Currently tracking {len(active_dm_conversations)} conversations",
        color=0x00ff00
    )
    
    for user_id, data in active_dm_conversations.items():
        try:
            user = bot.get_user(user_id)
            user_name = user.display_name if user else f"User {user_id}"
            
            moderator = bot.get_user(data["moderator_id"])
            mod_name = moderator.display_name if moderator else f"Staff {data['moderator_id']}"
            
            start_time = dt.datetime.fromtimestamp(data["start_time"])
            duration = discord.utils.utcnow() - start_time.replace(tzinfo=timezone.utc)
            
            embed.add_field(
                name=f"👤 {user_name}",
                value=f"**Moderator:** {mod_name}\n**Started:** {discord.utils.format_dt(start_time, style='R')}\n**Duration:** {str(duration).split('.')[0]}\n**Last Message:** {data['last_message'][:50]}...",
                inline=False
            )
        except Exception as e:
            embed.add_field(
                name=f"❌ User {user_id}",
                value=f"Error loading data: {e}",
                inline=False
            )
    
    embed.set_footer(text=f"Use !dmclose @user to close a conversation")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


@bot.command(name="dmhelp")
@commands.has_permissions(manage_messages=True)
async def dm_help(ctx):
    """Show detailed help for the DM system"""
    if ctx.channel.id != DM_CATEGORY_ID:
        await ctx.send("❌ This command can only be used in the designated DM category!")
        return
    
    embed = discord.Embed(
        title="📨 DM System Help",
        description="Staff DM system for communicating with server members",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🎯 Purpose",
        value="This system allows staff to send DMs to users and receive their replies in this category for easy moderation and support.",
        inline=False
    )
    
    embed.add_field(
        name="📝 Commands",
        value=(
            "**!dm @user <message>** - Send a DM to a user\n"
            "**!dm 123456789 <message>** - Send DM using user ID\n"
            "**!dmclose @user** - Close conversation with user\n"
            "**!dmclose 123456789** - Close conversation using user ID\n"
            "**!dmstatus** - Show active conversations\n"
            "**!dmhelp** - Show this help message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔄 How It Works",
        value=(
            "1. Staff sends DM using `!dm @user <message>` or `!dm 123456789 <message>`\n"
            "2. User receives DM with staff message\n"
            "3. User can reply to the DM\n"
            "4. User's reply appears in this category\n"
            "5. Staff can continue conversation or close it"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Important Notes",
        value=(
            "• Only works in designated DM category\n"
            "• Requires 'Manage Messages' permission\n"
            "• Users must have DMs enabled\n"
            "• Conversations persist until closed or bot restarts\n"
            "• All conversations are logged for moderation"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 Quick Actions",
        value=(
            "When you receive a reply, you can:\n"
            "• Use `!dm @user <message>` or `!dm 123456789 <message>` to reply\n"
            "• Use `!dmclose @user` or `!dmclose 123456789` to end conversation\n"
            "• Use `!dmstatus` to see all active conversations"
        ),
        inline=False
    )
    
    embed.set_footer(text="DM System - Staff Communication Tool")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)


# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI and MongoClient is not None:
    try:
        client = MongoClient(MONGO_URI)
        db = client["discord_bot"]
        # Test connection
        client.admin.command('ping')
        logger.info("✅ MongoDB connection established")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        db = None
else:
    logger.warning("⚠️ No MONGO_URI found or MongoClient unavailable, data persistence disabled")
    db = None

# --- Persistence Functions ---
def stringify_keys(d):
    """Recursively convert all dict keys to strings."""
    if isinstance(d, dict):
        return {str(k): stringify_keys(v) for k, v in d.items()}
    return d


def _save_voice_activity_today() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_today save")
        return
    try:
        db.voice_activity.delete_many({})
        if voice_activity_today:
            db.voice_activity.insert_one({"data": stringify_keys(voice_activity_today)})
        logger.debug("voice_activity_today saved successfully")
    except Exception as e:
        logger.error(f"Error saving voice_activity_today: {e}")

def _save_channel_stats() -> None:
    if db is None:
        logger.warning("Database not available, skipping channel_stats save")
        return
    try:
        db.channel_stats.delete_many({})
        if channel_stats:
            db.channel_stats.insert_one({"data": stringify_keys(channel_stats)})
        logger.debug("channel_stats saved successfully")
    except Exception as e:
        logger.error(f"Error saving channel_stats: {e}")

def _save_created_channels() -> None:
    if db is None:
        logger.warning("Database not available, skipping created_channels save")
        return
    try:
        db.created_channels.delete_many({})
        if created_channels:
            db.created_channels.insert_one({"ids": [str(k) for k in created_channels.keys()]})
        logger.debug("created_channels saved successfully")
    except Exception as e:
        logger.error(f"Error saving created_channels: {e}")

def _save_everyone_warnings() -> None:
    if db is None:
        logger.warning("Database not available, skipping everyone_warnings save")
        return
    try:
        db.everyone_warnings.delete_many({})
        if everyone_warnings:
            db.everyone_warnings.insert_one({"data": stringify_keys(everyone_warnings)})
        logger.debug("everyone_warnings saved successfully")
    except Exception as e:
        logger.error(f"Error saving everyone_warnings: {e}")

def _save_mention_spam_tracker() -> None:
    if db is None:
        logger.warning("Database not available, skipping mention_spam_tracker save")
        return
    try:
        tracker_data = [{"key": str(k), "timestamps": list(v)} for k, v in mention_spam_tracker.items()]
        db.mention_spam_tracker.delete_many({})
        if tracker_data:
            db.mention_spam_tracker.insert_many(tracker_data)
        logger.debug("mention_spam_tracker saved successfully")
    except Exception as e:
        logger.error(f"Error saving mention_spam_tracker: {e}")

def _save_mention_spam_warnings() -> None:
    if db is None:
        logger.warning("Database not available, skipping mention_spam_warnings save")
        return
    try:
        db.mention_spam_warnings.delete_many({})
        if mention_spam_warnings:
            db.mention_spam_warnings.insert_one({"data": stringify_keys(mention_spam_warnings)})
        logger.debug("mention_spam_warnings saved successfully")
    except Exception as e:
        logger.error(f"Error saving mention_spam_warnings: {e}")

def _save_warnings_db() -> None:
    if db is None:
        logger.warning("Database not available, skipping WARNINGS_DB save")
        return
    try:
        db.warnings_db.delete_many({})
        if WARNINGS_DB:
            db.warnings_db.insert_one({"data": stringify_keys(WARNINGS_DB)})
        logger.debug("WARNINGS_DB saved successfully")
    except Exception as e:
        logger.error(f"Error saving WARNINGS_DB: {e}")

def _save_server_stats() -> None:
    if db is None:
        logger.warning("Database not available, skipping server_stats save")
        return
    try:
        db.server_stats.delete_many({}) 
        if server_stats:
            db.server_stats.insert_one({"data": stringify_keys(server_stats)})
        logger.debug("server_stats saved successfully")
    except Exception as e:
        logger.error(f"Error saving server_stats: {e}")

def _save_user_activity() -> None:
    if db is None:
        logger.warning("Database not available, skipping user_activity save")
        return
    try:
        db.user_activity.delete_many({})
        if user_activity:
            db.user_activity.insert_one({"data": stringify_keys(user_activity)})
        logger.debug("user_activity saved successfully")
    except Exception as e:
        logger.error(f"Error saving user_activity: {e}")

def _save_message_cooldowns() -> None:
    if db is None:
        logger.warning("Database not available, skipping message_cooldowns save")
        return
    try:
        db.message_cooldowns.delete_many({})
        if message_cooldowns:
            db.message_cooldowns.insert_one({"data": stringify_keys(message_cooldowns)})
        logger.debug("message_cooldowns saved successfully")
    except Exception as e:
        logger.error(f"Error saving message_cooldowns: {e}")

def _save_active_dm_conversations() -> None:
    if db is None:
        logger.warning("Database not available, skipping active_dm_conversations save")
        return
    try:
        db.active_dm_conversations.delete_many({})
        if active_dm_conversations:
            dm_data = [{"user_id": str(k), "data": v} for k, v in active_dm_conversations.items()]
            if dm_data:
                db.active_dm_conversations.insert_many(dm_data)
        logger.debug("active_dm_conversations saved successfully")
    except Exception as e:
        logger.error(f"Error saving active_dm_conversations: {e}")

def _save_voice_activity_alltime() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_alltime save")
        return
    try:
        db.voice_activity_alltime.delete_many({})
        if voice_activity_alltime:
            db.voice_activity_alltime.insert_one({"data": stringify_keys(voice_activity_alltime)})
        logger.debug("voice_activity_alltime saved successfully")
    except Exception as e:
        logger.error(f"Error saving voice_activity_alltime: {e}")

def _save_voice_activity_weekly() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_weekly save")
        return
    try:
        db.voice_activity_weekly.delete_many({})
        if voice_activity_weekly:
            db.voice_activity_weekly.insert_one({"data": stringify_keys(voice_activity_weekly)})
        logger.debug("voice_activity_weekly saved successfully")
    except Exception as e:
        logger.error(f"Error saving voice_activity_weekly: {e}")

def _save_chat_activity_weekly() -> None:
    if db is None:
        logger.warning("Database not available, skipping chat_activity_weekly save")
        return
    try:
        db.chat_activity_weekly.delete_many({})
        if chat_activity_weekly:
            db.chat_activity_weekly.insert_one({"data": stringify_keys(chat_activity_weekly)})
        logger.debug("chat_activity_weekly saved successfully")
    except Exception as e:
        logger.error(f"Error saving chat_activity_weekly: {e}")

def save_all_data() -> None:
    global voice_activity_weekly
    if db is None:
        logger.warning("Database not available, skipping save")
        return
        
    try:
        _save_voice_activity_today()
        
        _save_channel_stats()
        
        _save_created_channels()
        
        _save_everyone_warnings()
        
        _save_mention_spam_tracker()
        
        _save_mention_spam_warnings()
        
        _save_warnings_db()
        
        _save_server_stats()
        
        _save_user_activity()
        
        _save_message_cooldowns()
            
        
        _save_active_dm_conversations()
        
        
        
        _save_voice_activity_alltime()
        
        _save_voice_activity_weekly()
        
        _save_chat_activity_weekly()
        
        logger.info("All data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}")


def _load_voice_activity_today() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_today load")
        return
    try:
        voice_activity_today.clear()
        doc = db.voice_activity.find_one()
        if doc:
            voice_activity_today.update(doc["data"])
        logger.debug("voice_activity_today loaded successfully")
    except Exception as e:
        logger.error(f"Error loading voice_activity_today: {e}")

def _load_channel_stats() -> None:
    if db is None:
        logger.warning("Database not available, skipping channel_stats load")
        return
    try:
        doc = db.channel_stats.find_one()
        if doc:
            channel_stats.clear()
            channel_stats.update(doc["data"])
        logger.debug("channel_stats loaded successfully")
    except Exception as e:
        logger.error(f"Error loading channel_stats: {e}")

def _load_created_channels() -> None:
    if db is None:
        logger.warning("Database not available, skipping created_channels load")
        return
    try:
        created_channels.clear()
        doc = db.created_channels.find_one()
        if doc:
            for cid in doc["ids"]:
                created_channels[int(cid)] = True
        logger.debug("created_channels loaded successfully")
    except Exception as e:
        logger.error(f"Error loading created_channels: {e}")

def _load_everyone_warnings() -> None:
    if db is None:
        logger.warning("Database not available, skipping everyone_warnings load")
        return
    try:
        everyone_warnings.clear()
        doc = db.everyone_warnings.find_one()
        if doc:
            everyone_warnings.update(doc["data"])
        logger.debug("everyone_warnings loaded successfully")
    except Exception as e:
        logger.error(f"Error loading everyone_warnings: {e}")

def _load_mention_spam_tracker() -> None:
    if db is None:
        logger.warning("Database not available, skipping mention_spam_tracker load")
        return
    try:
        mention_spam_tracker.clear()
        for doc in db.mention_spam_tracker.find():
            key = eval(doc["key"])
            mention_spam_tracker[key] = deque(doc["timestamps"], maxlen=MENTION_SPAM_THRESHOLD)
        logger.debug("mention_spam_tracker loaded successfully")
    except Exception as e:
        logger.error(f"Error loading mention_spam_tracker: {e}")

def _load_mention_spam_warnings() -> None:
    if db is None:
        logger.warning("Database not available, skipping mention_spam_warnings load")
        return
    try:
        mention_spam_warnings.clear()
        doc = db.mention_spam_warnings.find_one()
        if doc:
            mention_spam_warnings.update(doc["data"])
        logger.debug("mention_spam_warnings loaded successfully")
    except Exception as e:
        logger.error(f"Error loading mention_spam_warnings: {e}")

def _load_warnings_db() -> None:
    if db is None:
        logger.warning("Database not available, skipping WARNINGS_DB load")
        return
    try:
        WARNINGS_DB.clear()
        doc = db.warnings_db.find_one()
        if doc:
            WARNINGS_DB.update(doc["data"])
        logger.debug("WARNINGS_DB loaded successfully")
    except Exception as e:
        logger.error(f"Error loading WARNINGS_DB: {e}")

def _load_server_stats() -> None:
    if db is None:
        logger.warning("Database not available, skipping server_stats load")
        return
    try:
        server_stats.clear()
        doc = db.server_stats.find_one()
        if doc:
            server_stats.update(doc["data"])
        logger.debug("server_stats loaded successfully")
    except Exception as e:
        logger.error(f"Error loading server_stats: {e}")

def _load_user_activity() -> None:
    if db is None:
        logger.warning("Database not available, skipping user_activity load")
        return
    try:
        user_activity.clear()
        doc = db.user_activity.find_one()
        if doc:
            user_activity.update(doc["data"])
        logger.debug("user_activity loaded successfully")
    except Exception as e:
        logger.error(f"Error loading user_activity: {e}")

def _load_message_cooldowns() -> None:
    if db is None:
        logger.warning("Database not available, skipping message_cooldowns load")
        return
    try:
        message_cooldowns.clear()
        doc = db.message_cooldowns.find_one()
        if doc:
            message_cooldowns.update(doc["data"])
        logger.debug("message_cooldowns loaded successfully")
    except Exception as e:
        logger.error(f"Error loading message_cooldowns: {e}")


def _load_active_dm_conversations() -> None:
    if db is None:
        logger.warning("Database not available, skipping active_dm_conversations load")
        return
    try:
        active_dm_conversations.clear()
        for doc in db.active_dm_conversations.find():
            active_dm_conversations[int(doc["user_id"])] = doc["data"]
        logger.debug("active_dm_conversations loaded successfully")
    except Exception as e:
        logger.error(f"Error loading active_dm_conversations: {e}")

def _load_voice_activity_alltime() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_alltime load")
        return
    try:
        voice_activity_alltime.clear()
        doc = db.voice_activity_alltime.find_one()
        if doc:
            voice_activity_alltime.update(doc["data"])
        logger.debug("voice_activity_alltime loaded successfully")
    except Exception as e:
        logger.error(f"Error loading voice_activity_alltime: {e}")

def _load_voice_activity_weekly() -> None:
    if db is None:
        logger.warning("Database not available, skipping voice_activity_weekly load")
        return
    try:
        voice_activity_weekly.clear()
        doc = db.voice_activity_weekly.find_one()
        if doc:
            voice_activity_weekly.update(doc["data"])
        logger.debug("voice_activity_weekly loaded successfully")
    except Exception as e:
        logger.error(f"Error loading voice_activity_weekly: {e}")

def _load_chat_activity_weekly() -> None:
    if db is None:
        logger.warning("Database not available, skipping chat_activity_weekly load")
        return
    try:
        chat_activity_weekly.clear()
        doc = db.chat_activity_weekly.find_one()
        if doc:
            chat_activity_weekly.update(doc["data"])
        logger.debug("chat_activity_weekly loaded successfully")
    except Exception as e:
        logger.error(f"Error loading chat_activity_weekly: {e}")

def load_all_data() -> None:
    global voice_activity_weekly
    if db is None:
        logger.warning("Database not available, skipping load")
        return

        
    try:
        _load_voice_activity_today()
        
        _load_channel_stats()
        
        _load_created_channels()
        
        _load_everyone_warnings()
        
        _load_mention_spam_tracker()
        
        _load_mention_spam_warnings()
        
        _load_warnings_db()

        _load_server_stats()
        
        _load_user_activity()
        
        _load_message_cooldowns()
        
        _load_active_dm_conversations()
        
        _load_voice_activity_alltime()
        
        _load_voice_activity_weekly()
        
        _load_chat_activity_weekly()
        
        logger.info("All data loaded successfully")
    except Exception as e:
        logger.error(f"Error loading data on startup: {e}")

@bot.command(name="setmatchchannel")
@commands.has_permissions(administrator=True)
async def set_match_channel(ctx, channel: discord.TextChannel):
    set_guild_setting(ctx.guild.id, "match_channel_id", channel.id)
    await ctx.send(f"✅ Matchmaking channel set to {channel.mention}")

# --- Admin Setup Commands for Template Voice Channels ---
@bot.command(name="setduochannel")
@commands.has_permissions(administrator=True)
async def set_duo_channel(ctx, channel: discord.VoiceChannel):
    set_guild_setting(ctx.guild.id, "duo_channel_id", channel.id)
    await ctx.send(f"✅ Duo template channel set to {channel.mention}")

@bot.command(name="settriochannel")
@commands.has_permissions(administrator=True)
async def set_trio_channel(ctx, channel: discord.VoiceChannel):
    set_guild_setting(ctx.guild.id, "trio_channel_id", channel.id)
    await ctx.send(f"✅ Trio template channel set to {channel.mention}")

@bot.command(name="setsquadchannel")
@commands.has_permissions(administrator=True)
async def set_squad_channel(ctx, channel: discord.VoiceChannel):
    set_guild_setting(ctx.guild.id, "squad_channel_id", channel.id)
    await ctx.send(f"✅ Squad template channel set to {channel.mention}")

@bot.command(name="setteamchannel")
@commands.has_permissions(administrator=True)
async def set_team_channel(ctx, channel: discord.VoiceChannel):
    set_guild_setting(ctx.guild.id, "team_channel_id", channel.id)
    await ctx.send(f"✅ Team template channel set to {channel.mention}")

# --- Admin Setup Commands for Per-Guild Settings ---

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def set_welcome_channel(ctx, channel: discord.TextChannel):
    set_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command(name="setmodlog")
@commands.has_permissions(administrator=True)
async def set_modlog_channel(ctx, channel: discord.TextChannel):
    set_guild_setting(ctx.guild.id, "modlog_channel_id", channel.id)
    await ctx.send(f"✅ Moderation log channel set to {channel.mention}")

@bot.command(name="setdmcategory")
@commands.has_permissions(administrator=True)
async def set_dm_category(ctx, category_id: str):
    try:
        category_id_int = int(category_id)
    except ValueError:
        await ctx.send("❌ Please provide a valid numeric category ID.")
        return
    category = ctx.guild.get_channel(category_id_int)
    if not category:
        await ctx.send("❌ No channel or category found with that ID! Make sure you copied the **category** ID (not a text/voice channel).")
        return
    if not isinstance(category, discord.CategoryChannel):
        await ctx.send(f"❌ That ID is for a `{type(category).__name__}` not a category! Please provide a valid **category** ID.")
        return
    set_guild_setting(ctx.guild.id, "dm_category_id", category.id)
    await ctx.send(f"✅ DM category set to **{category.name}** (ID: `{category.id}`)")

@bot.command(name="setafk")
@commands.has_permissions(administrator=True)
async def set_afk_channel(ctx, channel: discord.VoiceChannel):
    set_guild_setting(ctx.guild.id, "afk_channel_id", channel.id)
    await ctx.send(f"✅ AFK channel set to {channel.mention}")

@bot.command(name="setaichannel")
@commands.has_permissions(administrator=True)
async def set_ai_channel(ctx, channel: discord.TextChannel):
    set_guild_setting(ctx.guild.id, "ai_channel_id", channel.id)
    await ctx.send(f"✅ AI/Miku channel set to {channel.mention}")

@bot.command(name="settimezone")
@commands.has_permissions(administrator=True)
async def set_timezone(ctx, *, country_or_tz: Optional[str] = None):
    if not country_or_tz or not isinstance(country_or_tz, str):
        await ctx.send("\u274c Please provide a valid country or timezone name.")
        return
    # Try as a timezone first
    try:
        pytz.timezone(country_or_tz)
        set_guild_setting(ctx.guild.id, "timezone", country_or_tz)
        await ctx.send(f"\u2705 Timezone set to `{country_or_tz}` for this server.")
        return
    except pytz.UnknownTimeZoneError:
        pass
    # Try as a country
    if CountryInfo is None:
        await ctx.send("\u274c Country-to-timezone feature is not available because the 'countryinfo' package is not installed.")
        return
    try:
        country = CountryInfo(country_or_tz)
        country_code = country.iso()['alpha2']
        timezones = pytz.country_timezones.get(country_code)
        if not timezones:
            await ctx.send("\u274c No timezone found for that country.")
            return
        # If multiple, pick the first (or prompt user for more advanced logic)
        tz = timezones[0]
        set_guild_setting(ctx.guild.id, "timezone", tz)
        await ctx.send(f"\u2705 Timezone for `{country_or_tz}` set to `{tz}` for this server.")
    except Exception:
        await ctx.send("\u274c Unknown country or timezone! Example: `Nepal`, `India`, `USA`, `Asia/Kathmandu`.")

@bot.command(name="servertime")
async def server_time(ctx):
    now_utc = discord.utils.utcnow().replace(tzinfo=pytz.utc)
    local_time = localize_time(now_utc, ctx.guild.id)
    await ctx.send(f"Server time: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

@bot.command(name="setpersonality")
@commands.has_permissions(administrator=True)
async def set_personality(ctx, *, prompt: str):
    """Overwrites the current AI personality for the server. (Admin only)"""
    if len(prompt) > 1500:
        await ctx.send("❌ Personality prompt is too long! Maximum 1500 characters.")
        return
    set_guild_setting(ctx.guild.id, "system_prompt", prompt)
    embed = discord.Embed(
        title="🤖 AI Personality Overwritten",
        description="The bot's personality for this server has been completely replaced.",
        color=0x00ff00
    )
    embed.add_field(name="New Personality Prompt", value=prompt)
    await ctx.send(embed=embed)

@bot.command(name="addpersonality")
@commands.has_permissions(administrator=True)
async def add_personality(ctx, *, prompt: str):
    """Adds a new trait to the current AI personality. (Admin only)"""
    current_prompt = get_system_prompt(ctx.guild.id)
    if len(current_prompt) + len(prompt) > 1500:
        await ctx.send("❌ Adding this trait would exceed the 1500 character limit.")
        return
    new_prompt = current_prompt + " " + prompt
    set_guild_setting(ctx.guild.id, "system_prompt", new_prompt)
    embed = discord.Embed(
        title="🤖 AI Personality Updated",
        description="A new trait has been added to the bot's personality.",
        color=0x00ff00
    )
    embed.add_field(name="Updated Personality Prompt", value=new_prompt)
    await ctx.send(embed=embed)
@bot.command(name="viewpersonality")
@commands.has_permissions(administrator=True)
async def view_personality(ctx):
    """Displays the current AI personality for the server. (Admin only)"""
    current_prompt = get_system_prompt(ctx.guild.id)
    embed = discord.Embed(
        title="🤖 Current AI Personality",
        description="This is the current personality prompt for the bot on this server.",
        color=0x00ff00
    )
    embed.add_field(name="Personality Prompt", value=current_prompt)
    await ctx.send(embed=embed)

# --- DM System ---
# Track active DM conversations
active_dm_conversations = {}  # {user_id: {"channel_id": channel_id, "moderator_id": moderator_id, "start_time": timestamp}}
@bot.command(name="resetpersonality")
@commands.has_permissions(administrator=True)
async def reset_personality(ctx):
    """Resets the AI personality to the default. (Admin only)"""
    set_guild_setting(ctx.guild.id, "system_prompt", DEFAULT_SYSTEM_PROMPT)
    embed = discord.Embed(
        title="🤖 AI Personality Reset",
        description="The bot's personality has been reset to the default.",
        color=0x00ff00
    )
    embed.add_field(name="Default Personality Prompt", value=DEFAULT_SYSTEM_PROMPT)
    await ctx.send(embed=embed)

# --- Music System ---
music_queues = {}  # {guild_id: [track_dict, ...]}
now_playing = {}   # {guild_id: track_dict}


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'cookiesfrombrowser': 'chrome', # Or 'firefox', 'edge', etc. Requires 'browser_cookie3' library.
        }
        ffmpeg_options = {
            'options': '-vn'
        }
        ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception as e:
            logger.error(f"Error extracting info for {url}: {e}")
            return None

        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

def get_weekday_index():
    return datetime.datetime.now().weekday()

def update_weekly_voice_time(guild_id, user_id, seconds):
    if guild_id not in voice_activity_weekly:
        voice_activity_weekly[guild_id] = {}
    if user_id not in voice_activity_weekly[guild_id]:
        voice_activity_weekly[guild_id][user_id] = [0] * 7
    idx = get_weekday_index()
    voice_activity_weekly[guild_id][user_id][idx] += seconds

async def reset_voice_activity_weekly() -> None:
    while True:
        now = discord.utils.utcnow()
        # Find next Monday 00:00 UTC
        days_ahead = 7 - now.weekday()  # 0=Monday
        if days_ahead == 0:
            days_ahead = 7
        next_week = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        await discord.utils.sleep_until(next_week)
        for guild in bot.guilds:
            guild_id = guild.id
            weekly = voice_activity_weekly.get(guild_id, {})
            if not weekly:
                continue
            # Find top user
            user_totals = {user_id: sum(days) for user_id, days in weekly.items()}
            if not user_totals:
                continue
            top_user_id = max(user_totals, key=user_totals.get)
            top_member = guild.get_member(int(top_user_id))
            if not top_member:
                continue
            # Role management
            role_name = "Voice Champion of the Week"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                role = await guild.create_role(name=role_name, color=discord.Color.gold(), reason="Weekly VC Champion")
            # Remove from all others
            for member in guild.members:
                if role in member.roles and member != top_member:
                    try:
                        await member.remove_roles(role, reason="New champion this week")
                    except Exception:
                        pass
            # Add to winner
            if role not in top_member.roles:
                try:
                    await top_member.add_roles(role, reason="Awarded for most VC hours this week")
                except Exception:
                    pass
            # Announce
            channel = guild.system_channel or guild.text_channels[0]
            if channel:
                try:
                    await channel.send(f"🏆 {top_member.mention} is the Voice Champion of the Week with {int(user_totals[top_user_id]//3600)}h {(int(user_totals[top_user_id])%3600)//60}m in VC!")
                except Exception:
                    pass
        # Reset weekly data
        voice_activity_weekly.clear()
        save_all_data()
        logger.info("Reset weekly voice activity and awarded champion role.")

token = os.getenv("TOKEN")
if not token:
    logger.error("❌ No TOKEN environment variable found!")
    logger.error("Please set your Discord bot token in the Secrets tab.")
else:
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token!")
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
