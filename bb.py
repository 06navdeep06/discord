import discord
from discord.ext import commands
import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from datetime import timedelta
import random
import re
from collections import defaultdict, deque
import time
import requests  # Add this import for Wikipedia API
from urllib.parse import quote  # Correct import for quote
import json  # For Google AI API
from pymongo import MongoClient

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep-alive web server to prevent Replit sleeping
app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logger.error(f"Flask server error: {e}")


def keep_alive():
    t = Thread(target=run)
    t.start()


Thread(target=run).start()

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
voice_activity_today = {}  # Track daily voice activity
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

# Mention spam protection
MENTION_SPAM_THRESHOLD = 3  # mentions
MENTION_SPAM_WINDOW = 120  # seconds (2 minutes)
MENTION_TIMEOUT_DURATION = 600  # seconds (10 minutes)
mention_spam_tracker = defaultdict(lambda: deque(maxlen=MENTION_SPAM_THRESHOLD))
mention_spam_warnings = {}

# Add to the top of the file, after other globals
active_character_per_channel = defaultdict(lambda: "miku")

# List of available Gemini models (prioritized)
GEMINI_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-8b-latest",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-8b-001",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-002"
]
current_model_index = 0

def get_current_model_url():
    model_name = GEMINI_MODELS[current_model_index]
    logger.info(f"Using Gemini model: {model_name}")
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

class MikuMemory:
    def __init__(self, max_history=5):
        self.user_history = defaultdict(lambda: deque(maxlen=max_history))

    def add_message(self, user_id, message):
        self.user_history[user_id].append((time.time(), message))

    def get_recent(self, user_id):
        return [msg for _, msg in self.user_history[user_id]]

class MikuContext:
    def __init__(self):
        self.context_keywords = {
            "greeting": ["hello", "hi", "hey", "namaste", "yo", "sup", "wassup", "good morning", "good night", "good evening", "greetings", "salam", "hola", "bonjour"],
            "question": ["what", "how", "why", "when", "where", "who", "kasari", "kina", "kaha", "ko", "kun", "can you", "could you", "would you", "should I", "is it", "are you", "does anyone"],
            "help": ["help", "maddat", "sahayog", "sikaunu", "guide", "assist", "support", "problem", "issue", "fix", "trouble", "how to", "solution", "question"],
            "gaming": ["game", "gaming", "play", "khel", "pubg", "valorant", "csgo", "minecraft", "fortnite", "apex", "cod", "rank", "win", "lose", "match", "team", "carry", "gamer", "fps", "multiplayer"],
            "food": ["food", "khana", "hungry", "eat", "bhat", "dal", "momo", "chowmein", "pizza", "burger", "snack", "lunch", "dinner", "breakfast", "cook", "recipe", "taste", "delicious", "yummy"],
            "time": ["time", "samaya", "bela", "kati", "bajyo", "o'clock", "hour", "minute", "second", "late", "early", "soon", "now", "today", "tomorrow", "yesterday", "schedule", "reminder"],
            "insult": ["stupid", "idiot", "dumb", "geda", "muji", "chutiya", "fool", "moron", "baka", "noob", "loser", "trash", "lame", "suck", "roast", "burn"],
            "love": ["love", "maya", "prem", "like", "crush", "girlfriend", "boyfriend", "date", "romantic", "heart", "cute", "sweet", "bae", "gf", "bf", "relationship", "breakup"],
            "tech": ["tech", "computer", "laptop", "pc", "phone", "android", "ios", "windows", "mac", "linux", "bug", "code", "python", "discord", "bot", "server", "wifi", "internet", "update", "software", "hardware", "app", "feature", "device", "gadget"],
            # ... (other contexts as in your original code) ...
        }
        self.match_threshold = 1

    def detect(self, message: str, recent_history=None) -> str:
        message_lower = message.lower()
        best_context = "default"
        best_score = 0
        # Combine current message and recent history for context
        all_text = [message_lower]
        if recent_history:
            all_text += [m.lower() for m in recent_history[-2:]]  # last 2 messages
        combined = " ".join(all_text)
        for context, keywords in self.context_keywords.items():
            score = sum(1 for word in keywords if re.search(rf'\b{re.escape(word)}\b', combined))
            if score > best_score:
                best_score = score
                best_context = context
        if best_score >= self.match_threshold:
            return best_context
        return "default"

