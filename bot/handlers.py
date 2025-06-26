from bot import app, states 
from bot.modules import static, settings, account, udid
from telegram.ext import filters, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler


cancel_handler = CommandHandler(
    command="cancel",
    callback=static.cancel_handler,
)
PRIVATE_CHATS = filters.ChatType.PRIVATE

app.add_handlers(
    [
        MessageHandler(
            callback=static.start_handler,
            filters=filters.Regex("^/(start|cancel)$") & PRIVATE_CHATS
        ),
        CallbackQueryHandler(
            callback=static.start_handler,
            pattern="home",
        ),
        CommandHandler(
            command="udid",
            filters=PRIVATE_CHATS,
            callback=static.get_special_link,
        ),
        CallbackQueryHandler(
            pattern="settings", 
            callback=settings.show_settings_buttons
        ), 
        CommandHandler(
            command="id", 
            filters=PRIVATE_CHATS,
            callback=static.get_user_id
        )
    ], 
    group=20
)

app.add_handler(cancel_handler, group=9)

# settings panel
app.add_handlers(
    [
        CommandHandler(
            command="lang", 
            filters=PRIVATE_CHATS,
            callback=settings.show_languages,
        ),
        CallbackQueryHandler(
            pattern="lang", 
            callback=settings.show_languages
        ),
        CallbackQueryHandler(
            callback=settings.set_language,
            pattern=r"set_lang\|(.+)",
        ),
    ], 
    group=19
)

# accounts handler 
app.add_handlers(
    [
        CallbackQueryHandler(
            callback=udid.select_device_type,
            pattern=r"account\|(.+)\|(register|genkey)",
        ),
        CallbackQueryHandler(
            callback=account.account_list,
            pattern=r"accounts\|(.+)\|(register|genkey|add_partner|remove_partner|enable_udid|list|disable_udid|refresh)",
        )
    ]
)

app.add_handler(
    ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=udid.keys_select_handler,
                pattern="genkey\|(.+)\|(ios|macos)"
            )
        ], 
        states={
            states.GenerateKeyStates.NO_OF_KEYS:[
                cancel_handler,
                MessageHandler(
                    filters=filters.TEXT & ~filters.COMMAND,
                    callback=udid.generate_key
                )
            ]
        },
        fallbacks=[],
        allow_reentry=True
    ), 
    group=15
)

app.add_handler(
    CallbackQueryHandler(
        callback=udid.download_certificate_handler,
        pattern=r"get_cert\|(.+)\|(.+)"
    ),
)
app.add_handler(
    CallbackQueryHandler(
        pattern=r"account\|(.+)\|list", 
        callback=udid.list_udids_handler
    )
)
app.add_handler(
    CallbackQueryHandler(
        pattern=r"account\|(.+)\|refresh",
        callback=account.refresh_account
    )
)

app.add_handler(
    CallbackQueryHandler(
        pattern=r"account\|(.+)\|cnfrefresh",
        callback=account.cnfrefresh_account
    )
)

app.add_handler(
    ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=udid.check_udid_prompt,
                pattern=r"check_status",
            ), 
        ], 
        states={
            states.CheckUDIDStates.UDID: [
                cancel_handler,
                MessageHandler(callback=udid.check_udid_handler, filters=filters.TEXT & ~filters.COMMAND)
            ]
        }, 
        fallbacks=[], 
        allow_reentry=True
    ), 
    group=14
)

app.add_handler(
    ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=udid.select_udid, pattern=r"^register\|(.+)\|(.+)$"
            ), 
            MessageHandler(
                callback=udid.select_udid,
                filters=filters.Regex("^/start key(.+)$")
            )
        ],
        states={
            states.RegisterUDIDStates.REGISTER: [
                cancel_handler,
                MessageHandler(callback=udid.register_udid, filters=filters.TEXT & ~filters.COMMAND)
            ],
        },
        fallbacks=[],
        allow_reentry=True, 
    ),
    group=13
)

app.add_handler(
    ConversationHandler(
        name="import_account",
        persistent=True,
        entry_points=[
            CommandHandler(
                command="import",
                filters=PRIVATE_CHATS,
                callback=account.import_account_handler,
            )
        ],
        states={
            states.ImportAccountStates.KEY_ID: [
                cancel_handler,
                MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=account.key_id_handler)
            ],
            states.ImportAccountStates.ISSUE_ID: [
                cancel_handler,
                MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=account.issue_id_handler)
            ],
            states.ImportAccountStates.P8_FILE: [
                cancel_handler,
                MessageHandler(~filters.COMMAND & filters.Document.ALL, callback=account.p8_file_handler)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    ), 
    group=12
)

app.add_handler(
    ConversationHandler(
        name="enable_disable_udid",
        persistent=True,
        entry_points=[
            CallbackQueryHandler(
                callback=udid.handle_enable_disable_udid,
                pattern=r"account\|(.+)\|(enable|disable)_udid"
            )
        ], 
        states={
            states.EnableDisableUDID.UDID_PROMPT: [
                cancel_handler,
                MessageHandler(callback=udid.handle_udid_response, filters=filters.TEXT & ~filters.COMMAND)
            ]
        }, 
        fallbacks=[], 
        allow_reentry=True
    ), 
    group=11
)
app.add_handler(
    CallbackQueryHandler(
        pattern=r"(hldisable|hlenable)\|(.+)",
        callback=udid.handle_udid_response_callback
    )
)

app.add_handlers([
    CallbackQueryHandler(
        callback=account.get_share_link, 
        pattern=r"account\|(.+)\|add_partner"
    ), 
    CallbackQueryHandler(
        callback=account.list_resellers, 
        pattern=r"account\|(.+)\|remove_partner"
    ),
    CallbackQueryHandler(
        callback=account.remove_reseller, 
        pattern=r"rm_reseller\|(.+)\|(.+)"
    ),
    MessageHandler(
        callback=account.install_account_handler,
        filters=filters.Regex("^/start install-(.+)$")
    )
])

app.add_handlers([
    MessageHandler(
        filters=filters.Regex("^/chk (.+)$") & filters.ChatType.GROUPS, 
        callback=udid.headless_udid_check
    ), 
    MessageHandler(
        filters=filters.Regex("^/start chk(.+)$") & filters.ChatType.PRIVATE, 
        callback=udid.headless_udid_check
    ), 
    CallbackQueryHandler(
        callback=static.inactive_account_handler, 
        pattern="inactive"
    )
])