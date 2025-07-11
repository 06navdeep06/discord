# MIKU-BOT

A powerful, multi-purpose Discord bot with AI chat, moderation, voice channel management, utility, and fun features. Miku adapts to your server's timezone, supports country-based timezone setup, and offers a rich set of commands for both users and admins.

## Features
- **AI Chat**: Context-aware, timezone-aware AI chat using Fireworks Llama 4.
- **Voice Channel Management**: Auto-creates and manages voice channels for groups, squads, and teams.
- **Moderation Tools**: Kick, ban, mute, warn, auto-moderation, and more.
- **Fun & Games**: Polls, 8-ball, coin flip, dice, and more.
- **Reminders & Utilities**: Set reminders, check server/user info, and more.
- **Custom Personalities**: Switch between different bot characters.
- **DM System**: Staff-user DM relay system for support.
- **Per-Guild Timezone**: Set timezone by country or city for accurate time features.

## Setup Instructions

### 1. Clone the Repository
```sh
git clone https://github.com/yourusername/miku-bot.git
cd miku-bot
```

### 2. Install Dependencies
Make sure you have Python 3.8+ installed.
```sh
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file or set these variables in your environment:
- `TOKEN` - Your Discord bot token
- `MONGO_URI` - MongoDB connection string (for persistence)
- `FIREWORKS_API_KEY` - Fireworks AI API key

Example `.env`:
```
TOKEN=your_discord_token (of the bot )
MONGO_URI=your_mongodb_uri
FIREWORKS_API_KEY=your_fireworks_api_key
```

### 4. Run the Bot
```sh
python bb.py
```

## Command Overview

### Moderation
- `!kick`, `!ban`, `!unban`, `!mute`, `!unmute`, `!clear`, `!warn`, `!checkwarnings`, `!warnings`, `!clearwarnings`

### Information
- `!serverinfo`, `!userinfo`, `!botinfo`, `!roleinfo`, `!ping`, `!avatar`, `!stats`, `!vcstats`, `!voiceactivity`, `!servertime`

### Fun
- `!poll`, `!8ball`, `!coinflip`, `!dice`, `!miku`

### Utility
- `!remind`, `!theme`, `!shape`

### Voice
- `!voiceactivity`, `!vcstats`, `!afk`

### DM System
- `!dm`, `!dmclose`, `!dmstatus`, `!dmhelp`

### Admin/Setup
- `!status`, `!cleanup`, `!setwelcome`, `!setmodlog`, `!setdmcategory`, `!setafk`, `!setaichannel`, `!settimezone`

### Help
- `!helpme`, `!invite`, `!support`

## Timezone Setup
Admins can set the server timezone using either a timezone (e.g., `Asia/Kathmandu`) or a country name (e.g., `Nepal`, `India`, `USA`):
```
!settimezone Nepal
!settimezone Asia/Kathmandu
```

## License
[MIT License](LICENSE) (or your preferred license) 