import jwt
import time
import enum
import uuid
import base64
import aiohttp
import logging
# from bot import db
from api import errors
from database import Database
from api.key import KeyManager
from typing import Optional, Dict, Any, Union


class DeviceType(enum.Enum):
    IOS = "IOS"
    MAC_OS = "MAC_OS"


async def fetch_error_message(response: aiohttp.ClientResponse) -> str:
    try:
        error_response = await response.json(content_type=None)
        return error_response.get('errors', [{}])[0].get("detail", "Failed to retrieve error message")
    except Exception as e:
        print(e)
        try:
            return await response.text()
        except Exception:
            return "Failed to retrieve error message"


class AioHttpClient:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session or aiohttp.ClientSession()

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Union[Dict[str, Any], None]:
        async with self.session.request(
            method=method, url=url, headers=headers, params=params, **kwargs
        ) as response:
            if response.ok:
                if method in ["PUT", "DELETE"]:
                    return
                return await response.json()
            elif response.status == 400:
                error_message = await fetch_error_message(response)
                logging.exception(error_message)
                raise errors.ErrorResponse(error_message)
            elif response.status == 401:
                error_message = await fetch_error_message(response)
                logging.exception(error_message)
                raise errors.Unauthorized(error_message)
            elif response.status == 403:
                error_message = await fetch_error_message(response)
                logging.exception(error_message)
                raise errors.Forbidden(error_message)
            elif response.status == 409:
                error_message = await fetch_error_message(response)
                logging.exception(error_message)
                raise errors.Conflict(error_message)
            else:
                raise Exception(
                    f"[{response.status}] Failed to retrieve data. \nURL : {url}\nHeaders : {headers}\nParameters : {params}\nResponse Text : {await response.text()}"
                )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.session.close()


