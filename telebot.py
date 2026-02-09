import os
import asyncio
import pty
import subprocess
import select
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pyte
import html
from dotenv import load_dotenv
import locale

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
except ValueError:
    print("Error: ALLOWED_USER_ID must be an integer.")
    ALLOWED_USER_ID = 0

if not TELEGRAM_TOKEN or ALLOWED_USER_ID == 0:
    print("Error: TELEGRAM_TOKEN and ALLOWED_USER_ID must be set in .env file or environment variables.")
    # We won't exit here to allow importing for testing, but main will fail if called

# Command to execute claude
CLAUDE_COMMAND = ["claude"]

# Virtual screen configuration (cols, rows)
SCREEN_COLS = 120
SCREEN_ROWS = 40

# Wait times (in seconds) for message aggregation
DEBOUNCE_TIME = 1.0  # For streaming mode
IDLE_TIME_THRESHOLD = 3.0 # Idle time to consider finished (smart mode)
MAX_WAIT_TIME = 5.0  # Max wait time before sending in streaming mode

# --- GLOBAL STATE ---
master_fd = None
slave_fd = None
process = None
screen = pyte.Screen(SCREEN_COLS, SCREEN_ROWS)
stream = pyte.Stream(screen)
last_output_time = 0
last_sent_time = 0
STREAM_MODE = False  # False = Send only at end (Smart Mode) / True = Send constant updates
force_update_next = False # To force update after interactive commands

