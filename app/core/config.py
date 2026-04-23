import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")

settings = Settings()
