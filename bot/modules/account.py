import io 
import math 
import uuid
import base64
import config 
import logging 
from html import escape
from bson import ObjectId
from pymongo import UpdateOne
from bot.utils import sanitize, send_log
from bot.states import ImportAccountStates
from bot import translations, LanguagePack, db
from telegram.ext import CallbackContext, ConversationHandler
from api import AppleDeveloperAccount, errors, DeviceType, AccountsManager
from telegram import Update, ReactionTypeEmoji, InputFile, InlineKeyboardButton, InlineKeyboardMarkup


@translations.get_lang
@sanitize(entry_point=True)
async def import_account_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    video_id = context.bot_data.get("video_id")
    if video_id:
        await update.effective_user.send_video(video=video_id, caption=user_lang.KEY_ID_PROMPT)
    else:
        with open("file.mp4", "rb") as file:
            video_object = await update.effective_user.send_video(video=InputFile(file), caption=user_lang.KEY_ID_PROMPT)
            context.bot_data["video_id"] = video_object.video.file_id
    return ImportAccountStates.KEY_ID

@translations.get_lang
@sanitize(conversation_state=True)
async def key_id_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    context.user_data["key_id"] = update.effective_message.text
    await update.effective_message.reply_text(user_lang.ACCESS_ID_PROMPT)
    return ImportAccountStates.ISSUE_ID


@translations.get_lang
@sanitize(conversation_state=True)
async def issue_id_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    context.user_data["issue_id"] = update.effective_message.text
    await update.effective_message.reply_text(user_lang.P8_FILE_PROMPT)
    return ImportAccountStates.P8_FILE


