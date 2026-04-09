# <img src="https://em-content.zobj.net/source/microsoft-teams/363/sparkles_2728.png" width="30" height="30"> Meekly Discord Bot

Meekly is a high-performance, multipurpose Discord bot designed for security, moderation, and community engagement. Built with `discord.py` and modular architecture, it features advanced Anti-Nuke protection, a customizable Help system, and immersive Voice Management.

---

## 🚀 Key Features

*   🛡️ **Advanced Anti-Nuke**: State-of-the-art protection against server-wide malicious actions.
*   ⚖️ **Automated Moderation**: Keep your server safe with robust filters and logging.
*   🔊 **Voice Master**: Dynamic voice channel management for your community.
*   🤖 **AI Powered**: Integrated with OpenAI and gTTS for intelligent responses and voice interaction.
*   📊 **Statistics**: Real-time system and bot statistics using modern Discord UI components.
*   🎮 **Fun & Games**: Includes features like Chess and interactive utility commands.

---

## 🛠️ Technology Stack

- **Core**: Python 3.x, `discord.py` 2.4+
- **Database**: SQLite with `aiosqlite` for asynchronous data handling.
- **System**: Monitoring with `psutil`.
- **AI**: OpenAI API, Google TTS (`gtts`).
- **Music**: `Wavelink` (Lavalink integration).

---

## ⚙️ Setup & Installation

### 1. Requirements
Ensure you have Python 3.10 installed. 

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and add your bot token:
```env
TOKEN=your_discord_bot_token_here
```

### 4. Run the Bot
```bash
python main.py
```

---

## 🎨 UI & Aesthetics
The bot uses modern **Discord Components V2** (`LayoutView`, `Container`, `Section`) to provide a premium, clean, and interactive user interface.

---

## 🔒 Security Advisory
> [!IMPORTANT]
> To keep your bot safe, **NEVER** share your `.env` file or bot token. Ensure that `.env` and the `db/` folder are included in your `.gitignore` before pushing to public repositories.

---

## 👥 Developers
- **Not_Op_gamer404_YT** (Main Developer)
- **ray.dev** (Co-Developer)

---

## 🔗 Support & Links
- [YouTube](https://youtube.com/@CodeXDevs)
- [Support Server](https://discord.gg/codexdev)
- [Free Hosting](https://nexio.host/)