class AppleDeveloperAccount:
    API_ENDPOINT = "https://api.appstoreconnect.apple.com/v1"

    # you can pick which capabilities you want enabled by default:
    # https://developer.apple.com/documentation/appstoreconnectapi/capabilitytype
    CAPABILITIES = [
    ]

    def __init__(self, key_id: str, issuer_id: str, p8_file: str):
        self.key_id = key_id
        self.p8_file = p8_file
        self.issuer_id = issuer_id

    @property
    def headers(self) -> Dict[str, str]:
        token = self.generate_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def generate_token(self) -> str:
        private_key = self.p8_file
        headers = {"alg": "ES256", "kid": self.key_id, "typ": "JWT"}
        payload = {
            "iss": self.issuer_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 20 * 60,  # Token expires after 20 minutes
            "aud": "appstoreconnect-v1",
            "jti": str(uuid.uuid4()),
        }

        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        return token

    async def get_certificates(self) -> Any:
        url = AppleDeveloperAccount.API_ENDPOINT + "/certificates"
        headers = self.headers

        async with AioHttpClient() as http_client:
            data = await http_client.request("GET", url, headers=headers)
            return data.get("data", [])

    async def get_certificate_info(self, certificate_id: str) -> Any:
        url = AppleDeveloperAccount.API_ENDPOINT + f"/certificates/{certificate_id}"
        headers = self.headers

        async with AioHttpClient() as http_client:
            return await http_client.request("GET", url, headers=headers)

    async def get_devices_info(self, platform: DeviceType) -> Any:
        url = AppleDeveloperAccount.API_ENDPOINT + "/devices"
        headers = self.headers
        params = {"filter[platform]": platform.value, "limit": 200}

        async with AioHttpClient() as http_client:
            data = await http_client.request("GET", url, headers=headers, params=params)
            return data.get("data", [])

    async def get_account_info(self) -> Any:
        url = AppleDeveloperAccount.API_ENDPOINT + "/users"
        headers = self.headers

        async with AioHttpClient() as http_client:
            data = await http_client.request("GET", url, headers=headers)
            return data.get("data", [])


    async def register_udid(self, udid: str, device_type: DeviceType):
        url = AppleDeveloperAccount.API_ENDPOINT + "/devices"
        headers = self.headers
        payload = {
            "data": {
                "type": "devices",
                "attributes": {
                    "name": udid,
                    "platform": device_type.value,
                    "udid": udid
                }
            }
        }
        async with AioHttpClient() as http_client:
            return await http_client.request("POST", url, headers=headers, json=payload)


    async def revoke_existing_certificates(self):
        url = AppleDeveloperAccount.API_ENDPOINT + "/certificates"
        headers = self.headers

        async with AioHttpClient() as http_client:
            data = await http_client.request("GET", url, headers=headers)
            certificates = data.get("data", [])
            for cert in certificates:
                cert_id = cert["id"]
                if cert["attributes"]["certificateType"] in ["IOS_DISTRIBUTION", "IOS_DEVELOPMENT"]:
                    delete_url = f"{url}/{cert_id}"
                    await http_client.request("DELETE", delete_url, headers=headers)

    # formerly create_adhoc_certificate
    async def create_p12_certificates(self, password: str) -> tuple[str, str, str, str]:
        private_key, csr_key = KeyManager.generate_keys()
        private_key_dev, csr_key_dev = KeyManager.generate_keys()
        url = AppleDeveloperAccount.API_ENDPOINT + "/certificates"
        headers = self.headers
        data = {
            "data": {
                "type": "certificates",
                "attributes": {
                    "certificateType": "IOS_DISTRIBUTION",
                    "csrContent": csr_key.decode("utf-8"),
                },
            }
        }

        async with AioHttpClient() as http_client:
            response = await http_client.request("POST", url=url, headers=headers, json=data)
            data["data"]["attributes"] = {"certificateType": "IOS_DEVELOPMENT", "csrContent": csr_key_dev.decode("utf-8")}
            response_dev = await http_client.request("POST", url=url, headers=self.headers, json=data)

            certificate_id = response["data"]["id"]
            cert_content = response["data"]["attributes"]["certificateContent"]

            certificate_id_dev = response_dev["data"]["id"]
            cert_content_dev = response_dev["data"]["attributes"]["certificateContent"]

            pem_file = KeyManager.convert_cert_to_pem(base64.b64decode(cert_content))
            pem_file_dev = KeyManager.convert_cert_to_pem(base64.b64decode(cert_content_dev))

            return (
                certificate_id, KeyManager.generate_p12(key_file=private_key, pem_file=pem_file, password=password),
                certificate_id_dev, KeyManager.generate_p12(key_file=private_key_dev, pem_file=pem_file_dev, password=password)
            )

    async def generate_certificate(self, password: str) -> tuple[str, str, str, str]:
        await self.revoke_existing_certificates()
        return await self.create_p12_certificates(password=password)

    async def create_app_id(self, account_id: str, callback: callable = None, k: int = 5) -> tuple[str, str]:
        url = AppleDeveloperAccount.API_ENDPOINT + "/bundleIds"
        headers = self.headers
        iden = str(uuid.uuid4())
        new_app_payload = {
            "data": {
                "type": "bundleIds",
                "attributes": {
                    "identifier": iden,
                    "name": iden,
                    "platform": "IOS",
                },
            }
        }

        async with AioHttpClient() as http_client:
            try:
                response = await http_client.request("POST", url=url, headers=headers, json=new_app_payload)
            except errors.Conflict:  # shouldnt happen anymore, due to uuid used
                get_bundle_id_payload = {
                    "filter[name]": account_id,
                }
                response = await http_client.request("GET", url=url, headers=headers, params=get_bundle_id_payload)
                for app in response["data"]:
                    app_id = app["id"]
                    delete_bundle_id_url = url + f"/{app_id}"
                    logging.info(f"Deleting existing app id: {app_id}")
                    await http_client.request("DELETE", delete_bundle_id_url, headers=headers)

                response = await http_client.request("POST", url=url, headers=headers, json=new_app_payload)

            app_id = response["data"]["id"]

            capability_url = AppleDeveloperAccount.API_ENDPOINT + "/bundleIdCapabilities"
            capabilities_status = {capabilty: False for capabilty in AppleDeveloperAccount.CAPABILITIES}
            for no, capability in enumerate(AppleDeveloperAccount.CAPABILITIES, start=1):
                payload = {
                    "data": {
                        "type": "bundleIdCapabilities",
                        "attributes": {"capabilityType": capability, "settings": []},
                        "relationships": {
                            "bundleId": {"data": {"type": "bundleIds", "id": app_id}}
                        },
                    }
                }
                await http_client.request("POST", url=capability_url, headers=headers, json=payload)
                capabilities_status[capability] = True

                if callback and callable(callback):
                    total_capabilities = len(AppleDeveloperAccount.CAPABILITIES)
                    if (no % k == 0) or (no == total_capabilities):
                        try:
                            await callback(capabilities_status=capabilities_status)
                        except Exception as e:
                            logging.exception(f"Error executing callable: {e}")

            return app_id, iden

    async def create_provision(self, certificate_id: str, device_id: str, app_id: str, adhoc: bool = True) -> dict:
        profile_url = AppleDeveloperAccount.API_ENDPOINT + "/profiles"
        headers = self.headers
        profileType = "IOS_APP_ADHOC" if adhoc else "IOS_APP_DEVELOPMENT"

        async with AioHttpClient() as http_client:
            attributes = {
                "name": str(uuid.uuid4()).replace('-', '0')[:16],
                "profileType": profileType
            }

            relationships = {
                "bundleId": {
                    "data": {
                        "id": app_id,
                        "type": "bundleIds"
                    }
                },
                "certificates": {
                    "data": [
                        {
                            "id": certificate_id,
                            "type": "certificates"
                        }
                    ]
                },
                "devices": {
                    "data": [
                        {
                            "id": device_id,
                            "type": "devices"
                        }
                    ]
                }
            }

            payload = {
                "data": {
                    "attributes": attributes,
                    "relationships": relationships,
                    "type": "profiles"
                }
            }

            profile_data = await http_client.request("POST", url=profile_url, headers=headers, json=payload)
            return profile_data['data']['attributes']


    async def enable_udid(self, udid_id: str) -> dict:
        url = AppleDeveloperAccount.API_ENDPOINT + f"/devices/{udid_id}"
        headers = self.headers

        payload = {
            "data": {
                "id": udid_id,
                "type": "devices",
                "attributes": {
                    "status": "ENABLED"
                }
            }
        }

        async with AioHttpClient() as http_client:
            return await http_client.request("PATCH", url, headers=headers, json=payload)


    async def get_udid_info(self, udid_id: str) -> dict:
        url = AppleDeveloperAccount.API_ENDPOINT + f"/devices/{udid_id}"
        headers = self.headers

        async with AioHttpClient() as http_client:
            return await http_client.request("GET", url, headers=headers)