@translations.get_lang
@sanitize(conversation_state=True)
async def p8_file_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    file = update.effective_message.document

    if not file:
        await update.effective_message.reply_text(user_lang.INVALID_P8_FILE_ERROR)
        return ImportAccountStates.P8_FILE

    if not file.file_name.endswith(".p8"):
        await update.effective_message.reply_text(user_lang.INVALID_P8_FILE_ERROR)
        return ImportAccountStates.P8_FILE

    if file.file_size > config.MAX_P8_FILE_SIZE:
        await update.effective_message.reply_text(user_lang.MAX_P8_FILE_SIZE_ERROR.format(max_limit=config.MAX_P8_FILE_SIZE))
        return ImportAccountStates.P8_FILE

    await update.effective_message.set_reaction(reaction=ReactionTypeEmoji("⚡️"))

    account_info: dict = context.user_data.copy()

    p8_file = await file.get_file()
    buffer = io.BytesIO()
    await p8_file.download_to_memory(out=buffer)
    buffer.seek(0)

    account = AppleDeveloperAccount(
        key_id=account_info["key_id"],
        issuer_id=account_info["issue_id"],
        p8_file=buffer.read(),
    )
    buffer.seek(0)

    try:
        account_response = await account.get_account_info()
        account_data = account_response[0]
        account_id = account_data.get("id")
        username = account_data.get("attributes", {}).get("username")
        first_name = account_data.get("attributes", {}).get("firstName")
        last_name = account_data.get("attributes", {}).get("lastName")  

        alert_message = await update.effective_message.reply_text(user_lang.IMPORTING_PROGRESS_MESSAGE.format(first_name=first_name, last_name=last_name))

        ios_data = await account.get_devices_info(DeviceType.IOS)
        macos_data = await account.get_devices_info(DeviceType.MAC_OS)
        certificate_id, certificate = await account.generate_certificate(password=config.PASSWORD)
        logging.info(f"Certificate ID : {certificate_id}")

        await alert_message.edit_text(user_lang.ENABLING_CAPABILITIES_MESSAGE)

        async def callback_function(capabilities_status: dict):
            completed = sum(capabilities_status.values())
            total = len(capabilities_status)
            capabilities = "\n".join(f"{'✅' if status else '🔍'} {capability}" for capability, status in capabilities_status.items())
            if completed == total:
                TEMPLATE = user_lang.ENABLED_CAPABILITIES_PROGRESS_MESSAGE
            else:
                TEMPLATE = user_lang.ENABLING_CAPABILITIES_PROGRESS_MESSAGE
            await alert_message.edit_text(TEMPLATE.format(completed=completed, total=total, capabilities=capabilities))

        app_id = await account.create_app_id(account_id, callback=callback_function)

    except errors.Unauthorized:
        await update.effective_message.reply_text(
            user_lang.INVALID_CREDENTIALS_ERROR
        )
        return ImportAccountStates.KEY_ID
    except errors.ErrorResponse:
        await update.effective_message.reply_text(
            user_lang.SOMETING_WENT_WRONG_ERROR
        )
        return ConversationHandler.END
    except errors.Forbidden:
        await update.effective_message.reply_text(
            user_lang.FORBIDDEN_ERROR
        )
        return ConversationHandler.END
    
    except Exception as e:
        logging.info(f"Error importing account: {e}")  
        await update.effective_message.reply_text(f"An error occured.\n\nPlease report it.")
        return ConversationHandler.END

    new_account_data = {
        "account_id": account_id,
        "p8_file": base64.b64encode(buffer.read()).decode("utf-8"),
        "user_id": update.effective_user.id,
        "inserted_at": update.effective_message.date,
        "account_info": account_data,
        "app_id": app_id,
        "key_id": account_info["key_id"],
        "issue_id": account_info["issue_id"],
        "p12": base64.b64encode(certificate).decode("utf-8"),
        "ios_count": len(ios_data),
        "macos_count": len(macos_data),
        "certificate_id": certificate_id
    }

    all_devices = ios_data + macos_data

    importing_device_message = await update.effective_message.reply_text(user_lang.IMPORTING_DEVICES_MESSAGE.format(completed=0, total=len(all_devices)))

    for no, device in enumerate(ios_data + macos_data, start=1):
        device_attributes = device.get("attributes", {})

        logging.info(f"Importing device {device.get('id')} with deviceClass {device_attributes.get('deviceClass')}")

        if no % 10 == 0:
            await importing_device_message.edit_text(user_lang.IMPORTING_DEVICES_MESSAGE.format(completed=no, total=len(all_devices)))

        if device_attributes.get("deviceClass") not in ["IPHONE", "IPOD", "MAC", "IPAD"]:
            logging.info(f"Skipping device {device.get('id')} because it is not allowed deviceClass")
            continue

        if device_attributes.get('status') in ["ENABLED"]:
            if device_attributes.get('status') == "DISABLED":
                logging.info(f"Enabling device {device.get('id')}")
                register_response = await account.enable_udid(udid_id=device.get('id'))
                # logging.info(register_response)

                device = await account.get_udid_info(udid_id=device.get("id"))

            logging.info(f"Creating provision for device {device.get('id')} with deviceClass {device_attributes.get('deviceClass')}")
            device["provision_data"] = await account.create_provision(certificate_id=certificate_id, device_id=device.get("id"), app_id=app_id)
        device["user_id"] = update.effective_user.id
        device["account_id"] = account_id

    await importing_device_message.edit_text(user_lang.IMPORTED_DEVICES_MESSAGE.format(completed=len(all_devices), total=len(all_devices)))

    await db.udids.delete_many({"account_id": account_id})

    if ios_data:
        ios_operations = [
            UpdateOne(
                {"id": device["id"]},
                {"$set": device},
                upsert=True
            )
            for device in ios_data
        ]
        await db.udids.bulk_write(ios_operations)

    if macos_data:
        macos_operations = [
            UpdateOne(
                {"device_id": device["id"]},
                {"$set": device},
                upsert=True
            )
            for device in macos_data
        ]
        await db.udids.bulk_write(macos_operations)

    await db.accounts.replace_one(
        {"account_id": account_id}, new_account_data, upsert=True
    )
    await send_log(f"{first_name} {last_name} ({username}) imported by {update.effective_user.mention_html()}\n\nDevices added: \nIOS : {len(ios_data)}\nMACOS : {len(macos_data)}")
    await update.effective_message.reply_text(user_lang.ACCOUNT_IMPORTED_MESSAGE.format(username=username))
    return ConversationHandler.END


