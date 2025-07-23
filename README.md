# Miku Bot: Your All-in-One Discord Server Assistant

Miku is a powerful, multi-purpose Discord bot designed to bring life and order to your server. Packed with features ranging from intelligent AI chat and robust moderation tools to dynamic voice channel management and engaging commands, Miku is the only bot you'll need. It's built to be highly configurable, with per-server settings for timezones, channels, and more, ensuring a tailored experience for your community.

## Key Features

- **💬 AI-Powered Chat**: Engage with a context-aware AI that understands your server's conversations. Powered by Fireworks Llama 4, Miku can switch between different personalities, from a helpful assistant to a sassy companion.
- **🎙️ Dynamic Voice Channels**: Miku automatically creates and deletes voice channels based on user activity. Set up templates for duos, trios, squads, and teams, and watch the bot manage the rest.
- **🛡️ Advanced Moderation**: Keep your server safe with a full suite of moderation commands, including kick, ban, mute, and warn. The bot also features auto-moderation to handle spam, excessive caps, and banned words.
- **🎉 Fun & Games**: Liven up your server with commands like `!poll`, `!8ball`, `!coinflip`, and `!dice`.
- **🛠️ Utility Belt**: A range of tools at your disposal, from setting reminders (`!remind`) to checking server statistics (`!serverinfo`) and user profiles (`!userinfo`).
- **🌍 Timezone Aware**: Configure the bot to your server's local timezone for accurate timestamps and scheduling. Miku can even determine the correct timezone from a country name.
- **🎵 Music Integration**: Play music from YouTube and Spotify with a full-featured music player, including queue management and playlist support.
- **💾 Data Persistence**: Miku uses MongoDB to save server settings, user warnings, activity stats, and more, ensuring your data is safe across bot restarts.

## Prerequisites

Before you begin, ensure you have the following:
- **Python 3.8+**
- A **Discord Bot Token** from the [Discord Developer Portal](https://discord.com/developers/applications)
- A **MongoDB Atlas** account and a connection URI for data persistence.
- A **Fireworks AI API Key** for the AI chat features.
- A **Spotify Developer App** with a Client ID and Secret for music features.

## Setup & Installation

1.  **Clone the Repository**
    ```sh
    git clone https://github.com/yourusername/miku-bot.git
    cd miku-bot
    ```

2.  **Create a Virtual Environment (Recommended)**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory and add the following variables:
    ```env
    TOKEN=your_discord_bot_token
    MONGO_URI=your_mongodb_connection_string
    FIREWORKS_API_KEY=your_fireworks_ai_api_key
    SPOTIFY_CLIENT_ID=your_spotify_client_id
    SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    ```

5.  **Run the Bot**
    ```sh
    python bb.py
    ```

## Initial Bot Setup (Admin Commands)

Once the bot is running and in your server, you'll need to configure it using these essential admin commands:

- **`!setwelcome #channel`**: Sets the channel for welcome messages.
- **`!setmodlog #channel`**: Sets the channel for moderation logs.
- **`!setafk #voice-channel`**: Sets the AFK voice channel.
- **`!setaichannel #channel`**: Designates a specific channel for AI chat.
- **`!settimezone <Country or Timezone>`**: Sets the server's timezone (e.g., `!settimezone Nepal` or `!settimezone Asia/Kathmandu`).
- **`!setdmcategory <Category ID>`**: Sets the category for the staff DM relay system.

### Voice Channel Templates
Set up the voice channels that Miku will use as templates for creating new ones:
```sh
!setduochannel #duo-vc
!settriochannel #trio-vc
!setsquadchannel #squad-vc
!setteamchannel #team-vc
```

## Commands

<details>
<summary><strong>🛡️ Moderation</strong></summary>

- `!kick @user [reason]`: Kicks a user.
- `!ban @user [reason]`: Bans a user.
- `!unban <user_id>`: Unbans a user.
- `!mute @user [duration_seconds] [reason]`: Mutes a user.
- `!unmute @user`: Unmutes a user.
- `!clear [amount]`: Deletes a number of messages.
- `!warn @user [reason]`: Warns a user.
- `!checkwarnings [@user]`: Checks warnings for a user or the server.
</details>

<details>
<summary><strong>📊 Information</strong></summary>

- `!serverinfo`: Displays server statistics.
- `!userinfo [@user]`: Shows information about a user.
- `!botinfo`: Provides bot statistics and system info.
- `!roleinfo @role`: Shows details about a role.
- `!ping`: Checks the bot's latency.
- `!avatar [@user]`: Displays a user's avatar.
- `!stats`: Shows server activity stats.
- `!vcstats`: Displays voice channel creation stats.
- `!voiceactivity [today]`: Shows the voice activity leaderboard.
- `!chatactivity`: Shows the weekly chat leaderboard.
</details>

<details>
<summary><strong>🎵 Music</strong></summary>

- `!play <url or search>`: Plays a song from YouTube or Spotify.
- `!join`: Makes the bot join your voice channel.
- `!leave`: Makes the bot leave the voice channel.
</details>

<details>
<summary><strong>🎮 Fun & Games</strong></summary>

- `!poll "Question" "Option 1" "Option 2"`: Creates a poll.
- `!8ball <question>`: Asks the magic 8-ball.
- `!coinflip`: Flips a coin.
- `!dice [sides]`: Rolls a die.
- `!miku [message]`: Interacts with the Miku personality.
</details>

<details>
<summary><strong>🛠️ Utility</strong></summary>

- `!remind <time> <message>`: Sets a reminder (e.g., `!remind 1h check on dinner`).
- `!theme [theme_name]`: Sets a theme for your next created voice channel.
- `!shape <personality>`: Changes the bot's AI personality for the channel (e.g., `!shape miku`).
</details>

<details>
<summary><strong>📨 DM Support System (Staff Only)</strong></summary>

- `!dm @user <message>`: Sends a direct message to a user through the bot.
- `!dmclose @user`: Closes an active DM conversation.
- `!dmstatus`: Shows all active DM conversations.
- `!dmhelp`: Provides detailed help for the DM system.
</details>

## AI Personalities

You can change the bot's behavior in a channel by switching its personality with the `!shape` command.
- **`miku`**: A sassy, vulgar, and unpredictable personality.
- **`shapeinc`**: A friendly, helpful, and professional assistant.

## Data Persistence

The bot uses a MongoDB database to store important data, including:
- Server settings (welcome channel, modlog, etc.)
- User warnings and moderation history
- Voice and chat activity statistics
- Created voice channel data
- Active DM conversations

This ensures that your configurations and user data are not lost when the bot restarts.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
