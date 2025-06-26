from .model import LanguagePack

class EnglishPack(LanguagePack):
    FLAG = "🇺🇸"

    BACK_BUTTON = "⬅️"
    GEN_KEY_BUTTON =  "🔑 Create Key"
    GET_UDID_BUTTON = "🆔 Get UDiD"
    CHECK_STATUS_BUTTON = "🔍 Check UDiD"
    REGISTER_UDID_BUTTON = "➕ Reg UDiD"

    START_MESSAGE = "Hi"

    LANGUAGE_MESSAGE = "Select your language"
    LANGUAGE_CHANGED = "Language changed successfully"
    LANGUAGE_NOT_CHANGED = "Language not changed"
    LANGUAGE_NOT_AVAILABLE = "Language not available"

    SHARE_LINK_BUTTON = "Share 🤝"
    MAGIC_LINK_MESSAGE = "Here is your magic link: {url}"

    KEY_ID_PROMPT = "Follow the video and please enter the KeyID from Appstore connect portal.\n\nLink: https://appstoreconnect.apple.com/\n\n Please send KEYID 👇👇"
    ACCESS_ID_PROMPT = "Please enter your issuer id."
    P8_FILE_PROMPT = "Please send your p8 file."

    INVALID_P8_FILE_ERROR = "Invalid p8 file. Please send a valid p8 file."
    MAX_P8_FILE_SIZE_ERROR = "The file is too big, max limit is {max_limit}."

    ACCOUNT_IMPORTED_MESSAGE = "Account {username} imported!"
    IMPORTING_PROGRESS_MESSAGE = "Importing <b>{first_name} {last_name}</b>..."
    ENABLING_CAPABILITIES_MESSAGE = "Enabling capabilities..."
    ENABLING_CAPABILITIES_PROGRESS_MESSAGE = "[{completed}/{total}] Enabling capabilities.\n\nStatus: <blockquote expandable>{capabilities}</blockquote>"
    ENABLED_CAPABILITIES_PROGRESS_MESSAGE = "[{completed}/{total}] Enabled capabilities.\n\nStatus: <blockquote expandable>{capabilities}</blockquote>"

    FORBIDDEN_ERROR = "You are not allowed to do this."
    SOMETING_WENT_WRONG_ERROR = "Something went wrong."
    INVALID_CREDENTIALS_ERROR = "Invalid credentials.\n\nSend KEY ID: or press /cancel to cancel."

    OLD_PAGE = "<" 
    NEXT_PAGE = ">" 
    ACCOUNT_LIST_MESSAGE = "Select account to conitnue.\n\n<i>page {current_page} of {total_page}</i>"

    UDID_PROMPT = "Please enter your UDID."
    INVALID_UDID_ERROR = "{udid} seems invalid!"

    SELECT_DEVICE_PROMPT = "Please select your device."

    NORMAL_PROVISION_TEMPLATE = """ID : <code>{id}</code>
UDID : <code>{udid}</code>
Model: {attributes[model]}
Added on : {attributes[addedDate]}

Status: {status_string}
Name : <b>{first_name} {last_name}</b>
"""

    ENABLED_PROVISION_TEMPLATE = """ID : <code>{id}</code>
UDID : <code>{udid}</code>
Model: {attributes[model]}
Added on : {attributes[addedDate]}
Expiry: {certificate_info[valid_to]}

Status: {status_string}
Name : <b>{first_name} {last_name}</b>

Entitlements:
<blockquote expandable>{entitlements}</blockquote>
"""

    EXPIRED_STATE = "Expired ⏲️"
    REVOKED_STATE = "Revoked ❌"
    DISABLED_STATE = "Disabled 🚫"
    INELIGIBLE_STATE = "Ineligible 14/30 ⏰"
    PROCESSING_STATE = "Processing ⌛ ({days} days, {hours} hours, {minutes} minutes)"

    GET_CERTIFICATE_BUTTON = "⬇️ Get Certificate ({first_name} {last_name})"
    UDID_NOT_FOUND_ERROR = "UDID not found!"
    UDID_ALREADY_REGISTERED = "<code>{udid}</code> Wrong UDiD!"

    ERROR_REGISTERING_UDID = "Error registering UDID! \nReason:\nEnter developer account and accept Apple terms and agreements'\n\n``Developer.apple.com``"

    PROCESSING_REGISTER_UDID = "Registering the UDID..."
    CHECKING_UDID_STATUS = "Checking the newly registered UDID status..."

    NO_USERNAME_ERROR = "You don't have a username. Please set it first."
    IN_CONVERSATION_ERROR = "You are already in a conversation. tap /cancel 👈"

    SPAM_MESSAGE = "You are spamming!"
    CERTIFICATE_NOT_FOUND = "UDID not found!"
    UDID_NOT_AVAILABLE = "UDID is not available!"
    FETCHING_CERTIFICATE = "Fetching certificate..."
    SIGNED_IPA_CAPTION_MESSAGE = "Password: <code>{password}</code>"

    CONFIRMATION_REFETCH_MESSAGE = "Go to developer portal and enable entitlements for this bundle ID: {bundle_id} "
    CONFIRMATION_REFETCH_BUTTON = "🔄 Done"
    REFETCH_PROVISION_BUTTON = "🔄 Update Provision"
    REFETCHING_PROVISION_MESSAGE = "Refetching provision for {completed}/{total} udids..."
    REFETCH_COMPLETED_MESSAGE = "{total_udids} refetched!"
    LIST_UDID_BUTTON = "📱 List UDID"
    EXPORTING_UDIDS_TEXT = "Exporting UDIDs..."

    IPA_ARE_SIGNED = """The application has been signed for the specified <code>{udid}</code> and is now ready for installation."""

    INVALID_KEY = "Invalid key!"
    NO_OF_KEYS_PROMPT = "Enter the number of keys you want to generate."
    KEY_GENERATED_MESSAGE = """
Key generated successfully!

Device Type : <b>{device_type}</b>

Account ID : <code>{acc_id}</code>
Account Name: <b>{first_name} {last_name}</b>

Links: 
{links}
"""
    KEY_NOT_FOUND = "Key not found or it already used!"
    MAX_KEYGEN_LIMIT = "You can only generate {limit} keys at a time.\n\nSend me the number of keys you want to generate:"

    IMPORTING_DEVICES_MESSAGE = "Importing {completed}/{total} devices..."
    IMPORTED_DEVICES_MESSAGE = "Imported {completed}/{total} devices."

    UDID_CHECK_LINK = "\n<blockquote>https://t.me/{username}?start=chk{udid}</blockquote>"
    INACTIVE_ACCOUNT_MESSAGE = "This account is inactive!"

    ACCOUNT_NOT_FOUND = "Account not found!"

    SETTINGS_BUTTON = "⚙️ Settings"

    LANGUAGE_SETTINGS = "🌐 Languages"
    SETTINGS_MESSAGE = "Settings" 
    ADD_PARTNER = "➕ Add partner"
    REMOVE_PARTNER = "➖ Remove Partner" 
    ENABLE_UDID = "🟢 Enable UDID" 
    DISABLE_UDID = "🔴 Disable UDID" 

    UDID_DISABLED = "UDID {udid} disabled!"
    UDID_ENABLED = "UDID {udid} enabled!"
    UDID_IS_DISABLED = "UDID is disabled, kindly contact the seller."

    ID_TEXT = "ID : <code>{id}</code>"

    ADD_PARTNER_MESSAGE = "Share this link with your partner to add them to your account as reseller.\n\n<code>{link}</code>"

    INVALID_PARTNER_KEY = "Invalid invite key or key is already used!"
    RESELLER_ADDED_MESSAGE = "{user} have been added to {email}"
    RESELLER_LIST_MESSAGE = "Select a reseller to remove."
    RESELLER_REMOVED_MESSAGE = "Reseller removed!"