# --- LOCALIZATION ---
TRANSLATIONS = {
    "en": {
        "connected": "🚀 Claude Bridge Connected.\nUse /help to see commands.",
        "restarting": "🔄 Restarting Claude...",
        "restarted": "✅ Restarted.",
        "interrupt_sent": "keyboard_interrupt sent (Ctrl+C)",
        "enter_sent": "Enter sent (\\r)",
        "arrow_up": "⬆️",
        "arrow_down": "⬇️",
        "bot_status": "📊 **Bot Status**",
        "process_running": "🟢 Running",
        "process_stopped": "🔴 Stopped",
        "current_model": "Current Model",
        "pid": "PID",
        "last_output": "Last output received",
        "last_sent": "Last sent to Telegram",
        "seconds_ago": "s ago",
        "raw_screen": "📺 **Raw Screen**",
        "empty_screen": "[Empty Screen]",
        "resuming_last": "🔄 Resuming **last session**...",
        "listing_sessions": "📋 **Listing sessions**\nUse /up, /down and /enter to select, or copy ID to use in `/resume <id>`.",
        "resuming_session": "🔄 Searching and resuming session: `{}`...",
        "new_session": "🆕 Starting **new session**...",
        "specify_model": "⚠️ You must specify the model.\nOptions: {}\nExample: `/model haiku`",
        "invalid_model": "❌ Invalid model. Use: {}",
        "restarting_model": "🔄 Restarting Claude with model **{}**...",
        "restarted_model": "✅ Restarted in {} mode.",
        "available_commands": "🤖 **Available Commands**",
        "current_mode": "Current Mode",
        "mode_streaming": "🌊 Streaming",
        "mode_silent": "🤫 Silent",
        "basics_header": "📝 **Basics:**",
        "advanced_header": "\n⚠️ **Advanced:**",
        "help_footer": "\n_(Use `/help admin` for more commands)_",
        "access_denied": "⛔ Access denied to ID {}",
        "mode_changed": "Mode changed to: **{}**",
        "language_changed": "🌐 Language changed to: **{}**",
        "invalid_language": "❌ Invalid language. Available: {}",
        # Commands descriptions
        "cmd_start": "Start the bot",
        "cmd_help": "See this help",
        "cmd_mode": "Toggle Silent/Streaming mode",
        "cmd_screen": "View current screen (useful in silent mode)",
        "cmd_enter": "Send ENTER key",
        "cmd_arrows": "Navigation arrows (for menus)",
        "cmd_status": "Process status",
        "cmd_resume": "Resume session (last, search or list)",
        "cmd_new": "Start new session",
        "cmd_model": "Change model (restarts)",
        "cmd_restart": "Restart process",
        "cmd_ctrlc": "Send Interrupt (Ctrl+C)",
        "cmd_lang": "Change language (en, es, zh)"
    },
    "es": {
        "connected": "🚀 Puente Claude Conectado.\nUsa /help para ver comandos.",
        "restarting": "🔄 Reiniciando Claude...",
        "restarted": "✅ Reiniciado.",
        "interrupt_sent": "interrupción enviada (Ctrl+C)",
        "enter_sent": "Enter enviado (\\r)",
        "arrow_up": "⬆️",
        "arrow_down": "⬇️",
        "bot_status": "📊 **Estado del Bot**",
        "process_running": "🟢 Ejecutando",
        "process_stopped": "🔴 Detenido",
        "current_model": "Modelo Actual",
        "pid": "PID",
        "last_output": "Último output recibido",
        "last_sent": "Último envío a Telegram",
        "seconds_ago": "s atrás",
        "raw_screen": "📺 **Pantalla Cruda**",
        "empty_screen": "[Pantalla Vacía]",
        "resuming_last": "🔄 Resumiendo **última sesión**...",
        "listing_sessions": "📋 **Listando sesiones**\nUsa /up, /down y /enter para seleccionar, o copia el ID para usar en `/resume <id>`.",
        "resuming_session": "🔄 Buscando y resumiendo sesión: `{}`...",
        "new_session": "🆕 Iniciando **nueva sesión**...",
        "specify_model": "⚠️ Debes especificar el modelo.\nOpciones: {}\nEjemplo: `/model haiku`",
        "invalid_model": "❌ Modelo inválido. Usa: {}",
        "restarting_model": "🔄 Reiniciando Claude con modelo **{}**...",
        "restarted_model": "✅ Reiniciado en modo {}.",
        "available_commands": "🤖 **Comandos Disponibles**",
        "current_mode": "Modo Actual",
        "mode_streaming": "🌊 Streaming",
        "mode_silent": "🤫 Silencioso",
        "basics_header": "📝 **Básicos:**",
        "advanced_header": "\n⚠️ **Avanzados:**",
        "help_footer": "\n_(Usa `/help admin` para más comandos)_",
        "access_denied": "⛔ Acceso denegado al ID {}",
        "mode_changed": "Modo cambiado a: **{}**",
        "language_changed": "🌐 Idioma cambiado a: **{}**",
        "invalid_language": "❌ Idioma inválido. Disponibles: {}",
        # Descriptions
        "cmd_start": "Iniciar el bot",
        "cmd_help": "Ver esta ayuda",
        "cmd_mode": "Cambiar modo Silencioso/Streaming",
        "cmd_screen": "Ver pantalla actual (útil en modo silencioso)",
        "cmd_enter": "Enviar tecla ENTER",
        "cmd_arrows": "Flechas de navegación (para menús)",
        "cmd_status": "Estado del proceso",
        "cmd_resume": "Resumir sesión (última, búsqueda o lista)",
        "cmd_new": "Iniciar nueva sesión",
        "cmd_model": "Cambiar modelo (reinicia)",
        "cmd_restart": "Reiniciar proceso",
        "cmd_ctrlc": "Enviar Interrupción (Ctrl+C)",
        "cmd_lang": "Cambiar idioma (en, es, zh)"
    },
    "zh": {
        "connected": "🚀 Claude Bridge 已连接。\n使用 /help 查看命令。",
        "restarting": "🔄 正在重启 Claude...",
        "restarted": "✅ 已重启。",
        "interrupt_sent": "中断信号已发送 (Ctrl+C)",
        "enter_sent": "Enter 已发送 (\\r)",
        "arrow_up": "⬆️",
        "arrow_down": "⬇️",
        "bot_status": "📊 **Bot 状态**",
        "process_running": "🟢 运行中",
        "process_stopped": "🔴 已停止",
        "current_model": "当前模型",
        "pid": "PID",
        "last_output": "上次接收输出",
        "last_sent": "上次发送到 Telegram",
        "seconds_ago": "秒前",
        "raw_screen": "📺 **原始屏幕**",
        "empty_screen": "[空屏幕]",
        "resuming_last": "🔄 恢复**上次会话**...",
        "listing_sessions": "📋 **列出会话**\n使用 /up, /down 和 /enter 选择，或复制 ID 用于 `/resume <id>`。",
        "resuming_session": "🔄 搜索并恢复会话: `{}`...",
        "new_session": "🆕 开始**新会话**...",
        "specify_model": "⚠️ 必须指定模型。\n选项: {}\n示例: `/model haiku`",
        "invalid_model": "❌ 无效模型。请使用: {}",
        "restarting_model": "🔄 正在使用模型 **{}** 重启 Claude...",
        "restarted_model": "✅ 已在 {} 模式下重启。",
        "available_commands": "🤖 **可用命令**",
        "current_mode": "当前模式",
        "mode_streaming": "🌊 流式 (Streaming)",
        "mode_silent": "🤫 静默 (Silent)",
        "basics_header": "📝 **基础:**",
        "advanced_header": "\n⚠️ **高级:**",
        "help_footer": "\n_(使用 `/help admin` 查看更多命令)_",
        "access_denied": "⛔ 拒绝访问 ID {}",
        "mode_changed": "模式已更改为: **{}**",
        "language_changed": "🌐 语言已更改为: **{}**",
        "invalid_language": "❌ 无效语言。可用: {}",
        # Descriptions
        "cmd_start": "启动机器人",
        "cmd_help": "查看此帮助",
        "cmd_mode": "切换 静默/流式 模式",
        "cmd_screen": "查看当前屏幕 (静默模式下有用)",
        "cmd_enter": "发送 ENTER 键",
        "cmd_arrows": "导航箭头 (用于菜单)",
        "cmd_status": "进程状态",
        "cmd_resume": "恢复会话 (上次, 搜索 或 列表)",
        "cmd_new": "开始新会话",
        "cmd_model": "更改模型 (需重启)",
        "cmd_restart": "重启进程",
        "cmd_ctrlc": "发送中断 (Ctrl+C)",
        "cmd_lang": "更改语言 (en, es, zh)"
    }
}