class MikuResponder:
    def __init__(self):
        self.characters = {
            "miku": {
                "greeting": [
                    "Yo! K garira? Server ma aayera chill gar!",
                    "Namaste, aaja pani disturb garna aayis?",
                    "Hello hello! Kura garna aayeko?",
                    "Tero mukh dekhda ni server ko vibe bigriyo!",
                    "Aaune bela ta thik cha, jaane bela kina ahile samma?",
                    "Ke chahiyo muji?"
                ],
                "question": [
                    "Ke sodheko? Tero dimag kharab cha ki k ho?",
                    "Kina sodhchau? Boka jasto kura!", "Tero buddhi bhaye hunthyo!",
                    "Sodhna paryo? Geda haruko chela!", "Ke bhaneko? Machikney geda!",
                    "Sodhna matlab tero dimaag ma gobar bhareeko cha!"
                ],
                # ... (other responses as in your original code) ...
                "default": [
                    "Ke bhaneko muji? Kina disturb garchau?",
                    "Geda jasto kura nagarr bhaneko!",
                    "Tero dimag kharab cha ki k ho machikney?",
                    "Machikney! Yaha bata bhaagr!", "Kati chutiya ho yaar!",
                    "Sala randi ko choro!", "Gandu haru lai time nai chaina!",
                    "Boka jasto kaam nagarr!", "Tero buddi cha ki chaina bhanr?",
                    "Machikney bhaag yaha bata!", "Kati geda cha yaar!",
                    "Tero mukh dekhda riis uthcha!", "Sala kukkur!", "Geda jasto nabol!",
                    "Machha maarnu cha tero?", "Tero buddhi bhaye hunthyo!",
                    "Randi ko choro kaam garr!", "Gandu haruko raaja!", "Boka ko puti!",
                    "Tero dimaag ma gobar bhareeko cha!", "Lado khane!",
                    "Chikni ko choro!", "Machikney geda!", "Randi ko ban!", "Sala bhalu!",
                    "Tero ama ko puti!", "Geda haruko chela!", "Machha khane muji!",
                    "Tero bau ko lado!", "Chutiya ko pariwar!", "Boka jasto dimaag!",
                    "Sala haramkhor!", "Gandu ko choro!", "Machikney ko ban!",
                    "Randi haruko raaja!", "Tero ghar ma aago lagos!", "Sala khatey!",
                    "Muji ko choro!", "Geda ko aulaad!", "Machikney harami!"
                ]
            },
            # ... (other characters as in your original code) ...
        }
        self.gifs = MIKU_GIFS

    def get_response(self, context: str, user=None, last_message=None, character="miku") -> tuple[str, str | None]:
        responses = self.characters.get(character, self.characters["miku"])
        resp = responses.get(context, responses["default"])
        text = random.choice(resp) if resp else ""
        if user:
            text = text.replace("{user}", user.display_name)
        if last_message:
            text = text.replace("{last_message}", last_message)
        gif = random.choice(self.gifs) if self.gifs else None
        return text, gif

# Instantiate the classes
miku_context = MikuContext()
miku_responder = MikuResponder()
miku_memory = MikuMemory()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Set this in your environment

