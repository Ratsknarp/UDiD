import os
import re
import io
import csv
import uuid
import base64
import config
import logging
import asyncio
from html import escape
from checker import check
from bson import ObjectId
from bson.errors import InvalidId
from template import PLIST_TEMPLATE
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone
from bot import translations, LanguagePack, db, r2, rdb
from telegram.ext import CallbackContext, ConversationHandler
from api import AppleDeveloperAccount, errors, DeviceType, AccountsManager
from bot.states import RegisterUDIDStates, CheckUDIDStates, GenerateKeyStates, EnableDisableUDID
from bot.utils import sanitize, send_log, aenumerate, normalize_time, get_command, url_shortner, format_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, InputFile, ReactionTypeEmoji


@translations.get_lang
async def headless_udid_check(user_lang: LanguagePack, update: Update, context: CallbackContext):
    udid = context.match.group(1)
    if len(udid) not in {25, 40, 60}:
        await update.effective_message.reply_text(user_lang.INVALID_UDID_ERROR.format(udid=udid))
        return

    await update.effective_message.set_reaction(ReactionTypeEmoji("⚡️"))

    devices = db.udids.find({"attributes.udid": re.compile(udid, re.IGNORECASE)})
    devices_count = await db.udids.count_documents({"attributes.udid": re.compile(udid, re.IGNORECASE)})
    if devices_count == 0:
        await update.effective_message.reply_text(user_lang.UDID_NOT_FOUND_ERROR)
        return


    async for no, device in aenumerate(devices, start=1):
        buttons = []
        status_message = ""
        status = device.get('attributes', {}).get("status")
        account_data = await db.accounts.find_one({"account_info.id": device.get('account_id')})
        if not account_data:
            logging.info(f"Account not found for UDID: {udid}")
            continue

        post_second_row = True
        is_owner = account_data.get("user_id") == update.effective_user.id
        is_reseller = any(reseller.get("user_id") == update.effective_user.id for reseller in account_data.get("resellers", []))

        first_name = account_data.get("account_info", {}).get("attributes", {}).get("firstName")
        last_name = account_data.get("account_info", {}).get("attributes", {}).get("lastName")
        provision_data = device.get("provision_data")

        if provision_data:
            check_response = await check(base64.b64decode(provision_data.get("profileContent")))
            status = check_response.get("certificate_status")
            entitlements = "\n".join([f"{'✅' if value.get('status') else '❌'} {key}" for key, value in check_response.get('entitlements').items()])
            check_response.update(entitlements=entitlements)
            device.update(**check_response)

        TEMPLATE = user_lang.NORMAL_PROVISION_TEMPLATE
        match status:
            case "ENABLED":
                status_string = "Active 🟢"
                if device.get("provision_data"):
                    TEMPLATE = user_lang.ENABLED_PROVISION_TEMPLATE
                    buttons.append(
                        [InlineKeyboardButton(user_lang.GET_CERTIFICATE_BUTTON.format(first_name=first_name, last_name=last_name), callback_data=f"get_cert|{device.get('id')}|{account_data.get('_id')}")],
                    )

            case "PROCESSING":
                enables_in = datetime.fromisoformat(device.get("attributes", {}).get("addedDate")) + timedelta(days=3, hours=12) - datetime.now(timezone.utc)
                enables_in_seconds = enables_in.total_seconds()
                days, hours, minutes, _ = normalize_time(enables_in_seconds)
                status_string = user_lang.PROCESSING_STATE.format(days=days, hours=hours, minutes=minutes)
            case "REVOKED":
                post_second_row = False
                status_string = user_lang.REVOKED_STATE
            case "EXPIRED":
                post_second_row = False
                status_string = user_lang.EXPIRED_STATE
            case "DISABLED":
                status_string = user_lang.DISABLED_STATE
            case "INELIGIBLE":
                status_string = user_lang.INELIGIBLE_STATE
            case unknown:
                status_string = unknown

        if (is_owner or is_reseller) and post_second_row:
            is_udid_disabled = device.get("disabled") == True
            action = "hlenable" if is_udid_disabled else "hldisable"
            buttons.append(
                [
                    InlineKeyboardButton(user_lang.ENABLE_UDID if is_udid_disabled else user_lang.DISABLE_UDID, callback_data=f"{action}|{device.get('_id')}"),
                    InlineKeyboardButton(user_lang.SHARE_LINK_BUTTON, url=f"tg://msg_url?url=t.me/{context.bot.username}?start=chk{udid}"),
                ]
            )
        device['attributes']['addedDate'] = format_time(device.get("attributes", {}).get("addedDate"))

        device.update(status_string=status_string, udid=udid, first_name=first_name, last_name=last_name)
        status_message += TEMPLATE.format_map(device)
        if no != devices_count:
            status_message += "--------------------------------\n"

        await update.effective_message.reply_text(status_message, reply_markup=InlineKeyboardMarkup(buttons))


