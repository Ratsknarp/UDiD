from telegram import Update
from database import Database
from .model import LanguagePack
from telegram.ext import ContextTypes
from typing import Callable, Awaitable, Any

from .en import EnglishPack
from .ru import RussianPack


class Translations:
    LANGUAGE_PACKS: dict[str, LanguagePack] = {
        "en": EnglishPack,
        "ru": RussianPack, 
    }

    def __init__(self, db: Database):
        self.db = db

    def get_lang(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            user_id = update.effective_user.id
            language = context.user_data.get("lang")
            if not language:
                language = await self.db.get_language(user_id) or update.effective_user.language_code
            lang_pack: LanguagePack = self.LANGUAGE_PACKS.get(language, EnglishPack)

            return await func(lang_pack, update, context, *args, **kwargs)
        return wrapper
