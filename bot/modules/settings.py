from telegram.ext import CallbackContext
from bot.utils import parse_buttons, sanitize
from bot import db, translations, LanguagePack
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup


@translations.get_lang
@sanitize()
async def show_languages(user_lang: LanguagePack, update: Update, context: CallbackContext):
    buttons = [
        InlineKeyboardButton(f"> {pack.FLAG} <" if pack == user_lang else pack.FLAG, callback_data=f"set_lang|{lang}")
        for lang, pack in translations.LANGUAGE_PACKS.items()
    ]
    parsed_buttons = parse_buttons(buttons)
    parsed_buttons.append([InlineKeyboardButton(user_lang.BACK_BUTTON, callback_data="home")])
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                user_lang.LANGUAGE_MESSAGE,
                reply_markup=InlineKeyboardMarkup(parsed_buttons),
            )
        except Exception:
            pass 
    else:
        await update.effective_message.reply_text(
            user_lang.LANGUAGE_MESSAGE,
            reply_markup=InlineKeyboardMarkup(parsed_buttons),
        )


@translations.get_lang
@sanitize()
async def set_language(user_lang: LanguagePack, update: Update, context: CallbackContext):
    lang = context.match.group(1)
    if lang not in translations.LANGUAGE_PACKS:
        await update.callback_query.answer(user_lang.LANGUAGE_NOT_AVAILABLE, show_alert=True)
        return
    
    if user_lang == translations.LANGUAGE_PACKS[lang]:
        await update.callback_query.answer(user_lang.LANGUAGE_NOT_CHANGED, show_alert=True)
        return
    
    context.user_data["lang"] = lang
    await db.set_language(update.effective_user.id, lang)
    await update.callback_query.answer(user_lang.LANGUAGE_CHANGED, show_alert=True)
    await show_languages(update, context)


@translations.get_lang
@sanitize()
async def show_settings_buttons(user_lang: LanguagePack, update: Update, context: CallbackContext):
    buttons = [
        [
            InlineKeyboardButton(user_lang.ADD_PARTNER, callback_data="accounts|0|add_partner"),
            InlineKeyboardButton(user_lang.REMOVE_PARTNER, callback_data="accounts|0|remove_partner")
        ],
        [
            InlineKeyboardButton(user_lang.ENABLE_UDID, callback_data="accounts|0|enable_udid"),
            InlineKeyboardButton(user_lang.DISABLE_UDID, callback_data="accounts|0|disable_udid")
        ],
        [
            InlineKeyboardButton(user_lang.LANGUAGE_SETTINGS, callback_data="lang")
        ],
        [
            InlineKeyboardButton(user_lang.REFETCH_PROVISION_BUTTON, callback_data="accounts|0|refresh")
        ],
        [
            InlineKeyboardButton(user_lang.LIST_UDID_BUTTON, callback_data="accounts|0|list"),
        ],
        [
            InlineKeyboardButton(user_lang.BACK_BUTTON, callback_data="home")
        ]
    ]

    await update.effective_message.edit_text(user_lang.SETTINGS_MESSAGE, reply_markup=InlineKeyboardMarkup(buttons))