@translations.get_lang
@sanitize(entry_point=True)
async def check_udid_prompt(user_lang: LanguagePack, update: Update, context: CallbackContext):
    await update.effective_message.edit_text(user_lang.UDID_PROMPT)
    return CheckUDIDStates.UDID


@translations.get_lang
@sanitize(conversation_state=True)
async def check_udid_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    if update.callback_query:
        udids = [context.match.group(1)]
    else:
        udids = update.effective_message.text.splitlines()

    await update.effective_message.set_reaction(ReactionTypeEmoji("⚡️"))

    for udid in udids[:config.MULTI_UDID_LIMIT]:
        if len(udid) not in {25, 40, 60}:
            await update.effective_message.reply_text(user_lang.INVALID_UDID_ERROR.format(udid=udid))
            continue

        devices = db.udids.find({"attributes.udid": re.compile(udid, re.IGNORECASE)})
        devices_count = await db.udids.count_documents({"attributes.udid": re.compile(udid, re.IGNORECASE)})
        if devices_count == 0:
            await update.effective_message.reply_text(user_lang.UDID_NOT_FOUND_ERROR)
            continue

        async for no, device in aenumerate(devices, start=1):
            status = device.get('attributes', {}).get("status")
            account_data = await db.accounts.find_one({"account_info.id": device.get('account_id')})
            if not account_data:
                logging.info(f"Account not found for UDID: {udid}")
                continue

            post_second_button = True
            is_owner = account_data.get("user_id") == update.effective_user.id
            is_reseller = any(reseller.get("user_id") == update.effective_user.id for reseller in account_data.get("resellers", []))

            first_name = account_data.get("account_info", {}).get("attributes", {}).get("firstName")
            last_name = account_data.get("account_info", {}).get("attributes", {}).get("lastName")
            provision_data = device.get("provision_data")

            if provision_data:
                check_response = await check(base64.b64decode(provision_data.get("profileContent")))
                status = check_response.get("certificate_status")
                entitlements = "\n".join([f"{'✅' if value.get('status') else '❌'} {key}" for key, value in check_response.get('entitlements').items()])
                check_response.update(entitlements=entitlements)
                device.update(**check_response)

            TEMPLATE = user_lang.NORMAL_PROVISION_TEMPLATE
            buttons = []
            match status:
                case "ENABLED":
                    status_string = "Active 🟢"
                    if device.get("provision_data"):
                        TEMPLATE = user_lang.ENABLED_PROVISION_TEMPLATE
                        buttons.append([InlineKeyboardButton(user_lang.GET_CERTIFICATE_BUTTON.format(first_name=first_name, last_name=last_name), callback_data=f"get_cert|{device.get('id')}|{account_data.get('_id')}")])
                case "PROCESSING":
                    enables_in = datetime.fromisoformat(device.get("attributes", {}).get("addedDate")) + timedelta(days=3, hours=12) - datetime.now(timezone.utc)
                    enables_in_seconds = enables_in.total_seconds()
                    days, hours, minutes, _ = normalize_time(enables_in_seconds)
                    status_string = user_lang.PROCESSING_STATE.format(days=days, hours=hours, minutes=minutes)
                case "REVOKED":
                    post_second_button = False
                    status_string = user_lang.REVOKED_STATE
                case "EXPIRED":
                    post_second_button = False
                    status_string = user_lang.EXPIRED_STATE
                case "DISABLED":
                    status_string = user_lang.DISABLED_STATE
                case "INELIGIBLE":
                    status_string = user_lang.INELIGIBLE_STATE
                case unknown:
                    status_string = unknown

            if is_owner or is_reseller and post_second_button:
                is_udid_disabled = device.get("disabled") == True
                action = "hlenable" if is_udid_disabled else "hldisable"
                buttons.append(
                    [
                        InlineKeyboardButton(user_lang.ENABLE_UDID if is_udid_disabled else user_lang.DISABLE_UDID, callback_data=f"{action}|{device.get('_id')}"),
                        InlineKeyboardButton(user_lang.SHARE_LINK_BUTTON, url=f"tg://msg_url?url=t.me/{context.bot.username}?start=chk{udid}"),
                    ]
                )
            device['attributes']['addedDate'] = format_time(device.get("attributes", {}).get("addedDate"))

            device.update(status_string=status_string, udid=udid, first_name=first_name, last_name=last_name)
            status_message = TEMPLATE.format_map(device)

            await update.effective_message.reply_text(status_message, reply_markup=InlineKeyboardMarkup(buttons))

    return ConversationHandler.END


