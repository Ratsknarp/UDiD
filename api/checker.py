import io
import json
import time
import config
import base64
import asyncio
import logging
from database import Database
from api import AppleDeveloperAccount, DeviceType

status_r2 = config.STATUS_R2

class AccountChecker:
    def __init__(self, db: Database, delay: int = 60*60):
        self.db = db
        self.delay = delay

    async def fetch_accounts(self):
        return self.db.accounts.find({"inactive": {"$ne": True}})

    async def check_udids(self, account_data: dict):
        dev_account = AppleDeveloperAccount(
            key_id=account_data["key_id"],
            issuer_id=account_data["issue_id"],
            p8_file=base64.b64decode(account_data["p8_file"]),
        )
        try:
            ios_devices = await dev_account.get_devices_info(DeviceType.IOS)
            mac_devices = await dev_account.get_devices_info(DeviceType.MAC_OS)
            await self.db.accounts.update_one({"_id": account_data["_id"]}, {"$set": {"ios_count": len(ios_devices), "macos_count": len(mac_devices)}})
            pending_udids = self.db.udids.find({
                "account_id": account_data.get("account_info", {}).get("id"),
                "attributes.status": {"$in": ["PROCESSING", "INELIGIBLE"]}
            })
            async for udid in pending_udids:
                try:
                    udid_status_response = await dev_account.get_udid_info(udid.get("id"))
                    udid_status = udid_status_response.get("data", {})

                    status = udid_status.get("attributes", {}).get("status")

                    if status == "ENABLED":
                        udid_status["provision_data"] = await dev_account.create_provision(certificate_id=account_data.get('certificate_id'), device_id=udid_status.get("id"), app_id=account_data.get("app_id"))
                        udid_status["provision_data_dev"] = await dev_account.create_provision(certificate_id=account_data.get('certificate_id_dev'), device_id=udid_status.get("id"), app_id=account_data.get("app_id"), adhoc=False)

                    await self.db.udids.update_one({"_id": udid["_id"]}, {"$set": udid_status})
                except Exception:
                    logging.exception(f"Error while updating udid ({udid.get('id')}) in account {account_data['_id']}")

        # except errors.Unauthorized:
        #     await self.db.accounts.update_one({"_id": account_data["_id"]}, {"$set": {"inactive": True}})
        except Exception:
            logging.exception(f"Error while checking account {account_data['_id']}")


    # async def check_account(self, account_data: dict):
    #     p12_file = base64.b64decode(account_data["p12"])
    #     p12_password = config.PASSWORD

    #     check_status = check(
    #         p12_bytes=p12_file,
    #         password=p12_password,
    #     )
    #     attributes = account_data.get("account_info", {}).get('attributes', {})
    #     first_name = attributes.get("firstName")
    #     last_name = attributes.get("lastName")
    #     status = check_status.get('certificate_status') == "ENABLED"
    #     await self.db.account_status.update_one({"pname": f"{first_name} {last_name}"}, {"$set": {"status": status}}, upsert=True)


    async def start_checking(self):
        logging.info("Starting account checker...")
        try:
            accounts = await self.fetch_accounts()
            t = time.time()

            account_list = [account async for account in accounts]
            logging.info(f"Checking {len(account_list)} accounts...")

            tasks = [self.check_udids(account) for account in account_list]
            await asyncio.gather(*tasks)

            # account_tasks = [self.check_account(account) for account in account_list]
            # await asyncio.gather(*account_tasks)

            # data = {
            #     "status": [],
            #     "last_checked_at": datetime.now(timezone.utc).timestamp()
            # }

            # all_certificates = self.db.account_status.find({}, {"_id": 0})
            # async for certificate in all_certificates:
            #     data["status"].append(certificate)

            # with io.BytesIO(json.dumps(data).encode()) as data_stream:
            #     url = await status_r2.upload_file(file=data_stream, path="certificates2.json")
            #     logging.debug(f"Uploaded data to {url}")

            logging.info(f"Checked {len(tasks)} accounts in {time.time() - t} seconds!")
        except Exception:
            logging.exception("An error occurred")
