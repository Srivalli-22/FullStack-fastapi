import os
from dotenv import load_dotenv

load_dotenv()  # load variables from the project-level .env file if present

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret_jwt_key_change_this")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
DEVICE_TOPIC = os.getenv("DEVICE_TOPIC", "device_data")

# MongoDB configuration – the URI must come from .env / environment
MONGODB_URL = os.getenv("MONGO_URI")
MONGODB_DB = "scmxpertlite"