@translations.get_lang
@sanitize()
async def select_device_type(user_lang: LanguagePack, update: Update, context: CallbackContext):
    document_id = context.match.group(1)
    action = context.match.group(2)

    account_data = await db.accounts.find_one({"_id": ObjectId(document_id)})
    ios_devices = account_data.get('ios_count')
    macos_devices = account_data.get('macos_count')

    await update.effective_message.edit_text(user_lang.SELECT_DEVICE_PROMPT, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton(f"iOS ({ios_devices})", callback_data=f"{action}|{document_id}|ios"),
        InlineKeyboardButton(f"Short ({macos_devices})", callback_data=f"{action}|{document_id}|macos")
    ]]))


@translations.get_lang
@sanitize(entry_point=True)
async def keys_select_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    account_id, device_type = context.match.groups()
    context.user_data["account_id"] = account_id
    context.user_data["device_type"] = device_type
    await update.effective_message.edit_text(user_lang.NO_OF_KEYS_PROMPT)
    return GenerateKeyStates.NO_OF_KEYS


@translations.get_lang
@sanitize(conversation_state=True)
async def generate_key(user_lang: LanguagePack, update: Update, context: CallbackContext):
    no_of_keys = update.effective_message.text
    if not no_of_keys.isdigit():
        await update.effective_message.reply_text("Invalid number!")
        return GenerateKeyStates.NO_OF_KEYS

    int_no = int(no_of_keys)
    if int_no > config.MAX_KEYGEN_PER_REQUEST:
        await update.effective_message.reply_text(user_lang.MAX_KEYGEN_LIMIT.format(limit=config.MAX_KEYGEN_PER_REQUEST))
        return GenerateKeyStates.NO_OF_KEYS

    account_id = context.user_data.get("account_id")
    device_type = context.user_data.get("device_type")

    account_info = await db.accounts.find_one({"_id": ObjectId(account_id)})
    if not account_info:
        await update.effective_message.reply_text(user_lang.ACCOUNT_NOT_FOUND)
        return ConversationHandler.END

    first_name = account_info.get("account_info", {}).get("attributes", {}).get("firstName")
    last_name = account_info.get("account_info", {}).get("attributes", {}).get("lastName")
    acc_id = account_info.get("account_id") # apple account id and not mongodb doc id

    links = []
    for no in range(int_no):
        key_id = await db.create_key(user_id=update.effective_user.id, account_id=account_id, device_type=device_type, created_on=datetime.now(timezone.utc))
        links.append("{}. https://t.me/{}?start=key{}".format(no+1, context.bot.username, key_id))

    await update.effective_message.reply_text(
        user_lang.KEY_GENERATED_MESSAGE.format(
            links="\n".join(links),
            acc_id=acc_id,
            device_type=device_type.upper(),
            first_name=first_name,
            last_name=last_name,
        ),
    )
    return ConversationHandler.END


@translations.get_lang
@sanitize(entry_point=True)
async def select_udid(user_lang: LanguagePack, update: Update, context: CallbackContext):
    key = None
    if update.callback_query:
        func = update.effective_message.edit_text
        document_id, device_type = context.match.groups()
    else:
        func = update.effective_message.reply_text
        key = context.match.group(1)

        data = await db.get_active_key(key=key)
        if not data:
            await update.effective_message.reply_text(user_lang.KEY_NOT_FOUND)
            return ConversationHandler.END

        document_id = data.get("account_id")
        device_type = data.get("device_type")

    context.user_data["document_id"] = document_id
    context.user_data["device_type"] = device_type
    context.user_data["key_id"] = key
    await func(user_lang.UDID_PROMPT)
    return RegisterUDIDStates.REGISTER


