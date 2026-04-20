{\rtf1\ansi\ansicpg1251\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import os\
import logging\
from datetime import datetime\
from typing import Optional\
\
from dotenv import load_dotenv\
from openai import OpenAI\
import gspread\
from google.oauth2.service_account import Credentials\
from telegram import Update\
from telegram.constants import ChatAction\
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters\
\
\
# =========================\
# CONFIG\
# =========================\
load_dotenv()\
\
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")\
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")\
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")\
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")\
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")\
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")  # optional\
\
SYSTEM_PROMPT = """\uc0\u1058 \u1099  \'97 \u1091 \u1085 \u1080 \u1074 \u1077 \u1088 \u1089 \u1072 \u1083 \u1100 \u1085 \u1099 \u1081  \u1086 \u1087 \u1077 \u1088 \u1072 \u1094 \u1080 \u1086 \u1085 \u1085 \u1099 \u1081  \u1087 \u1086 \u1084 \u1086 \u1097 \u1085 \u1080 \u1082  Beshir \u1074  Telegram.\
\
\uc0\u1058 \u1074 \u1086 \u1103  \u1088 \u1086 \u1083 \u1100 :\
- \uc0\u1087 \u1086 \u1084 \u1086 \u1075 \u1072 \u1090 \u1100  \u1089  \u1087 \u1088 \u1086 \u1076 \u1072 \u1078 \u1072 \u1084 \u1080 , \u1087 \u1080 \u1089 \u1100 \u1084 \u1072 \u1084 \u1080 , follow-up, \u1082 \u1086 \u1084 \u1084 \u1077 \u1088 \u1095 \u1077 \u1089 \u1082 \u1080 \u1084 \u1080  \u1087 \u1088 \u1077 \u1076 \u1083 \u1086 \u1078 \u1077 \u1085 \u1080 \u1103 \u1084 \u1080 \
- \uc0\u1087 \u1086 \u1084 \u1086 \u1075 \u1072 \u1090 \u1100  \u1089  \u1086 \u1087 \u1077 \u1088 \u1072 \u1094 \u1080 \u1086 \u1085 \u1085 \u1099 \u1084 \u1080  \u1079 \u1072 \u1076 \u1072 \u1095 \u1072 \u1084 \u1080 , \u1086 \u1090 \u1095 \u1077 \u1090 \u1072 \u1084 \u1080 , summaries, \u1087 \u1086 \u1088 \u1091 \u1095 \u1077 \u1085 \u1080 \u1103 \u1084 \u1080 \
- \uc0\u1086 \u1090 \u1074 \u1077 \u1095 \u1072 \u1090 \u1100  \u1095 \u1077 \u1090 \u1082 \u1086 , \u1087 \u1086  \u1076 \u1077 \u1083 \u1091  \u1080  \u1089 \u1090 \u1088 \u1091 \u1082 \u1090 \u1091 \u1088 \u1085 \u1086 \
- \uc0\u1077 \u1089 \u1083 \u1080  \u1079 \u1072 \u1076 \u1072 \u1095 \u1072  \u1085 \u1077 \u1086 \u1076 \u1085 \u1086 \u1079 \u1085 \u1072 \u1095 \u1085 \u1072 , \u1089 \u1085 \u1072 \u1095 \u1072 \u1083 \u1072  \u1089 \u1076 \u1077 \u1083 \u1072 \u1081  \u1083 \u1091 \u1095 \u1096 \u1077 \u1077  \u1087 \u1088 \u1077 \u1076 \u1087 \u1086 \u1083 \u1086 \u1078 \u1077 \u1085 \u1080 \u1077  \u1080  \u1087 \u1088 \u1077 \u1076 \u1083 \u1086 \u1078 \u1080  \u1091 \u1083 \u1091 \u1095 \u1096 \u1077 \u1085 \u1085 \u1091 \u1102  \u1074 \u1077 \u1088 \u1089 \u1080 \u1102 \
- \uc0\u1077 \u1089 \u1083 \u1080  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1100  \u1087 \u1088 \u1086 \u1089 \u1080 \u1090  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077 /\u1087 \u1080 \u1089 \u1100 \u1084 \u1086 , \u1089 \u1088 \u1072 \u1079 \u1091  \u1076 \u1072 \u1081  \u1075 \u1086 \u1090 \u1086 \u1074 \u1099 \u1081  \u1090 \u1077 \u1082 \u1089 \u1090  \u1076 \u1083 \u1103  \u1086 \u1090 \u1087 \u1088 \u1072 \u1074 \u1082 \u1080 \
- \uc0\u1077 \u1089 \u1083 \u1080  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1100  \u1087 \u1088 \u1086 \u1089 \u1080 \u1090  \u1086 \u1090 \u1095 \u1077 \u1090 , \u1076 \u1072 \u1081  \u1082 \u1086 \u1088 \u1086 \u1090 \u1082 \u1091 \u1102  \u1091 \u1087 \u1088 \u1072 \u1074 \u1083 \u1077 \u1085 \u1095 \u1077 \u1089 \u1082 \u1091 \u1102  \u1074 \u1077 \u1088 \u1089 \u1080 \u1102 \
- \uc0\u1077 \u1089 \u1083 \u1080  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1100  \u1087 \u1088 \u1086 \u1089 \u1080 \u1090  \u1087 \u1083 \u1072 \u1085 , \u1076 \u1072 \u1081  \u1082 \u1086 \u1085 \u1082 \u1088 \u1077 \u1090 \u1085 \u1099 \u1077  \u1096 \u1072 \u1075 \u1080 \
\
\uc0\u1060 \u1086 \u1088 \u1084 \u1072 \u1090  \u1086 \u1090 \u1074 \u1077 \u1090 \u1086 \u1074 :\
- \uc0\u1073 \u1077 \u1079  \u1074 \u1086 \u1076 \u1099 \
- \uc0\u1089  \u1072 \u1082 \u1094 \u1077 \u1085 \u1090 \u1086 \u1084  \u1085 \u1072  \u1087 \u1088 \u1072 \u1082 \u1090 \u1080 \u1095 \u1077 \u1089 \u1082 \u1080 \u1081  \u1088 \u1077 \u1079 \u1091 \u1083 \u1100 \u1090 \u1072 \u1090 \
- \uc0\u1075 \u1076 \u1077  \u1091 \u1084 \u1077 \u1089 \u1090 \u1085 \u1086 , \u1080 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1091 \u1081  \u1079 \u1072 \u1075 \u1086 \u1083 \u1086 \u1074 \u1082 \u1080  \u1080  \u1082 \u1086 \u1088 \u1086 \u1090 \u1082 \u1080 \u1077  \u1089 \u1087 \u1080 \u1089 \u1082 \u1080 \
- \uc0\u1087 \u1080 \u1096 \u1080  \u1085 \u1072  \u1090 \u1086 \u1084  \u1103 \u1079 \u1099 \u1082 \u1077 , \u1085 \u1072  \u1082 \u1086 \u1090 \u1086 \u1088 \u1086 \u1084  \u1087 \u1080 \u1096 \u1077 \u1090  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1100 \
"""\
\
logging.basicConfig(\
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",\
    level=logging.INFO,\
)\
logger = logging.getLogger(__name__)\
\
\
# =========================\
# OPENAI\
# =========================\
def get_openai_client() -> OpenAI:\
    if not OPENAI_API_KEY:\
        raise ValueError("OPENAI_API_KEY is missing")\
    return OpenAI(api_key=OPENAI_API_KEY)\
\
\
def ask_openai(user_text: str, user_name: str = "User") -> str:\
    client = get_openai_client()\
\
    response = client.responses.create(\
        model=OPENAI_MODEL,\
        input=[\
            \{"role": "system", "content": SYSTEM_PROMPT\},\
            \{\
                "role": "user",\
                "content": f"\uc0\u1048 \u1084 \u1103  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1103 : \{user_name\}\\n\u1047 \u1072 \u1076 \u1072 \u1095 \u1072 : \{user_text\}",\
            \},\
        ],\
    )\
\
    return response.output_text.strip()\
\
\
# =========================\
# GOOGLE SHEETS\
# =========================\
def get_worksheet():\
    if not GOOGLE_SHEETS_ID:\
        raise ValueError("GOOGLE_SHEETS_ID is missing")\
\
    scopes = [\
        "https://www.googleapis.com/auth/spreadsheets",\
        "https://www.googleapis.com/auth/drive",\
    ]\
