from pymongo import MongoClient

from app.config import settings

client = None
db = None


def connect():
    global client, db
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")
    db = client.get_default_database()
    db.users.create_index("googleId", unique=True)
    db.folders.create_index([("userId", 1), ("slug", 1)], unique=True)
    db.notes.create_index([("userId", 1), ("folderId", 1)])
    db.import_jobs.create_index("userId")
    return db