@translations.get_lang
@sanitize(conversation_state=True)
async def register_udid(user_lang: LanguagePack, update: Update, context: CallbackContext):
    udids = update.effective_message.text
    key_id = context.user_data.get("key_id")

    if key_id:
        statud = await db.set_processing_key(key=key_id)
        if not statud:
            await update.effective_message.reply_text(user_lang.KEY_NOT_FOUND)
            return ConversationHandler.END

    LIMIT = 1 if key_id else config.MULTI_UDID_LIMIT
    for udid in udids.splitlines()[:LIMIT]:
        if len(udid) not in {25, 40, 60}:
            await update.effective_message.reply_text(user_lang.INVALID_UDID_ERROR.format(udid=udid))
            if key_id:
                await db.set_key_active(key=key_id)
            continue

        doc_filter = {
            "_id": ObjectId(context.user_data["document_id"]),
        }
        if not key_id:
            doc_filter.update(
                {
                    "$or": [
                        {"user_id": update.effective_user.id},
                        {"resellers.user_id": update.effective_user.id}
                    ]
                }
            )

        account_data = await db.accounts.find_one(doc_filter)
        if not account_data:
            await update.effective_user.send_message(user_lang.ACCOUNT_NOT_FOUND)
            return

        alert_message = await update.effective_message.reply_text(user_lang.PROCESSING_REGISTER_UDID)
        try:
            apple_account = AppleDeveloperAccount(key_id=account_data["key_id"], issuer_id=account_data["issue_id"], p8_file=base64.b64decode(account_data["p8_file"]))
            device_type = DeviceType.IOS if context.user_data["device_type"] == "ios" else DeviceType.MAC_OS

            register_response = await apple_account.register_udid(udid=udid, device_type=device_type)
            register_response_data = register_response.get('data')

            response = await apple_account.get_udid_info(register_response_data.get("id"))
            response_data = response.get('data')

            buttons = []
            put_send_row_button = True
            status = response_data.get("attributes", {}).get("status")
            first_name = account_data.get("account_info", {}).get("attributes", {}).get("firstName")
            last_name = account_data.get("account_info", {}).get("attributes", {}).get("lastName")

            provision_data, provision_data_dev = {}, {}
            check_response = {}
            TEMPLATE = user_lang.NORMAL_PROVISION_TEMPLATE
            match status:
                case "ENABLED":
                    await alert_message.edit_text(user_lang.CHECKING_UDID_STATUS)
                    TEMPLATE = user_lang.ENABLED_PROVISION_TEMPLATE
                    provision_data = await apple_account.create_provision(certificate_id=account_data.get('certificate_id'), device_id=response_data.get("id"), app_id=account_data.get("app_id"))
                    provision_data_dev = await apple_account.create_provision(certificate_id=account_data.get('certificate_id_dev'), device_id=response_data.get("id"), app_id=account_data.get("app_id"), adhoc=False)
                    check_response = await check(base64.b64decode(provision_data.get("profileContent")))
                    status = check_response.get("certificate_status")
                    entitlements = "\n".join([f"{'✅' if value.get('status') else '❌'} {key}" for key, value in check_response.get('entitlements').items()])
                    check_response.update(entitlements=entitlements)

                    status_string = "Active 🟢"
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                user_lang.GET_CERTIFICATE_BUTTON.format(first_name=first_name, last_name=last_name),
                                callback_data=f"get_cert|{response_data.get('id')}|{account_data.get('_id')}"
                            )
                        ],
                    )

                case "PROCESSING":
                    status_string = user_lang.PROCESSING_STATE.format(days=3, hours=12, minutes=0)
                case "REVOKED":
                    put_send_row_button = False
                    status_string = user_lang.REVOKED_STATE
                case "EXPIRED":
                    put_send_row_button = False
                    status_string = user_lang.EXPIRED_STATE
                case "DISABLED":
                    status_string = user_lang.DISABLED_STATE
                case "INELIGIBLE":
                    status_string = user_lang.INELIGIBLE_STATE
                case unknown:
                    status_string = unknown

            response_data.update(user_id=update.effective_user.id, account_id=account_data.get('account_id'), provision_data=provision_data, provision_data_dev=provision_data_dev, key_used=key_id)
            update_document = await db.udids.find_one_and_update(
                {"id": response_data.get("id")},
                {"$set": response_data},
                upsert=True,
                return_document=True
            )
            if put_send_row_button:
                buttons.append(
                    [
                        InlineKeyboardButton(user_lang.DISABLE_UDID, callback_data=f"hldisable|{update_document.get('_id')}"),
                        InlineKeyboardButton(user_lang.SHARE_LINK_BUTTON, url=f"tg://msg_url?url=t.me/{context.bot.username}?start=chk{udid}"),
                    ]
                )

            response_data['attributes']['addedDate'] = format_time(response_data.get("attributes", {}).get("addedDate"))

            response_data.update(udid=udid, first_name=first_name, last_name=last_name, status_string=status_string, **check_response)

            model = response_data.get("attributes", {}).get("model", "")
            message = TEMPLATE.format_map(response_data)
            message += user_lang.UDID_CHECK_LINK.format(udid=udid, username=context.bot.username)

            await alert_message.edit_text(message, reply_markup=InlineKeyboardMarkup(buttons))

            log_msg = f"New UDID registed by {update.effective_user.mention_html()}\n\nStatus: {status_string}\nUDID: <code>{udid}</code>\nAccount: <b>{escape(first_name)} {escape(last_name)}</b> (<code>{account_data.get('account_id')}</code>)"
            if key_id:
                log_msg += f"\n\nKey Used: {key_id}"
                await db.set_key_data(
                    key=key_id,
                    data={
                        "udid": udid,
                        "status": "used",
                        "dev_account": {
                            "first_name": first_name,
                            "last_name": last_name,
                        },
                        "used_by_user_id": update.effective_user.id,
                        "used_date": datetime.now(timezone.utc),
                        "model": model
                    }
                )
            await send_log(log_msg)

        except errors.Conflict as error_message:
            await alert_message.edit_text(str(error_message))
            # await alert_message.edit_text(user_lang.UDID_ALREADY_REGISTERED.format(udid=udid))
            if key_id:
                await db.set_key_active(key=key_id)

        except errors.Unauthorized as error_message:
            await alert_message.edit_text(str(error_message))
            # await alert_message.edit_text(user_lang.FORBIDDEN_ERROR)
            if key_id:
                await db.set_key_active(key=key_id)

        except errors.ErrorResponse as error_message:
            await alert_message.edit_text(str(error_message))
            # await alert_message.edit_text(user_lang.FORBIDDEN_ERROR)
            if key_id:
                await db.set_key_active(key=key_id)

        except errors.Forbidden as error_message:
            await alert_message.edit_text(str(error_message))
            # await alert_message.edit_text(user_lang.FORBIDDEN_ERROR)
            if key_id:
                await db.set_key_active(key=key_id)

        except Exception:
            logging.exception(f"An error occurred while registering {udid}!")
            await alert_message.edit_text(user_lang.ERROR_REGISTERING_UDID)
            if key_id:
                await db.set_key_active(key=key_id)

    return ConversationHandler.END


