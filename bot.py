import logging
import os
import re
import string

from spellchecker import SpellChecker
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Spell checker (English by default; change `language=` for other languages,
# e.g. "es", "fr", "de", "pt", "ru" -- see pyspellchecker docs for support)
# ---------------------------------------------------------------------------
spell = SpellChecker(language="en")

WORD_RE = re.compile(r"[A-Za-z']+")
MAX_WORDS_LISTED = 30  # avoid flooding the reply on huge pastes


def check_text(text: str):
    """
    Returns:
        corrected_text: str  -- best-effort corrected version of the input
        misspelled: list[tuple[str, str]] -- (original_word, suggestion) pairs
    """
    words = WORD_RE.findall(text)
    misspelled_words = spell.unknown(words)

    corrected_text = text
    misspelled_pairs = []

    for word in words:
        if word in misspelled_words:
            suggestion = spell.correction(word)
            if suggestion and suggestion.lower() != word.lower():
                misspelled_pairs.append((word, suggestion))
                # Replace preserving original capitalization style
                replacement = suggestion
                if word.isupper():
                    replacement = suggestion.upper()
                elif word[0].isupper():
                    replacement = suggestion.capitalize()
                corrected_text = re.sub(
                    rf"\b{re.escape(word)}\b", replacement, corrected_text, count=1
                )

    return corrected_text, misspelled_pairs


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hi! I'm *SpellCheck1_Bot*.\n\n"
        "Send me any text and I'll check it for spelling mistakes and "
        "suggest corrections.\n\n"
        "Commands:\n"
        "/start - show this welcome message\n"
        "/help - how to use this bot\n"
        "/addword <word> - teach me a word so I stop flagging it\n\n"
        "Just type or paste a sentence to get started!",
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📝 *How to use SpellCheck1_Bot*\n\n"
        "1. Send any message with text.\n"
        "2. I'll reply with:\n"
        "   • ✅ a corrected version of your text\n"
        "   • 🔎 a list of misspelled words with suggestions\n\n"
        "If I don't find any mistakes, I'll let you know your text looks good!\n\n"
        "Use /addword <word> to add a custom word (like a name or slang) "
        "to my dictionary for this session.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /addword <word>")
        return
    word = context.args[0].strip(string.punctuation).lower()
    spell.word_frequency.load_words([word])
    await update.message.reply_text(f"Got it — I'll treat '{word}' as correct from now on.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    corrected_text, misspelled_pairs = check_text(text)

    if not misspelled_pairs:
        await update.message.reply_text("✅ Looks good! No spelling mistakes found.")
        return

    lines = ["🔎 *Possible spelling issues:*"]
    for original, suggestion in misspelled_pairs[:MAX_WORDS_LISTED]:
        lines.append(f"• `{original}` → *{suggestion}*")

    if len(misspelled_pairs) > MAX_WORDS_LISTED:
        lines.append(f"...and {len(misspelled_pairs) - MAX_WORDS_LISTED} more.")

    lines.append("\n✅ *Suggested correction:*")
    lines.append(corrected_text)

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update %s caused error %s", update, context.error)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Set it locally in a .env file or in Railway's Variables tab."
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addword", add_word))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("SpellCheck1_Bot is starting (polling mode)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
