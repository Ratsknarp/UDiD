import sys 
import math 
import uuid
import config 
import logging 
import aiohttp
import traceback
from bot import logger_bot
from datetime import datetime
from typing import Any, Callable
from translations.model import LanguagePack
from telegram.ext import ContextTypes, ConversationHandler
from telegram import InlineKeyboardButton, Update, InputFile


def parse_buttons(buttons: list[InlineKeyboardButton], k: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + k] for i in range(0, len(buttons), k)]

def format_time(time: datetime) -> str:
    if time:
        if isinstance(time, str):
            time = datetime.fromisoformat(time)
        return time.strftime("%d/%m/%Y")

def normalize_time(time: int) -> str:
    days = math.floor(time // 86400)
    hours = math.floor(time // 3600 % 24)
    minutes = math.floor(time // 60 % 60)
    seconds = math.floor(time % 60)
    return days, hours, minutes, seconds

async def url_shortner(url: str, max: bool = False) -> str:
    api_url = "https://api.udid.p12.ru/api"
    json_data = {"url": url}

    if max:
        json_data['expiration'] = 9999

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=json_data) as response:
            response_json = await response.json()
            return response_json

async def aenumerate(asequence, start=0):
    """Asynchronously enumerate an async iterator from a given start value"""
    n = start
    async for elem in asequence:
        yield n, elem
        n += 1

def get_command(
    p12: str,
    prov: str,
    output: str,
    ipa: str,
    bundle_id: str,
    password: str = None,
) -> str:
    base_command = f'~/zsign -k "{p12}" -m "{prov}" -z 0 -o "{output}"'
    if password:
        base_command += f' -p "{password}"'
    base_command += f' -b "{bundle_id}"'
    base_command += f' "{ipa}"'
    return base_command


def clear_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()

# handles error handling and conversation handling
def sanitize(entry_point: bool = False, cancel_command: bool = False, conversation_state: bool = False) -> Callable:
    def decorator(func: Callable) -> Callable:
        async def wrapper(lang_pack: LanguagePack, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            
            is_allowed = True

            if not conversation_state and context.user_data.get("in_conversation"):
                is_allowed = False

            if entry_point and is_allowed:
                context.user_data["in_conversation"] = True
            
            try:
                if is_allowed or cancel_command:
                    result = await func(lang_pack, update, context, *args, **kwargs)
                else:
                    if update.callback_query:
                        await update.callback_query.answer(lang_pack.IN_CONVERSATION_ERROR, show_alert=True)
                    elif update.effective_message:
                        await update.effective_message.reply_text(lang_pack.IN_CONVERSATION_ERROR)
                    return 

                if result == ConversationHandler.END:
                    clear_user_data(context=context)

                return result
    
            
            except Exception as error:
                await update.effective_message.reply_text("An error occurred.")
                
                logging.exception("Error")
                _, _, tb = sys.exc_info()
                tb_info = traceback.extract_tb(tb)
                filename, lineno, func_name, text = tb_info[-1]

                error_message = (
                    f"User: {update.effective_user.mention_html()}\n"
                    f"Error: {error}\n"
                    f"File: {filename}\n"
                    f"Function: {func_name}\n"
                    f"Line: {lineno}\n"
                    f"Code: {text}"
                )
                logging.exception("Error")
                await send_log(error_message)
                clear_user_data(context=context)
                return ConversationHandler.END 
            
        return wrapper
    return decorator

async def send_log(message: str):
    if len(message) > 4096:
        await logger_bot.send_document(config.LOG_CHAT_ID, InputFile(message.encode(), filename="app.log"))
    else:
        await logger_bot.send_message(config.LOG_CHAT_ID, message)
