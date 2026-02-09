# Claude Telegram Bridge 🤖

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A powerful bridge that allows you to interact with Anthropic's **Claude Code** CLI tool remotely via **Telegram**.

It uses pseudo-terminals (PTY) to emulate a real terminal session, rendering rich TUI interfaces (spinners, colors, progress bars) correctly in Telegram messages.

## ✨ Features

- **🛡️ Secure**: Restricted to your specific Telegram User ID. No one else can access your terminal.
- **🤫 Smart Silent Mode**: Automatically detects when Claude is "thinking" and only sends the final output, avoiding spam.
- **🌊 Streaming Mode**: Optional real-time updates if you want to see the progress live.
- **🌍 Multi-language**: Full support for English (🇺🇸), Spanish (🇪🇸), and Chinese (🇨🇳).
- **🖥️ TUI Support**: Correctly renders interactive elements using virtual screen emulation (`pyte`).
- **🔄 Session Management**: Pause, resume, and manage multiple Claude sessions.

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- A Telegram account
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (`npm install -g @anthropic-ai/claude-code`)

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/claude-telegram-bridge.git
cd claude-telegram-bridge
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

1.  Create a Telegram Bot via [@BotFather](https://t.me/BotFather) and get your **TOKEN**.
2.  Get your numerical User ID via [@userinfobot](https://t.me/userinfobot).
3.  Create your `.env` file:

```bash
cp .env.example .env
```

4.  Edit `.env` and fill in your details:

```env
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ALLOWED_USER_ID=123456789
BOT_LANGUAGE=en  # Optional: en, es, zh
```

### 4. Run

```bash
python3 telebot.py
```

## 🎮 Usage

Start a chat with your bot and send `/start`.

### Basic Commands

| Command | Description |
| :--- | :--- |
| `/start` | Initialize the bot connection. |
| `/help` | Show available commands. |
| `/mode` | Toggle between **Silent** (default) and **Streaming** mode. |
| `/screen` | Show the current raw content of the terminal screen. |
| `/status` | Show process PID and status. |
| `/enter` | Manually send an ENTER key (useful if UI gets stuck). |
| `/language` | Change language (`en`, `es`, `zh`). |

### Advanced Commands

| Command | Description |
| :--- | :--- |
| `/model <name>` | Change Claude's model (e.g., `/model haiku`). Restarts session. |
| `/restart` | Force restart the Claude process. |
| `/ctrlc` | Send a Ctrl+C interruption signal. |
| `/resume` | Resume the last session or search for one. |
| `/new` | Start a fresh session (clears context). |

## 🛠️ How it Works

1.  **PTY Spawning**: The script spawns `claude` inside a pseudo-terminal master/slave pair.
2.  **Virtual Screen**: It feeds the raw bytes from `stdout` into `pyte`, an in-memory VT100 emulator. This handles cursor movements, clear screen commands, and overwrites.
3.  **Smart Debounce**:
    - In **Silent Mode**, it waits for a pause in output (default 3s) before taking a "snapshot" of the virtual screen and sending it to Telegram.
    - In **Streaming Mode**, it updates every ~1s if there are changes.
4.  **HTML Rendering**: The screen content is converted to HTML `<pre>` tags to preserve monospace formatting in Telegram.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License

MIT