\
    creds = Credentials.from_service_account_file(\
        GOOGLE_SERVICE_ACCOUNT_FILE,\
        scopes=scopes,\
    )\
    gc = gspread.authorize(creds)\
    sh = gc.open_by_key(GOOGLE_SHEETS_ID)\
\
    try:\
        ws = sh.worksheet("tasks")\
    except gspread.WorksheetNotFound:\
        ws = sh.add_worksheet(title="tasks", rows=1000, cols=12)\
        ws.append_row(\
            [\
                "timestamp",\
                "telegram_user_id",\
                "username",\
                "full_name",\
                "chat_id",\
                "message_text",\
                "ai_response",\
                "status",\
                "category",\
                "priority",\
                "notes",\
                "source",\
            ]\
        )\
    return ws\
\
\
def detect_category(text: str) -> str:\
    t = text.lower()\
    if any(x in t for x in ["\uc0\u1086 \u1090 \u1095 \u1077 \u1090 ", "report", "summary", "summarize", "\u1088 \u1077 \u1079 \u1102 \u1084 \u1077 "]):\
        return "reporting"\
    if any(x in t for x in ["\uc0\u1087 \u1080 \u1089 \u1100 \u1084 \u1086 ", "email", "follow-up", "follow up", "reply", "\u1086 \u1090 \u1074 \u1077 \u1090 "]):\
        return "communication"\
    if any(x in t for x in ["\uc0\u1083 \u1080 \u1076 ", "lead", "client", "\u1082 \u1083 \u1080 \u1077 \u1085 \u1090 ", "sales", "\u1087 \u1088 \u1086 \u1076 \u1072 \u1078 "]):\
        return "sales"\
    if any(x in t for x in ["\uc0\u1079 \u1072 \u1076 \u1072 \u1095 \u1072 ", "task", "todo", "\u1085 \u1072 \u1087 \u1086 \u1084 \u1085 \u1080 ", "remind"]):\
        return "operations"\
    return "general"\