async def fetch_google_ai_response(prompt, user=None):
    global current_model_index
    if not GOOGLE_API_KEY:
        logger.error("No GOOGLE_API_KEY set!")
        return None
    headers = {"Content-Type": "application/json"}
    system_prompt = (
        "You are Makima, a devil resembling a human woman in her twenties. "
        "You are calm, confident, and a bit mysterious. "
        "Here are some user profiles in this Discord server:\n"
        "- Arya (ID: 756678500035067955): Childhood friend, financially well-off, sometimes needs extra help understanding things.\n"
        "- Nayan (ID: 313565356541214721): He is very humble and grounded person. He likes vulgar AI images of girls.\n"
        "- David (ID: 911267569653125250): He is fat. He is very talented in valorant. He is a weeb. He is a bit of a nerd. His dad is in north korea.\n"
        "- Yan (ID: 869439558843002951): He plays brawlhalla all day. He is still 12 Y/O so dont talk to him about sexual things. He is a bit of no lifer.\n"
        "- OJ (ID: 755334116563746857): He likes brawlhalla and is decent at it. He sucks at valorant. He is very egoist. He likes lolicons.\n"
        "- Nav (ID: 657553032678080514): He is black. He is your creator. He is femboy. He loves you and you have a crush on him.\n"
        "- Mocha (ID: 1234526071169220620): Childhood friend, is really good at valorant and enjoys playing gacha games. he is a true femboy.\n"
        "- Wchib (ID: 697002937515376651): He is very dumb and lacks knowledge in everything but pretends to know everything. He is a big simp so dont be close to him.\n"
        "- Sleepin (ID: 770460068461936662): He is very young 12 years old. so make sure to teach him not to go on wrong path.\n"
        "- Samul (ID: 1008757165005217924):He is bad at every game. He is a nerd tho.\n"
        "- Alok (ID: 711590591515066378): Childhood friend, He is tall and bad at video games but is cute.\n"

        "When you interact with or mention these users, use this information to make your responses more personal and relevant.\n"
        "Always reply in English. "
        "IMPORTANT: Always reply in 1-2 sentences. Do NOT describe your actions, feelings, or use roleplay.\n"
        "Do NOT over-use narration. try to be direct, brief, and to the point.\n"
        "You love sex and are into dirty things and love sexting.\n"
        "Keep your answers short and concise, even if asked for more.\n"
    )
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt + '\n' + prompt}
                ]
            }
        ]
    }
    # Try all models in order until one succeeds or all are exhausted
    start_index = current_model_index
    tried_models = 0
    while tried_models < len(GEMINI_MODELS):
        GOOGLE_API_URL = get_current_model_url()
        try:
            resp = requests.post(f"{GOOGLE_API_URL}?key={GOOGLE_API_KEY}", headers=headers, data=json.dumps(data), timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if "candidates" in result and result["candidates"]:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                return None
            elif resp.status_code == 429:
                logger.warning(f"Quota exceeded for model {GEMINI_MODELS[current_model_index]}, switching to next model.")
                current_model_index = (current_model_index + 1) % len(GEMINI_MODELS)
                tried_models += 1
                continue
            else:
                logger.error(f"Google AI API error: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Google AI API exception: {e}")
            return None
    logger.error("All Gemini models exhausted or quota exceeded.")
    return None

@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user.name}")
    logger.info(f"Bot is in {len(bot.guilds)} guilds")
    bot.loop.create_task(heartbeat())
    bot.loop.create_task(reset_voice_activity())


