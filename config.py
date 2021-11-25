import os
from os import getenv
from dotenv import load_dotenv

if os.path.exists("local.env"):
    load_dotenv("local.env")

load_dotenv()
que = {}
SESSION_NAME = getenv("SESSION_NAME", "session")
BOT_TOKEN = getenv("BOT_TOKEN")
BOT_NAME = getenv("BOT_NAME")
BG_IMAGE = getenv("BG_IMAGE", "https://telegra.ph/file/49ac0c33e0f9466934427.jpg")
THUMB_IMG = getenv("THUMB_IMG", "https://telegra.ph/file/49ac0c33e0f9466934427.jpg")
admins = {}
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_USERNAME = getenv("BOT_USERNAME")
ASSISTANT_NAME = getenv("ASSISTANT_NAME")
GROUP_SUPPORT = getenv("GROUP_SUPPORT", "TebBotSupport")
UPDATES_CHANNEL = getenv("UPDATES_CHANNEL", "TebMusicUpdate")
OWNER_NAME = getenv("OWNER_NAME", "Cyberhunt27")
DURATION_LIMIT = int(getenv("DURATION_LIMIT", "240"))

COMMAND_PREFIXES = list(getenv("COMMAND_PREFIXES", "/ ! .").split())

SUDO_USERS = list(map(int, getenv("SUDO_USERS").split()))

DATABASE_URL = os.environ.get("DATABASE_URL")  # fill with your mongodb url
