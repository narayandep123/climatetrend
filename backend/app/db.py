import os
from datetime import datetime
from typing import Any

import mongomock
from pymongo import MongoClient


def get_database() -> Any:
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    else:
        client = mongomock.MongoClient()

    database = client["climate_hazard_db"]
    database.weather_cache.create_index([("cache_key", 1)], unique=True)
    return database


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