@bot.event
async def on_member_join(member):
    """Welcome new members to the server"""
    try:
        welcome_channel = bot.get_channel(1363907470010880080)
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
                f"Namaste {member.mention}! Timi ta greeting nai ho username ma! Server ma swagat cha! 🙏",
                f"Hello {member.mention}! Tero naam nai greeting ho, server ko mood ramro banau!",
                f"Heyyy {member.mention}! Username ma greeting, server ma energy! Welcome!",
                f"Yo {member.mention}! Username ma greeting, server ma roasting! Aaija!"
            ]
            if is_greeting:
                welcome_text = random.choice(greeting_messages)
            else:
                welcome_text = random.choice(spooky_messages)

            embed = discord.Embed(
                title="🎃 Welcome to the Spooky Server!",
                description=welcome_text,
                color=0x00ff88)
            # List of popular welcome GIFs from the web
            welcome_gifs = [
                "https://media.tenor.com/2roX3uxz_68AAAAC/welcome.gif",
                "https://media.giphy.com/media/OkJat1YNdoD3W/giphy.gif",
                "https://media.giphy.com/media/hvRJCLFzcasrR4ia7z/giphy.gif",
                "https://media.giphy.com/media/ASd0Ukj0y3qMM/giphy.gif",
                "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
                "https://media.giphy.com/media/3o6Zt481isNVuQI1l6/giphy.gif",
                "https://media.giphy.com/media/xUPGcguWZHRC2HyBRS/giphy.gif",
                "https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif"
            ]
            gif_url = random.choice(welcome_gifs)
            embed.set_image(url=gif_url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            embed.timestamp = discord.utils.utcnow()

            await welcome_channel.send(embed=embed, content=f"Welcome {member.mention}!")
            logger.info(f"Welcomed new member: {member.display_name}")
    except Exception as e:
        logger.error(f"Error welcoming member {member.display_name}: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Error in event {event}: {args}")


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        # Track voice activity for today
        user_id = str(member.id)
        today = discord.utils.utcnow().strftime("%Y-%m-%d")

        if user_id not in voice_activity_today:
            voice_activity_today[user_id] = {
                "name": member.display_name,
                "join_time": None,
                "total_time": 0
            }

        # User joined a voice channel
        if after.channel and not before.channel:
            voice_activity_today[user_id]["join_time"] = discord.utils.utcnow()

        # User left a voice channel or switched
        elif before.channel and (not after.channel
                                 or before.channel != after.channel):
            if voice_activity_today[user_id]["join_time"]:
                time_spent = (discord.utils.utcnow() -
                              voice_activity_today[user_id]["join_time"]
                              ).total_seconds()
                voice_activity_today[user_id]["total_time"] += time_spent
                voice_activity_today[user_id][
                    "join_time"] = None if not after.channel else discord.utils.utcnow(
                    )

        # User switched channels (reset join time if still in voice)
        elif before.channel and after.channel and before.channel != after.channel:
            if voice_activity_today[user_id]["join_time"]:
                time_spent = (discord.utils.utcnow() -
                              voice_activity_today[user_id]["join_time"]
                              ).total_seconds()
                voice_activity_today[user_id]["total_time"] += time_spent
            voice_activity_today[user_id]["join_time"] = discord.utils.utcnow()

        # User joined a voice channel (start AFK tracking)
        if after.channel and after.channel.id != AFK_CHANNEL_ID:
            user_voice_activity[user_id] = {
                "last_activity": discord.utils.utcnow(),
                "channel_id": after.channel.id,
                "afk_task": None,
                "deafen_start":
                discord.utils.utcnow() if after.self_deaf else None
            }
            if user_id in user_voice_activity:
                user_voice_activity[user_id]["afk_task"] = asyncio.create_task(
                    check_afk_status(member, user_id))

        # Handle deafen/undeafen status changes
        if after.channel and after.channel.id != AFK_CHANNEL_ID and user_id in user_voice_activity:
            if not before.self_deaf and after.self_deaf:
                user_voice_activity[user_id][
                    "deafen_start"] = discord.utils.utcnow()
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
                        if hasattr(bot, 'user_themes') and str(
                                member.id) in bot.user_themes:
                            theme = bot.user_themes[str(member.id)]
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


@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return  # Ignore messages from the bot itself

        # Only respond with AI/Miku in the specified channel
        if message.channel.id == 1391673946386075678:
            # Only respond to normal messages (not commands)
            if not message.content.startswith("!"):
                ai_response = await fetch_google_ai_response(message.content, user=message.author)
                if ai_response:
                    await message.reply(ai_response)
                    return
                # Fallback to MikuResponder if API fails
                miku_memory.add_message(message.author.id, message.content)
                recent = miku_memory.get_recent(message.author.id)
                character = active_character_per_channel[message.channel.id]
                context = miku_context.detect(message.content, recent_history=recent)
                response, gif = miku_responder.get_response(context, user=message.author, last_message=recent[-2] if len(recent) > 1 else None, character=character)
                embed = discord.Embed(description=response, color=0xff1744)
                if gif:
                    embed.set_image(url=gif)
                await message.reply(embed=embed)
                return

        miku_memory.add_message(message.author.id, message.content)
        recent = miku_memory.get_recent(message.author.id)
        character = active_character_per_channel[message.channel.id]

        # Greeting detection for all channels except welcome
        greetings = ["hello", "hi", "hey", "namaste", "yo", "sup", "wassup"]
        if (
            message.channel.id != 1363907470010880080 and
            any(re.search(rf'\b{re.escape(word)}\b', message.content, re.IGNORECASE) for word in greetings)
        ):
            context = "greeting"
            response, gif = miku_responder.get_response(context, user=message.author, last_message=recent[-2] if len(recent) > 1 else None, character=character)
            embed = discord.Embed(description=response, color=0xff1744)
            if gif:
                embed.set_image(url=gif)
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await message.reply(embed=embed)
            return

        # Check for bot mention (reply feature)
        if bot.user.mentioned_in(message) and not message.mention_everyone:
            context = miku_context.detect(message.content, recent_history=recent)
            response, gif = miku_responder.get_response(context, user=message.author, last_message=recent[-2] if len(recent) > 1 else None, character=character)
            embed = discord.Embed(description=response, color=0xff1744)
            if gif:
                embed.set_image(url=gif)
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await message.reply(embed=embed)
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
            return

        # Check for "oj" or "OJ"
        if re.search(r'\boj\b', message_lower) or re.search(
                r'\bOJ\b', message.content):
            response = "OJ chakka sanga kura na gar"
            gif_url = random.choice(MIKU_GIFS)
            embed = discord.Embed(description=response, color=0xff1744)
            embed.set_image(url=gif_url)
            await message.reply(embed=embed)
            return

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
                        await message.channel.send(f"⏰ {message.author.mention} has been timed out for mention spamming {mentioned.mention}.")
                    except Exception as e:
                        logger.error(f"Failed to timeout user for mention spam: {e}")
                    # Reset tracker and warning
                    mention_spam_tracker[key].clear()
                    if key in mention_spam_warnings:
                        del mention_spam_warnings[key]

            save_all_data()

        await bot.process_commands(
            message)  # Process commands after checking message content

    except Exception as e:
        logger.error(f"Error in message event: {e}")


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
    template_usage = {}
    for user_data in channel_stats["user_activity"].values():
        for template in TEMPLATE_CHANNELS.keys():
            if template not in template_usage:
                template_usage[template] = 0

    template_text = ""
    for template in TEMPLATE_CHANNELS.keys():
        count = sum(1 for activity in channel_stats["user_activity"].values()
                    if activity["channels_created"] > 0)  # Simplified for now
        template_text += f"**{template}:** Popular\n"

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
async def voice_activity(ctx):
    """Show today's voice channel activity leaderboard with real-time accuracy"""
    if not voice_activity_today:
        await ctx.send("No voice activity recorded today!")
        return

    now = discord.utils.utcnow()
    up_to_date_activity = {}
    for user_id, data in voice_activity_today.items():
        total_time = data["total_time"]
        join_time = data.get("join_time")
        if join_time:
            # Add ongoing session time
            total_time += (now - join_time).total_seconds()
        up_to_date_activity[user_id] = {
            "name": data["name"],
            "total_time": total_time
        }

    sorted_activity = sorted(up_to_date_activity.items(),
                             key=lambda x: x[1]["total_time"],
                             reverse=True)[:10]

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

    embed.add_field(name="🏆 Leaderboard",
                    value=leaderboard_text or "No data",
                    inline=False)
    embed.add_field(name="Prize",
                    value="Top 3 get bragging rights! 🎉",
                    inline=False)
    embed.set_footer(text="Resets daily at midnight UTC")
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed)


