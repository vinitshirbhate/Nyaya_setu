from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient = None
    db = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        mongodb.client = AsyncIOMotorClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=5000
        )
        # Test connection
        await mongodb.client.admin.command('ping')
        mongodb.db = mongodb.client[settings.mongo_db_name]
        logger.info(f"Connected to MongoDB: {settings.mongo_db_name}")
    except ServerSelectionTimeoutError as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Closed MongoDB connection")


def get_database():
    """Get database instance"""
    return mongodb.db