@translations.get_lang
@sanitize()
async def refresh_account(user_lang: LanguagePack, update: Update, context: CallbackContext):
    account_id = ObjectId(context.match.group(1))
    account_data = await db.accounts.find_one({"_id": account_id, "user_id": update.effective_user.id})
    if not account_data:
        await update.callback_query.answer(user_lang.ACCOUNT_NOT_FOUND, show_alert=True)
        return 
    
    await update.effective_message.edit_text(
        text=user_lang.CONFIRMATION_REFETCH_MESSAGE.format(bundle_id=account_data.get("account_id", "123")), 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(user_lang.CONFIRMATION_REFETCH_BUTTON, callback_data=f"account|{context.match.group(1)}|cnfrefresh")],
        ])
    )


@translations.get_lang
@sanitize()
async def cnfrefresh_account(user_lang: LanguagePack, update: Update, context: CallbackContext):
    account_id = ObjectId(context.match.group(1))
    account_data = await db.accounts.find_one({"_id": account_id, "user_id": update.effective_user.id})

    if not account_data:
        await update.callback_query.answer(user_lang.ACCOUNT_NOT_FOUND, show_alert=True)
        return

    filters = {
        "account_id": account_data.get("account_id"),
        "attributes.status": "ENABLED", 
    }

    active_udids = db.udids.find(filters)
    total_active_udid_count = await db.udids.count_documents(filters)

    apple_account = AppleDeveloperAccount(key_id=account_data["key_id"], issuer_id=account_data["issue_id"], p8_file=base64.b64decode(account_data["p8_file"]))

    count = 0 
    await update.effective_message.edit_text(user_lang.REFETCHING_PROVISION_MESSAGE.format(completed=count, total=total_active_udid_count))
    async for udid in active_udids:
        count += 1

        try:
            new_udid_provision_data = await apple_account.create_provision(certificate_id=account_data.get('certificate_id'), device_id=udid.get("id"), app_id=account_data.get("app_id"))
            await db.udids.update_one(
                {"_id": udid["_id"]}, 
                {"$set": {"provision_data": new_udid_provision_data}}
            )
        except Exception as e:
            logging.exception(f"Error refreshing provision for udid {udid.get('id')}: {e}") 

        if count % 10 == 0:
            try:
                await update.effective_message.edit_text(user_lang.REFETCHING_PROVISION_MESSAGE.format(completed=count, total=total_active_udid_count))
            except: pass 

    await update.effective_message.edit_text(user_lang.REFETCH_COMPLETED_MESSAGE.format(total_udids=total_active_udid_count))    
    

@translations.get_lang
@sanitize()
async def account_list(user_lang: LanguagePack, update: Update, context: CallbackContext):
    page_no = int(context.match.group(1))
    action = context.match.group(2)
    allow_reseller = action in ["register"]
    accounts, next_page, last_page, total_pages = await AccountsManager(update.effective_user.id).pagination(start_page=page_no, allow_reseller=allow_reseller)

    buttons = []
    async for account in accounts:
        document_id = account.get("_id")
        account_data = account.get("account_info", {}).get("attributes", {})
        full_name = f"{account_data.get('firstName')} {account_data.get('lastName')}"
        button_text = full_name
        if action == "register":
            account_id = account.get("account_id")
            total_udids = account.get("ios_count", 0) + account.get("macos_count", 0)
            button_text = f"{full_name} ({total_udids}/300)"
        
        elif action in ["add_partner", "remove_partner"]:
            button_text = f"{full_name} ({len(account.get('resellers', []))})"

        if account.get('inactive'):
            button_text = f"🔴 {button_text}"
            buttons.append([InlineKeyboardButton(button_text, callback_data="inactive")])
        else:
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"account|{document_id}|{action}")])
    
    pagination_buttons = []

    if last_page is not None:
        pagination_buttons.append(InlineKeyboardButton(user_lang.OLD_PAGE, callback_data=f"accounts|{last_page}|{action}"))
    pagination_buttons.append(InlineKeyboardButton(user_lang.BACK_BUTTON, callback_data="home"))
    if next_page:
        pagination_buttons.append(InlineKeyboardButton(user_lang.NEXT_PAGE, callback_data=f"accounts|{next_page}|{action}"))

    buttons.append(pagination_buttons)
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_message.edit_text(user_lang.ACCOUNT_LIST_MESSAGE.format(current_page=page_no+1, total_page=math.ceil(total_pages)), reply_markup=keyboard)


