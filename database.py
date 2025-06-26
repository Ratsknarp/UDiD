import uuid
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from r2 import R2Storage
from datetime import datetime
import redis.asyncio as redis

class RedisDatabase:
    def __init__(self, redis_uri: str, redis_password: str=None):
        if redis_password:
            self.db = redis.from_url(url=redis_uri, password=redis_password)
        else:
            self.db = redis.from_url(url=redis_uri)


class Database:
    def __init__(self, db_uri: str, r2: R2Storage):
        self.r2 = r2
        self.client = AsyncIOMotorClient(db_uri)
        self._admin: AsyncIOMotorDatabase = self.client["admin"]
        
        self.cache: AsyncIOMotorCollection = self.client["udid_bot"]["cache"]

        self.keys: AsyncIOMotorCollection = self.client["udid_bot"]["keys"]
        self.users: AsyncIOMotorCollection = self.client["udid_bot"]["users"]
        self.udids: AsyncIOMotorCollection = self.client["udid_bot"]["udids"]

        self.sharing_keys: AsyncIOMotorCollection = self.client["udid_bot"]["sharing_keys"]

        self.accounts: AsyncIOMotorCollection = self.client["udid_bot"]["accounts"]
        self.account_status: AsyncIOMotorCollection = self.client["udid_bot"]["account_status"]


    async def setup(self):
        await self.cache.create_index("expire_at", expireAfterSeconds=0)
        await self.accounts.create_index([("account_info.attributes.firstName", 1)])


    async def get_language(self, user_id: int) -> str:
        user = await self.users.find_one({"user_id": user_id})
        return user.get("language") if user else None


    async def set_language(self, user_id: int, lang: str) -> None:
        await self.users.update_one({"user_id": user_id}, {"$set": {"language": lang}}, upsert=True)


    async def create_key(self, user_id: int, account_id: str, device_type: str, created_on: datetime):
        key_id = uuid.uuid4().hex[:10]
        data = {
            "key_id": key_id,
            "user_id": user_id,
            "account_id": account_id,
            "device_type": device_type,
            "created_on": created_on,
            "status": "active",
        }
        await self.keys.insert_one(data)
        await self.r2.upload_json(data=data, path=f"keys/{key_id}.json")
        return key_id

    async def update_key_status(self, key: str, current_status: str, new_status: str):
        data = await self.keys.find_one_and_update(
            {"key_id": key, "status": current_status},
            {"$set": {"status": new_status}}
        )
        if data:
            await self.r2.upload_json(data=data, path=f"keys/{key}.json")
            return data
        return None

    async def set_processing_key(self, key: str):
        return await self.update_key_status(key, current_status="active", new_status="processing")

    async def set_key_active(self, key: str):
        return await self.update_key_status(key, current_status="processing", new_status="active")

    async def get_active_key(self, key: str):
        return await self.keys.find_one({"key_id": key, "status": "active"})
    
    async def set_key_data(self, key: str, data: dict):
        old_data = await self.keys.find_one({"key_id": key})
        old_data.update(data)
        await self.r2.upload_json(data=old_data, path=f"keys/{key}.json")
        return await self.keys.update_one({"key_id": key}, {"$set": data})
