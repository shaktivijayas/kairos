import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "")
CASH_LIMIT_INR = int(os.environ.get("CASH_LIMIT_INR", "10000"))
GEMMA_MODEL = "gemma-4-31b-it"
