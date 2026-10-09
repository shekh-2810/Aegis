import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set. Create a .env file with your MongoDB Atlas connection string.")

client = MongoClient(MONGO_URI)
db = client["aiges"]

articles_collection = db["articles"]
alerts_collection = db["alerts"]
subscribers_collection = db["subscribers"]
users_collection = db["users"]
incidents_collection = db["incidents"]
detections_collection = db["detections"]

users_collection.create_index("email", unique=True)
incidents_collection.create_index("tracking_code", unique=True)
detections_collection.create_index("domain", unique=True)
# Cached detection results expire automatically 24 hours after they were
# written, so a repeated scan of the same domain re-checks it daily.
detections_collection.create_index("checked_at", expireAfterSeconds=86400)


def get_database():
    return db