@translations.get_lang
@sanitize()
async def list_udids_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    account_id = context.match.group(1)
    key = f"rate_limit:{update.effective_user.id}:account-{account_id}"
    ttl = 25

    is_allowed = await rdb.db.set(key, 1, ex=ttl, nx=True)

    if not is_allowed:
        await update.callback_query.answer(user_lang.SPAM_MESSAGE, show_alert=True)
        return

    await update.effective_message.edit_text(user_lang.EXPORTING_UDIDS_TEXT)
    accounts = await AccountsManager(user_id=update.effective_user.id).list_udids(account_id=ObjectId(account_id), search_resellers=True)
    if not accounts:
        await update.effective_message.edit_text(user_lang.ACCOUNT_NOT_FOUND)
        return

    file = io.StringIO()
    writer = csv.writer(file)
    writer.writerow(["ID", "UDID", "Status", "Device Type", "Devicve Name", "Added on", "Expiry"])
    async for account in accounts:
        account_attributes = account.get('attributes', {})
        provision_attributes = account.get('provision_data', {})
        writer.writerow([
            account.get('id'),
            account_attributes.get('udid'),
            account_attributes.get('status'),
            account_attributes.get('deviceClass'),
            account_attributes.get('model'),
            provision_attributes.get('createdDate'),
            provision_attributes.get('expirationDate')
        ])
    file.seek(0)
    await update.effective_message.reply_document(
        document=InputFile(file, filename="udids.csv"),
    )
    await update.effective_message.delete()