class AccountsManager:
    db: Database

    def __init__(self, user_id: int):
        self.user_id = user_id

    def accounts(self, search_resellers: bool = False):
        if search_resellers:
            return self.db.accounts.find({
                "$or": [
                    {"user_id": self.user_id},
                    {"resellers.user_id": self.user_id}
                ]
            })
        else:
            return self.db.accounts.find({"user_id": self.user_id})


    async def list_udids(self, account_id: str, additional_filters: dict = {}, search_resellers: bool = False):
        filter = {"_id": account_id, "user_id": self.user_id}
        if search_resellers:
            filter = {"_id": account_id, "$or": [
                {"user_id": self.user_id},
                {"resellers.user_id": self.user_id}
            ]}
        account = await self.db.accounts.find_one(filter)
        if not account:
            return None

        filter_argument = {"account_id": account.get('account_id')}
        if additional_filters:
            filter_argument.update(additional_filters)

        return self.db.udids.find(filter_argument)

    async def set_udid_status(self, udid_id: str, set_disable: bool, account_id: str):
        filter = {"attributes.udid": udid_id, "account_id": account_id}
        if set_disable:
            update = {"$set": {"disabled": True}}
        else:
            update = {"$unset": {"disabled": ""}}

        await self.db.udids.update_one(filter, update)

    async def get_account(self, doc_id: str, search_resellers: bool = False):
        filter = {"_id": doc_id, "user_id": self.user_id}
        if search_resellers:
            filter = {"_id": doc_id, "$or": [
                {"user_id": self.user_id},
                {"resellers.user_id": self.user_id}
            ]}
        return await self.db.accounts.find_one(filter)

    async def total_accounts_count(self, allow_reseller: bool = False):
        if allow_reseller:
            return await self.db.accounts.count_documents({"$or": [
                {"user_id": self.user_id},
                {"resellers.user_id": self.user_id}
            ]})
        else:
            return await self.db.accounts.count_documents({"user_id": self.user_id})

    async def pagination(self, start_page: int = 0, per_page: int = 15, allow_reseller: bool = False):
        if start_page < 0:
            start_page = 0

        if per_page < 1:
            per_page = 15

        accounts = self.accounts(search_resellers=allow_reseller)
        total_accounts = await self.total_accounts_count(allow_reseller=allow_reseller)

        next_page_no = start_page + 1 if (start_page + 1) * per_page < total_accounts else None
        prev_page_no = start_page - 1 if start_page > 0 else None

        accounts = accounts.sort("account_info.attributes.firstName").skip(start_page * per_page).limit(per_page)

        return accounts, next_page_no, prev_page_no, total_accounts/per_page
