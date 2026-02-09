# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Claude Telegram Bridge** allows users to interact with the Claude Code CLI tool remotely via Telegram. It acts as a bridge between a Telegram Bot and a pseudo-terminal (PTY) running the Claude process.

## Development Setup

1.  **Install Dependencies**: `pip install -r requirements.txt`
2.  **Configuration**: Copy `.env.example` to `.env` and fill in `TELEGRAM_TOKEN` and `ALLOWED_USER_ID`.
3.  **Run Bot**: `python3 telebot.py`

## Architecture

- **Entry Point**: `telebot.py` handles the Telegram bot logic and subprocess management.
- **Terminal Emulation**: Uses `pty` to spawn the `claude` CLI process and `pyte` to maintain an in-memory virtual screen. This ensures TUI output (cursor movements, overwrites) is rendered correctly into static text.
- **Output Handling**:
  - `read_from_pty`: Asynchronously reads raw bytes from the pseudo-terminal.
  - `send_buffered_output`: Periodically checks for screen updates using a smart debounce mechanism (Streaming vs Silent mode).
- **Input Handling**: User messages are written to the `master_fd` of the pty.
- **Localization**: Supports English, Spanish, and Chinese via the `TRANSLATIONS` dictionary.

## Key Features

- **Smart Silent Mode**: Only sends updates when Claude finishes generating output (avoids spam).
- **Streaming Mode**: Optional real-time updates.
- **Multi-language**: Dynamic language switching via `/language`.
- **Session Management**: Resume previous sessions or start new ones.
- **Admin Security**: Restricts access to a specific `ALLOWED_USER_ID`.

## Bot Commands

- `/start`: Start the bot
- `/help`: Show help message
- `/mode`: Toggle between Silent (smart updates) and Streaming (verbose) modes
- `/screen`: Show the current raw screen content
- `/status`: Show bot and process status
- `/language [code]`: Change language (en, es, zh)
- `/enter`: Send manual Enter key
- `/up`, `/down`: Send arrow keys
- `/resume [query]`: Resume a session
- `/new`: Start a new session
- Admin commands (hidden): `/restart`, `/model`, `/ctrlc`