@translations.get_lang
@sanitize()
async def get_share_link(user_lang: LanguagePack, update: Update, context: CallbackContext):
    account_id = ObjectId(context.match.group(1))
    account = await db.accounts.find_one({"_id": account_id, "user_id": update.effective_user.id})
    if not account:
        return
    
    account_id = account.get("account_id")

    doc = {
        "account_doc_id": account.get("_id"), 
        "key": str(uuid.uuid4()).replace("-", ""), 
        "created_from": update.effective_user.id
    }

    await db.sharing_keys.insert_one(doc)

    link = f"https://t.me/{context.bot.username}?start=install-{doc['key']}"

    await update.effective_message.edit_text(user_lang.ADD_PARTNER_MESSAGE.format(link=link))


@translations.get_lang
@sanitize()
async def install_account_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    key = context.match.group(1)
    sharing_key = await db.sharing_keys.find_one({"key": key})

    if not sharing_key:
        await update.effective_message.reply_text(user_lang.INVALID_PARTNER_KEY)
        return
    
    creator = sharing_key.get("created_from")

    await db.sharing_keys.delete_one({"key": key})
    account = await db.accounts.find_one({"_id": sharing_key.get("account_doc_id")})

    if not account:
        await update.effective_message.reply_text(user_lang.ACCOUNT_NOT_FOUND)
        return 

    email = account.get("account_info", {}).get("attributes", {}).get("username")
    user_id = update.effective_user.id

    await db.accounts.update_one(
        {"_id": account.get("_id")},
        {"$addToSet": {"resellers": {"name": escape(update.effective_user.full_name), "user_id": user_id}}}
    )

    await update.effective_message.reply_text(user_lang.RESELLER_ADDED_MESSAGE.format(user="you", email=email))
    try:
        await context.bot.send_message(creator, user_lang.RESELLER_ADDED_MESSAGE.format(user=update.effective_user.mention_html(), email=email))
    except Exception:
        pass


@translations.get_lang 
@sanitize()
async def list_resellers(user_lang: LanguagePack, update: Update, context: CallbackContext, overriden_data: str = None):
    if overriden_data:
        account_id = ObjectId(overriden_data)
    else:
        account_id = ObjectId(context.match.group(1))
        
    account = await db.accounts.find_one({"_id": account_id, "user_id": update.effective_user.id})
    if not account:
        await update.callback_query.answer(user_lang.ACCOUNT_NOT_FOUND, show_alert=True)
        return
    
    resellers = account.get("resellers", [])

    buttons = []
    for reseller in resellers:
        buttons.append([InlineKeyboardButton(reseller.get("name"), callback_data=f"rm_reseller|{reseller.get('user_id')}|{account_id}")])

    buttons.append([InlineKeyboardButton(user_lang.BACK_BUTTON, callback_data="home")])
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_message.edit_text(user_lang.RESELLER_LIST_MESSAGE, reply_markup=keyboard)


@translations.get_lang
@sanitize()
async def remove_reseller(user_lang: LanguagePack, update: Update, context: CallbackContext):
    user_id = int(context.match.group(1))
    account_id = ObjectId(context.match.group(2))

    account = await db.accounts.find_one({"_id": account_id, "user_id": update.effective_user.id})
    if not account:
        await update.callback_query.answer(user_lang.ACCOUNT_NOT_FOUND, show_alert=True)
        return

    await db.accounts.update_one(
        {"_id": account_id},
        {"$pull": {"resellers": {"user_id": user_id}}}
    )

    await update.callback_query.answer(user_lang.RESELLER_REMOVED_MESSAGE, show_alert=True)
    await list_resellers(update, context, overriden_data=account_id)