# --- HELPERS ---

def get_system_lang():
    lang_code = os.getenv("BOT_LANGUAGE")
    if lang_code and lang_code in TRANSLATIONS:
        return lang_code

    try:
        sys_lang = locale.getdefaultlocale()[0]
        if sys_lang:
            code = sys_lang.split('_')[0]
            if code in TRANSLATIONS:
                return code
    except:
        pass

    return "en" # Default fallback

CURRENT_LANG = get_system_lang()

def t(key, *args):
    """Get translated string."""
    lang_dict = TRANSLATIONS.get(CURRENT_LANG, TRANSLATIONS["en"])
    text = lang_dict.get(key, key)
    if args:
        return text.format(*args)
    return text

def get_clean_screen_text():
    """Gets rendered text from pyte virtual screen."""
    rows = screen.display
    cleaned_rows = []
    for row in rows:
        stripped = row.rstrip()
        if not stripped:
            continue
        # Filters
        if "ctrl+g" in stripped.lower() or "──────" in stripped:
            continue
        if "esc to undo" in stripped.lower():
            continue
        cleaned_rows.append(stripped)
    return "\n".join(cleaned_rows)

def trigger_update():
    """Signals that an update should be forced soon."""
    global force_update_next
    force_update_next = True

async def safe_reply(update: Update, text: str, parse_mode=None):
    """Sends a reply safely, handling edited or empty messages."""
    try:
        message = update.effective_message
        if message:
            await message.reply_text(text, parse_mode=parse_mode)
        else:
            print(f"⚠️ Could not reply: update without valid message. Text: {text}")
    except Exception as e:
        print(f"❌ Error replying: {e}")

async def read_from_pty():
    """Reads bytes from process and updates pyte virtual screen."""
    global master_fd, last_output_time
    loop = asyncio.get_event_loop()

    while True:
        if master_fd is None:
            await asyncio.sleep(1)
            continue

        try:
            output = await loop.run_in_executor(None, os.read, master_fd, 1024)
            if not output:
                print("EOF from PTY process")
                await asyncio.sleep(1)
                continue

            try:
                last_output_time = time.time()
                text_chunk = output.decode('utf-8', errors='ignore')
                stream.feed(text_chunk)
            except Exception as e:
                print(f"Error processing chunk: {e}")

        except OSError:
            await asyncio.sleep(1)

