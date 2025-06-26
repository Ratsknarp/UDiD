from r2 import R2Storage

BOT_TOKEN = "main_bot_token"
LOG_BOT_TOKEN = "log_channel_bot_token"

BOT_API_SERVER = "http://94.228.168.77:81/bot"
BOT_API_FILE_SERVER = "http://94.228.168.77:81/file/bot"

REDIS_URL = "redis://localhost:0000"
DATABASE_URL = "mangoDB_URL"

PASSWORD = "1"

LOG_CHAT_ID=-id_of_log_channel

MULTI_UDID_LIMIT = 100
MAX_KEYGEN_PER_REQUEST = 60

MAX_P8_FILE_SIZE = 1024 * 1024

API_URL = "https://fetch.p12.ru"
INSTALL_APP_URL = "https://t.me/udid_ibot/install"
GET_UDID_WEBAPP = "https://t.me/udid_ibot/udid"
WEBAPP_URL = "https://udid.p12.ru"

CHECK_DURATION = 2

R2 = R2Storage(
    endpoint_url="https://dasfasdjfhjasdjkfsd???",
    key_id="keyid",
    access_key="054101bf1b227",
    bucket="name_of_bucket",
    bucket_url="https://custom_bucket_url",
)

KEYS_R2 = R2Storage(
    endpoint_url="https://416c8dfd48d7017aa7d3dc38412356ca.r2.cloudflarestorage.com/",
    key_id="keyid",
    access_key="5e69",
    bucket="name_of_bucket",
    bucket_url="https://custom_bucket_url",
)

# same as R2
STATUS_R2 = R2