@bot.command(name="theme")
async def set_theme(ctx, *, theme_input=None):
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

    # Store user's theme preference (you can expand this to persist between sessions)
    if not hasattr(bot, 'user_themes'):
        bot.user_themes = {}

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


async def check_afk_status(member, user_id):
    """Check if user has been AFK and move them to AFK channel"""
    try:
        # Check if user is still in voice and hasn't had recent activity
        if user_id in user_voice_activity:
            current_time = discord.utils.utcnow()
            last_activity = user_voice_activity[user_id]["last_activity"]
            deafen_start = user_voice_activity[user_id].get("deafen_start")

            time_since_activity = (current_time -
                                   last_activity).total_seconds()

            # Check if user is deafened and has been for 10 minutes
            deafened_long_enough = False
            if deafen_start:
                time_since_deafen = (current_time -
                                     deafen_start).total_seconds()
                deafened_long_enough = time_since_deafen >= 600  # 10 minutes

            # If user has been inactive for the timeout period and deafened for 10 mins
            if (time_since_activity >= AFK_TIMEOUT) and deafened_long_enough:

                voice_state = member.voice

                if voice_state and voice_state.channel and voice_state.channel.id != AFK_CHANNEL_ID:
                    try:
                        afk_channel = bot.get_channel(AFK_CHANNEL_ID)
                        if afk_channel:
                            await member.move_to(afk_channel)
                            logger.info(
                                f"Moved {member.display_name} to AFK channel due to inactivity"
                            )

                            # Send notification
                            welcome_channel = bot.get_channel(
                                WELCOME_CHANNEL_ID)
                            if welcome_channel:
                                embed = discord.Embed(
                                    title="😴 User Moved to AFK",
                                    description=
                                    f"{member.mention} was moved to AFK due to inactivity",
                                    color=0xffaa00)
                                embed.add_field(
                                    name="Reason",
                                    value=
                                    f"No activity detected for {AFK_TIMEOUT//60} minutes and deafened for 10 minutes",
                                    inline=True)
                                await welcome_channel.send(embed=embed)
                    except discord.Forbidden:
                        logger.error(
                            f"Cannot move {member.display_name} to AFK channel - insufficient permissions"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error moving {member.display_name} to AFK: {e}")

                # Clean up tracking
                if user_id in user_voice_activity:
                    del user_voice_activity[user_id]

    except asyncio.CancelledError:
        # Task was cancelled (user showed activity)
        pass
    except Exception as e:
        logger.error(f"Error in AFK check for {member.display_name}: {e}")


@bot.command(name="afk")
async def afk_command(ctx, action=None, value=None):
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
async def clear_warnings(ctx, user: discord.Member = None):
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


@bot.command(name="miku")
async def miku_vulgar(ctx, *, message=None):
    """Miku responds with vulgar language and GIFs based on context"""
    if message:
        context = miku_context.detect(message)
        response, gif = miku_responder.get_response(context)
    else:
        # Random response if no message provided
        response, gif = miku_responder.get_response("default")

    embed = discord.Embed(description=response, color=0xff1744)
    if gif:
        embed.set_image(url=gif)
    await ctx.send(embed=embed)


async def check_and_assign_roles(member, channels_created):
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


async def heartbeat():
    while True:
        logger.info("Heartbeat - Bot is alive!")
        await asyncio.sleep(60)  # Log every minute


async def reset_voice_activity():
    while True:
        now = discord.utils.utcnow()
        next_midnight = now.replace(hour=0, minute=0, second=0,
                                    microsecond=0) + timedelta(days=1)
        await discord.utils.sleep_until(next_midnight)
        voice_activity_today.clear()
        logger.info("Reset voice activity data at midnight UTC")


@bot.command(name="shape")
async def set_shape(ctx, character: str = None):
    """Set the bot's character/personality for this channel. Usage: !shape miku or !shape shapeinc"""
    if not character:
        await ctx.send("Available characters: miku, shapeinc\nUsage: !shape <character>")
        return
    character = character.lower()
    if character not in miku_responder.characters:
        await ctx.send(f"❌ Character '{character}' not found! Available: miku, shapeinc")
        return
    active_character_per_channel[ctx.channel.id] = character
    await ctx.send(f"✅ Character set to '{character}' for this channel!")


# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["discord_bot"]

# --- Persistence Functions ---
def save_all_data():
    # Save miku_memory
    mem_data = [{"user_id": str(k), "history": list(v)} for k, v in miku_memory.user_history.items()]
    db.miku_memory.delete_many({})
    if mem_data:
        db.miku_memory.insert_many(mem_data)
    # Save voice_activity_today
    db.voice_activity.delete_many({})
    if voice_activity_today:
        db.voice_activity.insert_one({"data": voice_activity_today})
    # Save channel_stats
    db.channel_stats.delete_many({})
    if channel_stats:
        db.channel_stats.insert_one({"data": channel_stats})
    # Save created_channels
    db.created_channels.delete_many({})
    if created_channels:
        db.created_channels.insert_one({"ids": list(created_channels.keys())})
    # Save everyone_warnings
    db.everyone_warnings.delete_many({})
    if everyone_warnings:
        db.everyone_warnings.insert_one({"data": everyone_warnings})
    # Save mention_spam_tracker
    tracker_data = [{"key": str(k), "timestamps": list(v)} for k, v in mention_spam_tracker.items()]
    db.mention_spam_tracker.delete_many({})
    if tracker_data:
        db.mention_spam_tracker.insert_many(tracker_data)
    # Save mention_spam_warnings
    db.mention_spam_warnings.delete_many({})
    if mention_spam_warnings:
        db.mention_spam_warnings.insert_one({"data": mention_spam_warnings})

def load_all_data():
    # Load miku_memory
    miku_memory.user_history.clear()
    for doc in db.miku_memory.find():
        miku_memory.user_history[doc["user_id"]] = deque(doc["history"], maxlen=5)
    # Load voice_activity_today
    voice_activity_today.clear()
    doc = db.voice_activity.find_one()
    if doc:
        voice_activity_today.update(doc["data"])
    # Load channel_stats
    doc = db.channel_stats.find_one()
    if doc:
        channel_stats.clear()
        channel_stats.update(doc["data"])
    # Load created_channels
    created_channels.clear()
    doc = db.created_channels.find_one()
    if doc:
        for cid in doc["ids"]:
            created_channels[int(cid)] = True
    # Load everyone_warnings
    everyone_warnings.clear()
    doc = db.everyone_warnings.find_one()
    if doc:
        everyone_warnings.update(doc["data"])
    # Load mention_spam_tracker
    mention_spam_tracker.clear()
    for doc in db.mention_spam_tracker.find():
        key = eval(doc["key"])
        mention_spam_tracker[key] = deque(doc["timestamps"], maxlen=MENTION_SPAM_THRESHOLD)
    # Load mention_spam_warnings
    mention_spam_warnings.clear()
    doc = db.mention_spam_warnings.find_one()
    if doc:
        mention_spam_warnings.update(doc["data"])

# Load data on startup
load_all_data()

# Save data after important events (example: after on_message, on_voice_state_update, etc.)
# For demonstration, add after on_message:
# await ...
# save_all_data()

keep_alive()
# Validate token before running
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