@translations.get_lang
@sanitize()
async def download_certificate_handler(user_lang: LanguagePack, update: Update, context: CallbackContext):
    udid_id = context.match.group(1)
    account_id = context.match.group(2)

    udid_id, account_id = context.match.groups()
    account_data = await db.accounts.find_one({"_id": ObjectId(account_id)})
    if not account_data:
        await update.callback_query.answer("Account not found!", show_alert=True)
        return ConversationHandler.END

    udid_data = await db.udids.find_one({"id": udid_id})
    if not udid_data:
        await update.callback_query.answer(user_lang.CERTIFICATE_NOT_FOUND, show_alert=True)
        return ConversationHandler.END

    if udid_data.get("disabled"):
        await update.callback_query.answer(user_lang.UDID_IS_DISABLED, show_alert=True)
        return ConversationHandler.END

    if not udid_data.get("attributes", {}).get("status") == "ENABLED":
        await update.callback_query.answer(user_lang.UDID_NOT_AVAILABLE, show_alert=True)
        return ConversationHandler.END

    key = f"rate_limit:{update.effective_user.id}:certificate-{udid_id}"
    ttl = 25

    is_allowed = await rdb.db.set(key, 1, ex=ttl, nx=True)

    if not is_allowed:
        await update.callback_query.answer(user_lang.SPAM_MESSAGE, show_alert=True)
        return

    await update.callback_query.answer(user_lang.FETCHING_CERTIFICATE, show_alert=True)
    udid = udid_data.get("attributes", {}).get("udid")
    provision_data = udid_data.get("provision_data")
    provision_data_dev = udid_data.get("provision_data_dev")

    p12_file = account_data.get("p12")
    p12_dev = account_data.get("p12_dev")
    mobile_provision_file = provision_data.get("profileContent")
    devMobileprovision = provision_data_dev.get("profileContent")

    await update.effective_chat.send_action("upload_document")
    files = [
        InputMediaDocument(base64.b64decode(p12_file), filename=f"{udid}.p12"),
        InputMediaDocument(base64.b64decode(p12_dev), filename=f"{udid}-dev.p12"),
        InputMediaDocument(
            base64.b64decode(mobile_provision_file),
            filename=f"{udid}.mobileprovision"
        ),
        InputMediaDocument(
            base64.b64decode(devMobileprovision),
            filename=f"{udid}-dev.mobileprovision",
            caption=user_lang.SIGNED_IPA_CAPTION_MESSAGE.format(password=config.PASSWORD)
        )
    ]
    await update.effective_chat.send_media_group(media=files)

    with TemporaryDirectory(dir="temp") as temp_dir:

        await update.effective_user.send_action("upload_document")

        p12_file_path = os.path.join(temp_dir, f"{udid}.p12")
        with open(p12_file_path, "wb") as opened_file:
            opened_file.write(base64.b64decode(p12_file))

        mobile_provision_file_path = os.path.join(temp_dir, f"{udid}.mobileprovision")
        with open(mobile_provision_file_path, "wb") as opened_file:
            opened_file.write(base64.b64decode(mobile_provision_file))


        signed_apps = {}
        for app in os.listdir("apps"):
            output_app_path = os.path.join(temp_dir, app)
            app_path = os.path.join("apps", app)

            generated_uuid = str(uuid.uuid4())
            bundle_id = f"com.one.{generated_uuid[:3]}"
            command = get_command(
                p12=p12_file_path,
                prov=mobile_provision_file_path,
                ipa=app_path,
                bundle_id=bundle_id,
                output=output_app_path,
                password=config.PASSWORD,
            )

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            stderr = stderr.decode()
            stdout = stdout.decode()

            if not os.path.isfile(output_app_path):
                logging.error(
                    f"[{update.effective_user.id}] Error signing {app}\nError: {stderr}\nOutput: {stdout}"
                )
                continue

            app_name = re.search(r'AppName:\s+(.+)', stdout)
            app_name = app_name.group(1) if app_name else ""

            r2_file_path = os.path.join(generated_uuid, app)
            ipa_url = await r2.upload_file(output_app_path, r2_file_path)

            plist_content = PLIST_TEMPLATE.format(
                url=ipa_url, appname=app_name, package_name=bundle_id
            )
            with io.BytesIO(plist_content.encode()) as plist_bytes:
                plist_file_path = os.path.join(
                    generated_uuid, "plist", app_name + ".plist"
                )
                plist_file_url = await r2.upload_file(
                    plist_bytes, plist_file_path
                )
                short_url_data = await url_shortner(url=f"itms-services://?action=download-manifest&url={plist_file_url}")
            signed_apps[app_name] = f"{config.INSTALL_APP_URL}?startapp={short_url_data.get('code')}&mode=compact"

        signed_app_message = user_lang.IPA_ARE_SIGNED.format(udid=udid)

        buttons = [
            InlineKeyboardButton(text=app_name, url=app_link)
            for app_name, app_link in signed_apps.items()
        ]

        reply_markup = []

        if buttons:
            reply_markup.append(buttons[:2])

        for i in range(2, len(buttons), 3):
            reply_markup.append(buttons[i:i+3])

    await update.effective_chat.send_message(signed_app_message, reply_markup=InlineKeyboardMarkup(reply_markup))

    return ConversationHandler.END