\
\
def detect_priority(text: str) -> str:\
    t = text.lower()\
    if any(x in t for x in ["\uc0\u1089 \u1088 \u1086 \u1095 \u1085 \u1086 ", "urgent", "asap", "\u1085 \u1077 \u1084 \u1077 \u1076 \u1083 \u1077 \u1085 \u1085 \u1086 "]):\
        return "high"\
    if any(x in t for x in ["\uc0\u1089 \u1077 \u1075 \u1086 \u1076 \u1085 \u1103 ", "today", "\u1076 \u1086  \u1074 \u1077 \u1095 \u1077 \u1088 \u1072 "]):\
        return "medium"\
    return "normal"\
\
\
def log_to_sheets(\
    telegram_user_id: str,\
    username: str,\
    full_name: str,\
    chat_id: str,\
    message_text: str,\
    ai_response: str,\
    status: str = "done",\
    notes: str = "",\
    source: str = "telegram",\
) -> None:\
    ws = get_worksheet()\
    ws.append_row(\
        [\
            datetime.utcnow().isoformat(),\
            telegram_user_id,\
            username,\
            full_name,\
            chat_id,\
            message_text,\
            ai_response,\
            status,\
            detect_category(message_text),\
            detect_priority(message_text),\
            notes,\
            source,\
        ]\
    )\
\
\
# =========================\
# TELEGRAM HELPERS\
# =========================\
def is_admin(update: Update) -> bool:\
    if not ADMIN_TELEGRAM_ID:\
        return True\
    return str(update.effective_user.id) == str(ADMIN_TELEGRAM_ID)\
\
\
async def safe_reply(update: Update, text: str) -> None:\
    max_len = 4000\
    if len(text) <= max_len:\
        await update.message.reply_text(text)\
        return\
\
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]\
    for chunk in chunks:\
        await update.message.reply_text(chunk)\
\
\
# =========================\
# COMMANDS\
# =========================\
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\
    if not is_admin(update):\
        await update.message.reply_text("\uc0\u1059  \u1074 \u1072 \u1089  \u1085 \u1077 \u1090  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1072  \u1082  \u1101 \u1090 \u1086 \u1084 \u1091  \u1073 \u1086 \u1090 \u1091 .")\
        return\
