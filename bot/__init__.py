import config
import logging

from api import AccountsManager
from api.checker import AccountChecker

from database import Database, RedisDatabase
from logging.handlers import RotatingFileHandler
from translations import Translations, LanguagePack
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import ApplicationBuilder, Defaults, PicklePersistence, Application, ExtBot
from telegram import LinkPreviewOptions, BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats


logging.basicConfig(
    level=logging.INFO,
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5 * 1024 * 1024, backupCount=3),
        logging.StreamHandler(),
    ],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def setup(app: Application):
    bot = app.bot
    await db.setup()

    schedulers.start()
    schedulers.add_job(
        account_checker.start_checking,
        trigger="cron",
        hour="*",
        id="account_checker",
        max_instances=1,
    )

    await bot.delete_my_commands()
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Start the bot."),
            BotCommand(command="lang", description="Change bot language."),            
            BotCommand(command="udid", description="Get udid magic link."),            
            BotCommand(command="cancel", description="Cancels ongoing conversation."),            
            BotCommand(command="import", description="Import your developer account."),            
        ], 
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(command="chk", description="Check udid status."),
        ], 
        scope=BotCommandScopeAllGroupChats()
    )
    
r2 = config.R2
keys_r2 = config.KEYS_R2
    
rdb = RedisDatabase(config.REDIS_URL)
db = Database(config.DATABASE_URL, r2=keys_r2)
translations = Translations(db=db)
account_checker = AccountChecker(db=db)
AccountsManager.db = db

schedulers = AsyncIOScheduler()

app = (
    ApplicationBuilder()
    .token(config.BOT_TOKEN)
    .defaults(Defaults(parse_mode="HTML", block=False, link_preview_options=LinkPreviewOptions(is_disabled=True)))
    .persistence(PicklePersistence(filepath="data_file"))
    .post_init(setup)
    .write_timeout(60*60)
    .read_timeout(60*60)
    .build()
)
logger_bot = ExtBot(token=config.LOG_BOT_TOKEN, defaults=Defaults(parse_mode="HTML", block=False))

