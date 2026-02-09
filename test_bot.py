import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

# Importamos la lógica del bot
# Nota: Para testear handle_message necesitamos mockear os.write en el módulo telebot
import telebot
from telebot import change_model, handle_message, ALLOWED_USER_ID, safe_reply

@pytest.mark.asyncio
async def test_change_model_safe_reply():
    """Verifica que change_model usa safe_reply y no falla si update.message es None"""
    # Mock del update
    update = MagicMock(spec=Update)
    update.effective_user.id = ALLOWED_USER_ID

    # Caso 1: update.message es None, pero effective_message existe (simulación de comando editado)
    update.message = None
    mock_message = AsyncMock(spec=Message)
    update.effective_message = mock_message

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["haiku"]

    # Mockear start_claude_process para que no intente arrancar procesos reales
    with patch('telebot.start_claude_process') as mock_start:
        await change_model(update, context)

    # Verificar que se llamó a reply_text en el mensaje efectivo
    assert mock_message.reply_text.call_count >= 1

@pytest.mark.asyncio
async def test_handle_message_split_enter():
    """Verifica que handle_message envía el texto y luego el Enter por separado"""
    update = MagicMock(spec=Update)
    update.effective_user.id = ALLOWED_USER_ID

    # Mensaje con texto
    mock_message = MagicMock(spec=Message)
    mock_message.text = "comando de prueba"
    update.message = mock_message
    update.effective_message = mock_message

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Mockear os.write y master_fd
    telebot.master_fd = 123 # File descriptor falso

    with patch('os.write') as mock_os_write:
        await handle_message(update, context)

        # Debería haber llamado a os.write al menos 2 veces
        # 1. El texto ("comando de prueba")
        # 2. El enter (b'\n')
        assert mock_os_write.call_count == 2

        # Verificar argumentos de las llamadas
        args_list = mock_os_write.call_args_list

        # Primera llamada: texto codificado
        assert args_list[0][0][1] == b"comando de prueba"

        # Segunda llamada: salto de línea
        assert args_list[1][0][1] == b"\n"

@pytest.mark.asyncio
async def test_safe_reply_logic():
    """Verifica la lógica de safe_reply"""
    update = MagicMock(spec=Update)

    # Caso: effective_message existe
    mock_msg = AsyncMock(spec=Message)
    update.effective_message = mock_msg

    await safe_reply(update, "hola")
    mock_msg.reply_text.assert_called_with("hola", parse_mode=None)

    # Caso: effective_message es None (no debería crashear)
    update.effective_message = None
    try:
        await safe_reply(update, "hola")
    except Exception:
        pytest.fail("safe_reply crasheó con effective_message=None")
