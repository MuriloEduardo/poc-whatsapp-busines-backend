import os
import pymongo
from ConnectionManager import ConnectionManager

MONGO_DB_URL = os.getenv('MONGO_DB_URL')

manager = ConnectionManager()
mongo_client = pymongo.MongoClient(MONGO_DB_URL)


def get_manager():
    return manager


def get_mongo():
    return mongo_client