def start_claude_process():
    """Starts or restarts the Claude process."""
    global process, master_fd, slave_fd, screen, stream

    if process:
        try:
            process.terminate()
            process.wait()
        except:
            pass

    if master_fd:
        try: os.close(master_fd)
        except: pass

    if slave_fd:
        try: os.close(slave_fd)
        except: pass

    screen.reset()
    stream = pyte.Stream(screen)

    master_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = str(SCREEN_COLS)
    env["LINES"] = str(SCREEN_ROWS)

    print(f"Starting Claude process: {' '.join(CLAUDE_COMMAND)} ...")
    process = subprocess.Popen(
        CLAUDE_COMMAND,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        universal_newlines=False,
        env=env
    )
    os.close(slave_fd)
    slave_fd = None

async def send_buffered_output(app):
    """Sends screen content to Telegram."""
    global last_output_time, last_sent_time, force_update_next

    while True:
        await asyncio.sleep(0.5)
        current_time = time.time()

        if last_output_time <= last_sent_time:
            continue

        silence_duration = current_time - last_output_time
        time_since_last_send = current_time - last_sent_time
        should_send = False

        if STREAM_MODE:
            is_silence = (silence_duration >= DEBOUNCE_TIME)
            is_timeout = (time_since_last_send >= MAX_WAIT_TIME)
            should_send = is_silence or is_timeout
        else:
            if force_update_next:
                if silence_duration >= 0.5:
                    should_send = True
                    force_update_next = False
            else:
                is_long_silence = (silence_duration >= IDLE_TIME_THRESHOLD)
                should_send = is_long_silence

        if should_send:
            text = get_clean_screen_text()
            last_sent_time = current_time

            if text.strip():
                if len(text) > 4000:
                    text = text[-4000:]
                    text = "...\n" + text

                safe_text = html.escape(text)
                try:
                    await app.bot.send_message(
                        chat_id=ALLOWED_USER_ID,
                        text=f"<pre>{safe_text}</pre>",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Error sending to Telegram: {e}")

# --- COMMANDS ---

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    global CURRENT_LANG

    if not context.args:
        available = ", ".join(TRANSLATIONS.keys())
        await safe_reply(update, f"🌐 Current language: **{CURRENT_LANG}**\nOptions: {available}\nExample: `/language es`", parse_mode="Markdown")
        return

    new_lang = context.args[0].lower()
    if new_lang in TRANSLATIONS:
        CURRENT_LANG = new_lang
        await safe_reply(update, t("language_changed", new_lang), parse_mode="Markdown")
    else:
        available = ", ".join(TRANSLATIONS.keys())
        await safe_reply(update, t("invalid_language", available), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ALLOWED_USER_ID: return
    await safe_reply(update, t("connected"))

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    await safe_reply(update, t("restarting"), parse_mode="Markdown")
    start_claude_process()
    await safe_reply(update, t("restarted"))

async def send_ctrl_c(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    if master_fd:
        os.write(master_fd, b'\x03')
        await safe_reply(update, t("interrupt_sent"))

async def send_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    if master_fd:
        os.write(master_fd, b'\r')
        trigger_update()
        await safe_reply(update, t("enter_sent"))

async def send_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    if master_fd:
        os.write(master_fd, b'\x1b[A')
        trigger_update()
        await safe_reply(update, t("arrow_up"))

async def send_down(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    if master_fd:
        os.write(master_fd, b'\x1b[B')
        trigger_update()
        await safe_reply(update, t("arrow_down"))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    is_running = process and process.poll() is None
    status_msg = (
        f"{t('bot_status')}\n"
        f"Claude Process: {t('process_running') if is_running else t('process_stopped')}\n"
        f"{t('current_model')}: `{' '.join(CLAUDE_COMMAND)}`\n"
        f"{t('pid')}: {process.pid if process else 'N/A'}\n"
        f"{t('last_output')}: {time.time() - last_output_time:.1f}{t('seconds_ago')}\n"
        f"{t('last_sent')}: {time.time() - last_sent_time:.1f}{t('seconds_ago')}\n"
    )
    await safe_reply(update, status_msg, parse_mode="Markdown")

async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    rows = screen.display
    raw_text = "\n".join([r.rstrip() for r in rows if r.strip()])
    if not raw_text: raw_text = t("empty_screen")
    if len(raw_text) > 4000: raw_text = raw_text[-4000:]
    safe_text = html.escape(raw_text)
    await safe_reply(update, f"{t('raw_screen')}:\n<pre>{safe_text}</pre>", parse_mode="HTML")

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    global CLAUDE_COMMAND
    if not context.args:
        CLAUDE_COMMAND = ["claude", "--continue"]
        await safe_reply(update, t("resuming_last"), parse_mode="Markdown")
    else:
        search_term = " ".join(context.args)
        if search_term.strip().lower() == "list":
             CLAUDE_COMMAND = ["claude", "--resume"]
             await safe_reply(update, t("listing_sessions"), parse_mode="Markdown")
        else:
            CLAUDE_COMMAND = ["claude", "--resume", search_term]
            await safe_reply(update, t("resuming_session", search_term), parse_mode="Markdown")
    start_claude_process()

async def new_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    global CLAUDE_COMMAND
    CLAUDE_COMMAND = ["claude"]
    await safe_reply(update, t("new_session"), parse_mode="Markdown")
    start_claude_process()

async def change_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    ALLOWED_MODELS = ["sonnet", "opus", "haiku"]
    if not context.args:
        await safe_reply(update, t("specify_model", ', '.join(ALLOWED_MODELS)), parse_mode="Markdown")
        return
    model = context.args[0].lower()
    if model not in ALLOWED_MODELS:
        await safe_reply(update, t("invalid_model", ', '.join(ALLOWED_MODELS)))
        return
    global CLAUDE_COMMAND
    CLAUDE_COMMAND = ["claude", "--model", model]
    await safe_reply(update, t("restarting_model", model), parse_mode="Markdown")
    start_claude_process()
    await safe_reply(update, t("restarted_model", model))

async def toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    global STREAM_MODE
    STREAM_MODE = not STREAM_MODE
    mode_name = t("mode_streaming") if STREAM_MODE else t("mode_silent")
    await safe_reply(update, t("mode_changed", mode_name), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID: return
    show_sensitive = False
    if context.args and "admin" in context.args:
        show_sensitive = True
    current_mode = t("mode_streaming") if STREAM_MODE else t("mode_silent")
    help_text = (
        f"{t('available_commands')}\n\n"
        f"{t('current_mode')}: **{current_mode}**\n\n"
        f"{t('basics_header')}\n"
        f"/start - {t('cmd_start')}\n"
        f"/help - {t('cmd_help')}\n"
        f"/mode - {t('cmd_mode')}\n"
        f"/screen - {t('cmd_screen')}\n"
        f"/enter - {t('cmd_enter')}\n"
        f"/up /down - {t('cmd_arrows')}\n"
        f"/status - {t('cmd_status')}\n"
        f"/resume [query|list] - {t('cmd_resume')}\n"
        f"/new - {t('cmd_new')}\n"
        f"/language [code] - {t('cmd_lang')}\n"
    )
    if show_sensitive:
        help_text += (
            f"{t('advanced_header')}\n"
            f"/model [name] - {t('cmd_model')}\n"
            f"/restart - {t('cmd_restart')}\n"
            f"/ctrlc - {t('cmd_ctrlc')}\n"
        )
    else:
        help_text += t("help_footer")
    await safe_reply(update, help_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global master_fd
    user = update.effective_user
    if user.id != ALLOWED_USER_ID:
        print(t("access_denied", user.id))
        return
    message = update.message or update.edited_message
    if not message or not message.text: return

    print(f"Message from {user.first_name} (ID: {user.id}): {message.text}")

    if master_fd:
        os.write(master_fd, message.text.encode('utf-8'))
        await asyncio.sleep(0.1)
        os.write(master_fd, b'\r')
        trigger_update()

def main():
    global process, master_fd

    if not TELEGRAM_TOKEN or ALLOWED_USER_ID == 0:
        print("Bot cannot start: invalid configuration.")
        return

    start_claude_process()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("ctrlc", send_ctrl_c))
    application.add_handler(CommandHandler("enter", send_enter))
    application.add_handler(CommandHandler("up", send_up))
    application.add_handler(CommandHandler("down", send_down))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("screen", screen_command))
    application.add_handler(CommandHandler("model", change_model))
    application.add_handler(CommandHandler("mode", toggle_mode))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("new", new_session_command))
    application.add_handler(CommandHandler("language", change_language))
    application.add_handler(CommandHandler("lang", change_language))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    loop = asyncio.get_event_loop()
    loop.create_task(read_from_pty())
    loop.create_task(send_buffered_output(application))

    print("🤖 Bot Pro started... Waiting for messages.")
    application.run_polling()

if __name__ == "__main__":
    main()