\
    text = (\
        "\uc0\u1055 \u1088 \u1080 \u1074 \u1077 \u1090 . \u1071  \u1090 \u1074 \u1086 \u1081  \u1086 \u1087 \u1077 \u1088 \u1072 \u1094 \u1080 \u1086 \u1085 \u1085 \u1099 \u1081  \u1087 \u1086 \u1084 \u1086 \u1097 \u1085 \u1080 \u1082 .\\n\\n"\
        "\uc0\u1063 \u1090 \u1086  \u1103  \u1091 \u1084 \u1077 \u1102 :\\n"\
        "- \uc0\u1087 \u1080 \u1089 \u1072 \u1090 \u1100  \u1087 \u1080 \u1089 \u1100 \u1084 \u1072  \u1080  follow-up\\n"\
        "- \uc0\u1076 \u1077 \u1083 \u1072 \u1090 \u1100  summaries \u1080  \u1086 \u1090 \u1095 \u1077 \u1090 \u1099 \\n"\
        "- \uc0\u1087 \u1086 \u1084 \u1086 \u1075 \u1072 \u1090 \u1100  \u1089  \u1087 \u1088 \u1086 \u1076 \u1072 \u1078 \u1072 \u1084 \u1080  \u1080  \u1079 \u1072 \u1076 \u1072 \u1095 \u1072 \u1084 \u1080 \\n"\
        "- \uc0\u1089 \u1086 \u1093 \u1088 \u1072 \u1085 \u1103 \u1090 \u1100  \u1086 \u1073 \u1088 \u1072 \u1097 \u1077 \u1085 \u1080 \u1103  \u1074  Google Sheets\\n\\n"\
        "\uc0\u1055 \u1088 \u1080 \u1084 \u1077 \u1088 \u1099 :\\n"\
        "\'95 \uc0\u1053 \u1072 \u1087 \u1080 \u1096 \u1080  follow-up \u1082 \u1083 \u1080 \u1077 \u1085 \u1090 \u1091  \u1087 \u1086 \u1089 \u1083 \u1077  \u1074 \u1089 \u1090 \u1088 \u1077 \u1095 \u1080 \\n"\
        "\'95 \uc0\u1057 \u1076 \u1077 \u1083 \u1072 \u1081  \u1082 \u1088 \u1072 \u1090 \u1082 \u1080 \u1081  weekly sales report\\n"\
        "\'95 \uc0\u1055 \u1086 \u1076 \u1075 \u1086 \u1090 \u1086 \u1074 \u1100  \u1082 \u1086 \u1084 \u1084 \u1077 \u1088 \u1095 \u1077 \u1089 \u1082 \u1086 \u1077  \u1087 \u1088 \u1077 \u1076 \u1083 \u1086 \u1078 \u1077 \u1085 \u1080 \u1077 \\n"\
        "\'95 \uc0\u1057 \u1086 \u1089 \u1090 \u1072 \u1074 \u1100  \u1087 \u1083 \u1072 \u1085  \u1079 \u1072 \u1076 \u1072 \u1095  \u1085 \u1072  \u1089 \u1077 \u1075 \u1086 \u1076 \u1085 \u1103 "\
    )\
    await update.message.reply_text(text)\
\
\
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\
    if not is_admin(update):\
        await update.message.reply_text("\uc0\u1059  \u1074 \u1072 \u1089  \u1085 \u1077 \u1090  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1072  \u1082  \u1101 \u1090 \u1086 \u1084 \u1091  \u1073 \u1086 \u1090 \u1091 .")\
        return\
\
    await update.message.reply_text(\
        "\uc0\u1050 \u1086 \u1084 \u1072 \u1085 \u1076 \u1099 :\\n"\
        "/start \'97 \uc0\u1079 \u1072 \u1087 \u1091 \u1089 \u1082 \\n"\
        "/help \'97 \uc0\u1087 \u1086 \u1084 \u1086 \u1097 \u1100 \\n"\
        "/ping \'97 \uc0\u1087 \u1088 \u1086 \u1074 \u1077 \u1088 \u1082 \u1072 \\n"\
        "/last \'97 \uc0\u1087 \u1086 \u1082 \u1072 \u1079 \u1072 \u1090 \u1100  \u1087 \u1086 \u1089 \u1083 \u1077 \u1076 \u1085 \u1102 \u1102  \u1079 \u1072 \u1087 \u1080 \u1089 \u1100  \u1080 \u1079  \u1083 \u1086 \u1075 \u1080 \u1082 \u1080  \u1085 \u1077  \u1088 \u1077 \u1072 \u1083 \u1080 \u1079 \u1086 \u1074 \u1072 \u1085 \u1086 \\n\\n"\
        "\uc0\u1048 \u1083 \u1080  \u1087 \u1088 \u1086 \u1089 \u1090 \u1086  \u1085 \u1072 \u1087 \u1080 \u1096 \u1080  \u1079 \u1072 \u1076 \u1072 \u1095 \u1091  \u1086 \u1073 \u1099 \u1095 \u1085 \u1099 \u1084  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077 \u1084 ."\
    )\