@translations.get_lang
@sanitize()
async def handle_enable_disable_udid(user_lang: LanguagePack, update: Update, context: CallbackContext):
    document_id = context.match.group(1)
    action = context.match.group(2)

    context.user_data["action"] = action
    context.user_data["document_id"] = document_id

    await update.callback_query.edit_message_text(user_lang.UDID_PROMPT)
    return EnableDisableUDID.UDID_PROMPT


@translations.get_lang
@sanitize()
async def handle_udid_response(user_lang: LanguagePack, update: Update, context: CallbackContext):
    action = context.user_data.get("action")
    document_id = context.user_data.get("document_id")

    udids = update.effective_message.text

    account_manager = AccountsManager(user_id=update.effective_user.id)

    account = await account_manager.get_account(ObjectId(document_id))
    if not account:
        await update.effective_message.reply_text(user_lang.ACCOUNT_NOT_FOUND)
        return ConversationHandler.END

    message = user_lang.UDID_ENABLED if action == "enable" else user_lang.UDID_DISABLED

    for udid in udids.split():
        if len(udid) not in {25, 40, 60}:
            await update.effective_message.reply_text(user_lang.INVALID_UDID_ERROR.format(udid=udid))
            continue

        await account_manager.set_udid_status(udid_id=udid, account_id=account.get('account_id'), set_disable=action == "disable")
        await update.effective_message.reply_text(message.format(udid=udid))

    return ConversationHandler.END



@translations.get_lang
@sanitize()
async def handle_udid_response_callback(user_lang: LanguagePack, update: Update, context: CallbackContext):
    action = context.match.group(1)
    document_id = context.match.group(2)

    udid_data = await db.udids.find_one({"_id": ObjectId(document_id)})
    if not udid_data:
        await update.callback_query.answer(user_lang.UDID_NOT_FOUND_ERROR, show_alert=True)
        return

    account_id = udid_data.get("account_id")
    account_data = await db.accounts.find_one({"account_info.id": account_id})

    is_owner = account_data.get("user_id") == update.effective_user.id
    is_reseller = any(reseller.get("user_id") == update.effective_user.id for reseller in account_data.get("resellers", []))

    if not is_owner and not is_reseller:
        await update.callback_query.answer(user_lang.FORBIDDEN_ERROR, show_alert=True)
        return

    is_action_disable = action == "hldisable"
    udid = udid_data.get("attributes", {}).get("udid")

    account_manager = AccountsManager(user_id=update.effective_user.id)
    await account_manager.set_udid_status(udid_id=udid, account_id=account_id, set_disable=is_action_disable)

    next_action = "hlenable" if action == "hldisable" else "hldisable"
    first_name = account_data.get("account_info", {}).get("attributes", {}).get("firstName")
    last_name = account_data.get("account_info", {}).get("attributes", {}).get("lastName")

    status = udid_data.get('attributes', {}).get("status")

    buttons = []
    if status == "ENABLED":
        buttons.append(
            [InlineKeyboardButton(user_lang.GET_CERTIFICATE_BUTTON.format(first_name=first_name, last_name=last_name), callback_data=f"get_cert|{udid_data.get('id')}|{account_data.get('_id')}")]
        )

    if status not in ["EXPIRED", "REVOKED"]:
        buttons.append(
            [
                InlineKeyboardButton(user_lang.ENABLE_UDID if is_action_disable else user_lang.DISABLE_UDID, callback_data=f"{next_action}|{udid_data.get('_id')}"),
                InlineKeyboardButton(user_lang.SHARE_LINK_BUTTON, url=f"tg://msg_url?url=t.me/{context.bot.username}?start=chk{udid}"),
            ]
        )

    await update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
