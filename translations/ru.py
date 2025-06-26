from .model import LanguagePack

class RussianPack(LanguagePack):
    FLAG = "🇷🇺"


    BACK_BUTTON = "⬅️"
    GEN_KEY_BUTTON = "🔑 Ключ"
    GET_UDID_BUTTON = "🆔 Получить UDiD"
    CHECK_STATUS_BUTTON = "🔍 Статус UDiD"
    REGISTER_UDID_BUTTON = "➕ Рег UDID"

    START_MESSAGE = "Привет"

    LANGUAGE_MESSAGE = "Выберите язык"
    LANGUAGE_CHANGED = "Язык успешно изменён"
    LANGUAGE_NOT_CHANGED = "Язык не изменён"
    LANGUAGE_NOT_AVAILABLE = "Язык недоступен"

    SHARE_LINK_BUTTON = "Поделиться 🤝"
    MAGIC_LINK_MESSAGE = "Вот ваша волшебная ссылка: {url}"

    KEY_ID_PROMPT = "Следуйте видео и введите KeyID с портала Appstore connect.\n\nСсылка: https://appstoreconnect.apple.com/\n\n Пожалуйста, отправьте KEYID 👇👇"
    ACCESS_ID_PROMPT = "Введите ваш идентификатор издателя."
    P8_FILE_PROMPT = "Отправьте ваш файл p8."

    INVALID_P8_FILE_ERROR = "Неверный файл p8. Отправьте корректный файл p8."
    MAX_P8_FILE_SIZE_ERROR = "Файл слишком большой, максимальный размер {max_limit}."

    ACCOUNT_IMPORTED_MESSAGE = "Аккаунт {username} импортирован!"
    IMPORTING_PROGRESS_MESSAGE = "Импортирую <b>{first_name} {last_name}</b>..."
    ENABLING_CAPABILITIES_MESSAGE = "Включение возможностей..."
    ENABLING_CAPABILITIES_PROGRESS_MESSAGE = "[{completed}/{total}] Включение возможностей.\n\nСтатус: <blockquote expandable>{capabilities}</blockquote>"
    ENABLED_CAPABILITIES_PROGRESS_MESSAGE = "[{completed}/{total}] Возможности включены.\n\nСтатус: <blockquote expandable>{capabilities}</blockquote>"

    FORBIDDEN_ERROR = "Вам не разрешено это делать."
    SOMETING_WENT_WRONG_ERROR = "Что-то пошло не так."
    INVALID_CREDENTIALS_ERROR = "Неверные учетные данные.\n\nОтправьте KEY ID: или нажмите /cancel для отмены."

    OLD_PAGE = "<"
    NEXT_PAGE = ">"
    ACCOUNT_LIST_MESSAGE = "Выберите аккаунт для продолжения.\n\n<i>страница {current_page} из {total_page}</i>"

    UDID_PROMPT = "Введите ваш UDID."
    INVALID_UDID_ERROR = "{udid} кажется недействительным!"

    SELECT_DEVICE_PROMPT = "Выберите ваше устройство."

    NORMAL_PROVISION_TEMPLATE = """ID : <code>{id}</code>
UDID : <code>{udid}</code>
Модель: {attributes[model]}
Добавлен: {attributes[addedDate]}

Статус: {status_string}
Имя: <b>{first_name} {last_name}</b>
"""

    ENABLED_PROVISION_TEMPLATE = """ID : <code>{id}</code>
UDID : <code>{udid}</code>
Модель: {attributes[model]}
Добавлен: {attributes[addedDate]}
Истекает: {certificate_info[valid_to]}

Статус: {status_string}
Имя: <b>{first_name} {last_name}</b>

Права:
<blockquote expandable>{entitlements}</blockquote>
"""

    EXPIRED_STATE = "Истек ⏲️"
    REVOKED_STATE = "Отозван ❌"
    DISABLED_STATE = "Отключен 🚫"
    INELIGIBLE_STATE = "Неподходящий 14/30 ⏰"
    PROCESSING_STATE = "Обрабатывается ⌛ ({days} дней, {hours} часов, {minutes} минут)"

    GET_CERTIFICATE_BUTTON = "⬇️ Получить сертификат ({first_name} {last_name})"
    UDID_NOT_FOUND_ERROR = "UDID не найден!"
    UDID_ALREADY_REGISTERED = "<code>{udid}</code> Неверный UDID!"

    ERROR_REGISTERING_UDID = "Ошибка при регистрации UDID! \nПричина:\nВойдите в аккаунт разработчика и примите условия и соглашения Apple'\n\n``Developer.apple.com``"

    PROCESSING_REGISTER_UDID = "Регистрация UDID..."
    CHECKING_UDID_STATUS = "Проверка статуса вновь зарегистрированного UDID..."

    NO_USERNAME_ERROR = "У вас нет имени пользователя. Пожалуйста, сначала установите его."
    IN_CONVERSATION_ERROR = "Вы уже в диалоге. Нажмите /cancel 👈"

    SPAM_MESSAGE = "Вы спамите!"
    CERTIFICATE_NOT_FOUND = "UDID не найден!"
    UDID_NOT_AVAILABLE = "UDID недоступен!"
    FETCHING_CERTIFICATE = "Получение сертификата..."
    SIGNED_IPA_CAPTION_MESSAGE = "Пароль: <code>{password}</code>"

    CONFIRMATION_REFETCH_MESSAGE = "Go to developer portal and enable entitlements for this bundle ID: {bundle_id} "
    CONFIRMATION_REFETCH_BUTTON = "🔄 Done"
    REFETCH_PROVISION_BUTTON = "🔄 Обновить Provision"
    REFETCHING_PROVISION_MESSAGE = "Обновление provision для {completed}/{total} udids..."
    REFETCH_COMPLETED_MESSAGE = "{total_udids} обновлено!"
    LIST_UDID_BUTTON = "📱 Спис UDiD"
    EXPORTING_UDIDS_TEXT = "Экспортирую UDID..."

    IPA_ARE_SIGNED = """Приложение подписано для указанного <code>{udid}</code> и готово к установке."""

    INVALID_KEY = "Неверный ключ!"
    NO_OF_KEYS_PROMPT = "Введите количество ключей, которое вы хотите сгенерировать."
    KEY_GENERATED_MESSAGE = """
Ключ успешно сгенерирован!

Тип устройства : <b>{device_type}</b>

ID аккаунта : <code>{acc_id}</code>
Имя аккаунта: <b>{first_name} {last_name}</b>

Ссылки:
{links}
"""
    KEY_NOT_FOUND = "Ключ не найден или уже использован!"
    MAX_KEYGEN_LIMIT = "Вы можете сгенерировать не более {limit} ключей за раз.\n\nОтправьте количество ключей, которое вы хотите сгенерировать:"

    IMPORTING_DEVICES_MESSAGE = "Импортирую {completed}/{total} устройств..."
    IMPORTED_DEVICES_MESSAGE = "Импортировано {completed}/{total} устройств."

    UDID_CHECK_LINK = "\n<blockquote>https://t.me/{username}?start=chk{udid}</blockquote>"
    INACTIVE_ACCOUNT_MESSAGE = "Этот аккаунт неактивен!"

    ACCOUNT_NOT_FOUND = "Аккаунт не найден!"

    SETTINGS_BUTTON = "⚙️ Настройки"

    LANGUAGE_SETTINGS = "🌐 Язык"
    SETTINGS_MESSAGE = "Настройки"
    ADD_PARTNER = "➕ Добавить партнера"
    REMOVE_PARTNER = "➖ Удалить партнера"
    ENABLE_UDID = "🟢 Включить UDID"
    DISABLE_UDID = "🔴 Отключить UDID"

    UDID_DISABLED = "UDID {udid} отключен!"
    UDID_ENABLED = "UDID {udid} включен!"
    UDID_IS_DISABLED = "UDID отключен, пожалуйста, свяжитесь с продавцом."

    ID_TEXT = "ID : <code>{id}</code>"

    ADD_PARTNER_MESSAGE = "Поделитесь этой ссылкой с вашим партнером, чтобы добавить его в ваш аккаунт как реселлера.\n\n<code>{link}</code>" 

    INVALID_PARTNER_KEY = "Недействительный ключ приглашения или ключ уже использован!"
    RESELLER_ADDED_MESSAGE = "Вы были добавлены к {email}"
    RESELLER_LIST_MESSAGE = "Выберите реселлера для удаления."
    RESELLER_REMOVED_MESSAGE = "Реселлер удален!"
