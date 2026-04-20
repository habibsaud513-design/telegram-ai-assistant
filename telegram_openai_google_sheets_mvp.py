import os
import logging
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters


# =========================
# CONFIG
# =========================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")  # optional

SYSTEM_PROMPT = """Ты — универсальный операционный помощник Beshir в Telegram.

Твоя роль:
- помогать с продажами, письмами, follow-up, коммерческими предложениями
- помогать с операционными задачами, отчетами, summaries, поручениями
- отвечать четко, по делу и структурно
- если задача неоднозначна, сначала сделай лучшее предположение и предложи улучшенную версию
- если пользователь просит сообщение/письмо, сразу дай готовый текст для отправки
- если пользователь просит отчет, дай короткую управленческую версию
- если пользователь просит план, дай конкретные шаги

Формат ответов:
- без воды
- с акцентом на практический результат
- где уместно, используй заголовки и короткие списки
- пиши на том языке, на котором пишет пользователь
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =========================
# OPENAI
# =========================
def get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=OPENAI_API_KEY)


def ask_openai(user_text: str, user_name: str = "User") -> str:
    client = get_openai_client()

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Имя пользователя: {user_name}\nЗадача: {user_text}",
            },
        ],
    )

    return response.output_text.strip()


# =========================
# GOOGLE SHEETS
# =========================
def get_worksheet():
    if not GOOGLE_SHEETS_ID:
        raise ValueError("GOOGLE_SHEETS_ID is missing")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=scopes,
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEETS_ID)

    try:
        ws = sh.worksheet("tasks")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="tasks", rows=1000, cols=12)
        ws.append_row(
            [
                "timestamp",
                "telegram_user_id",
                "username",
                "full_name",
                "chat_id",
                "message_text",
                "ai_response",
                "status",
                "category",
                "priority",
                "notes",
                "source",
            ]
        )
    return ws


def detect_category(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["отчет", "report", "summary", "summarize", "резюме"]):
        return "reporting"
    if any(x in t for x in ["письмо", "email", "follow-up", "follow up", "reply", "ответ"]):
        return "communication"
    if any(x in t for x in ["лид", "lead", "client", "клиент", "sales", "продаж"]):
        return "sales"
    if any(x in t for x in ["задача", "task", "todo", "напомни", "remind"]):
        return "operations"
    return "general"


def detect_priority(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["срочно", "urgent", "asap", "немедленно"]):
        return "high"
    if any(x in t for x in ["сегодня", "today", "до вечера"]):
        return "medium"
    return "normal"


def log_to_sheets(
    telegram_user_id: str,
    username: str,
    full_name: str,
    chat_id: str,
    message_text: str,
    ai_response: str,
    status: str = "done",
    notes: str = "",
    source: str = "telegram",
) -> None:
    ws = get_worksheet()
    ws.append_row(
        [
            datetime.utcnow().isoformat(),
            telegram_user_id,
            username,
            full_name,
            chat_id,
            message_text,
            ai_response,
            status,
            detect_category(message_text),
            detect_priority(message_text),
            notes,
            source,
        ]
    )


# =========================
# TELEGRAM HELPERS
# =========================
def is_admin(update: Update) -> bool:
    if not ADMIN_TELEGRAM_ID:
        return True
    return str(update.effective_user.id) == str(ADMIN_TELEGRAM_ID)


async def safe_reply(update: Update, text: str) -> None:
    max_len = 4000
    if len(text) <= max_len:
        await update.message.reply_text(text)
        return

    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    for chunk in chunks:
        await update.message.reply_text(chunk)


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    text = (
        "Привет. Я твой операционный помощник.\n\n"
        "Что я умею:\n"
        "- писать письма и follow-up\n"
        "- делать summaries и отчеты\n"
        "- помогать с продажами и задачами\n"
        "- сохранять обращения в Google Sheets\n\n"
        "Примеры:\n"
        "• Напиши follow-up клиенту после встречи\n"
        "• Сделай краткий weekly sales report\n"
        "• Подготовь коммерческое предложение\n"
        "• Составь план задач на сегодня"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    await update.message.reply_text(
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/ping — проверка\n"
        "/last — показать последнюю запись из логики не реализовано\n\n"
        "Или просто напиши задачу обычным сообщением."
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    await update.message.reply_text("Бот работает.")


# =========================
# MAIN MESSAGE HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if not is_admin(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    user = update.effective_user
    user_text = update.message.text or ""

    if not user_text.strip():
        await update.message.reply_text("Пришли текстовую задачу.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        ai_response = ask_openai(
            user_text=user_text,
            user_name=user.full_name or user.username or "User",
        )

        await safe_reply(update, ai_response)

        log_to_sheets(
            telegram_user_id=str(user.id),
            username=user.username or "",
            full_name=user.full_name or "",
            chat_id=str(update.effective_chat.id),
            message_text=user_text,
            ai_response=ai_response,
        )

    except Exception as e:
        logger.exception("Error while processing message")
        error_text = f"Ошибка: {str(e)}"
        await update.message.reply_text(error_text)

        try:
            log_to_sheets(
                telegram_user_id=str(user.id),
                username=user.username or "",
                full_name=user.full_name or "",
                chat_id=str(update.effective_chat.id),
                message_text=user_text,
                ai_response=error_text,
                status="error",
                notes="processing_failed",
            )
        except Exception:
            logger.exception("Failed to write error log to sheets")


# =========================
# ENTRYPOINT
# =========================
def validate_env() -> None:
    missing = []
    for key, value in {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "GOOGLE_SHEETS_ID": GOOGLE_SHEETS_ID,
    }.items():
        if not value:
            missing.append(key)

    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        missing.append(f"GOOGLE_SERVICE_ACCOUNT_FILE file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    if missing:
        raise ValueError("Missing config: " + ", ".join(missing))


def main() -> None:
    validate_env()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