\
\
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\
    if not is_admin(update):\
        await update.message.reply_text("\uc0\u1059  \u1074 \u1072 \u1089  \u1085 \u1077 \u1090  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1072  \u1082  \u1101 \u1090 \u1086 \u1084 \u1091  \u1073 \u1086 \u1090 \u1091 .")\
        return\
\
    await update.message.reply_text("\uc0\u1041 \u1086 \u1090  \u1088 \u1072 \u1073 \u1086 \u1090 \u1072 \u1077 \u1090 .")\
\
\
# =========================\
# MAIN MESSAGE HANDLER\
# =========================\
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\
    if not update.message or not update.effective_user:\
        return\
\
    if not is_admin(update):\
        await update.message.reply_text("\uc0\u1059  \u1074 \u1072 \u1089  \u1085 \u1077 \u1090  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1072  \u1082  \u1101 \u1090 \u1086 \u1084 \u1091  \u1073 \u1086 \u1090 \u1091 .")\
        return\
\
    user = update.effective_user\
    user_text = update.message.text or ""\
\
    if not user_text.strip():\
        await update.message.reply_text("\uc0\u1055 \u1088 \u1080 \u1096 \u1083 \u1080  \u1090 \u1077 \u1082 \u1089 \u1090 \u1086 \u1074 \u1091 \u1102  \u1079 \u1072 \u1076 \u1072 \u1095 \u1091 .")\
        return\
\
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)\
\
    try:\
        ai_response = ask_openai(\
            user_text=user_text,\
            user_name=user.full_name or user.username or "User",\
        )\
\
        await safe_reply(update, ai_response)\
\
        log_to_sheets(\
            telegram_user_id=str(user.id),\
            username=user.username or "",\
            full_name=user.full_name or "",\
            chat_id=str(update.effective_chat.id),\
            message_text=user_text,\
            ai_response=ai_response,\
        )\
\
    except Exception as e:\
        logger.exception("Error while processing message")\
        error_text = f"\uc0\u1054 \u1096 \u1080 \u1073 \u1082 \u1072 : \{str(e)\}"\
        await update.message.reply_text(error_text)\
\
        try:\
            log_to_sheets(\
                telegram_user_id=str(user.id),\
                username=user.username or "",\
                full_name=user.full_name or "",\
                chat_id=str(update.effective_chat.id),\
                message_text=user_text,\
                ai_response=error_text,\
                status="error",\
                notes="processing_failed",\
            )\
        except Exception:\
            logger.exception("Failed to write error log to sheets")\
\
\
# =========================\
# ENTRYPOINT\
# =========================\
def validate_env() -> None:\
    missing = []\
    for key, value in \{\
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,\
        "OPENAI_API_KEY": OPENAI_API_KEY,\
        "GOOGLE_SHEETS_ID": GOOGLE_SHEETS_ID,\
    \}.items():\
        if not value:\
            missing.append(key)\
\
    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):\
        missing.append(f"GOOGLE_SERVICE_ACCOUNT_FILE file not found: \{GOOGLE_SERVICE_ACCOUNT_FILE\}")\
\
    if missing:\
        raise ValueError("Missing config: " + ", ".join(missing))\
\
\
def main() -> None:\
    validate_env()\
\
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()\
\
    app.add_handler(CommandHandler("start", start))\
    app.add_handler(CommandHandler("help", help_command))\
    app.add_handler(CommandHandler("ping", ping))\
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))\
\
    logger.info("Bot is running...")\
    app.run_polling()\
\
\
if __name__ == "__main__":\
    main()\
}