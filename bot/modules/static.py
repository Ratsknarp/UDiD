import config 
from urllib.parse import quote
from bot.utils import sanitize, url_shortner
from bot import translations, LanguagePack, db
from telegram.ext import CallbackContext, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


@translations.get_lang
@sanitize()
async def start_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    short_url_data = await url_shortner(url=f"{config.API_URL}/?account={context.bot.username}")
    url = f"{config.WEBAPP_URL}/?tgWebAppStartParam={short_url_data.get('code')}"
    buttons = [[
        InlineKeyboardButton(user_lang.CHECK_STATUS_BUTTON, callback_data="check_status"), 
        InlineKeyboardButton(user_lang.GET_UDID_BUTTON, web_app=WebAppInfo(url=url))
    ]]
    user_status = await db.accounts.find_one({
        "$or": [
            {"user_id": update.effective_user.id},
            {"resellers.user_id": update.effective_user.id}
        ]
    })
    if user_status:
        buttons.append(
            [
                InlineKeyboardButton(user_lang.GEN_KEY_BUTTON, callback_data="accounts|0|genkey"),
                InlineKeyboardButton(user_lang.REGISTER_UDID_BUTTON, callback_data="accounts|0|register")
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(user_lang.SETTINGS_BUTTON, callback_data="settings")
            ]
        )

    if update.callback_query:
        await update.callback_query.edit_message_text(user_lang.START_MESSAGE, reply_markup=InlineKeyboardMarkup(buttons))
        return
    await update.effective_message.reply_text(user_lang.START_MESSAGE, reply_markup=InlineKeyboardMarkup(buttons))


@translations.get_lang
@sanitize(cancel_command=True)
async def cancel_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    return ConversationHandler.END


@translations.get_lang
@sanitize()
async def get_special_link(user_lang: LanguagePack, update: Update, context: CallbackContext):
    username = update.effective_user.username
    if not username:
        await update.effective_message.reply_text(user_lang.NO_USERNAME_ERROR)
        return 
    
    short_url_data = await url_shortner(url=f"{config.API_URL}/?account={username}", max=True)
    code = short_url_data.get("code")
    url = f"{config.GET_UDID_WEBAPP}?startapp={code}&mode=compact"
    buttons = [[InlineKeyboardButton(user_lang.SHARE_LINK_BUTTON, url=f"tg://msg_url?url={quote(url)}")]]
    await update.effective_message.reply_text(user_lang.MAGIC_LINK_MESSAGE.format(url=url), reply_markup=InlineKeyboardMarkup(buttons))


@translations.get_lang  
@sanitize()
async def inactive_account_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    await update.callback_query.answer(user_lang.INACTIVE_ACCOUNT_MESSAGE, show_alert=True)

@translations.get_lang
@sanitize()
async def get_user_id(user_lang: LanguagePack, update: Update, context: CallbackContext):
    await update.effective_message.reply_text(user_lang.ID_TEXT.format(id=update.effective_user.id))