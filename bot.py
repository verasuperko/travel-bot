import os
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
CHANNEL = os.environ.get("CHANNEL", "@gdetytamopyat")

EXAMPLE_POSTS = (
    "Пример 1:\n"
    "Торрес Дель Пайне. Сходила W за 3 дня ~~не советую повторять~~. Итого: ~65км, дождь 3/3, радуга 3/3, слезы 3/3.\n\n"
    "Пример 2:\n"
    "Стартует все около 5 утра. Граница закрыта до 8. Ради этого стоило вставать в 4:30 🤡\n\n"
    "Пример 3:\n"
    "Она: ваааау прикинь! Мы в Чили! Я: а чего такого? Не жизнь, а невероятное чудо! ✨"
)

def generate_post(user_text):
    client = genai.Client(api_key=GEMINI_KEY)
    prompt = (
        "Пиши посты для телеграм-канала о путешествиях в стиле автора.\n\n"
        "Примеры постов:\n" + EXAMPLE_POSTS +
        "\n\nСтиль: живой язык, самоирония, зачёркнутый текст ~~вот так~~, эмодзи умеренно, без хэштегов, без тире в начале абзацев.\n\n"
        "Напиши пост про: " + user_text +
        "\n\nТолько текст поста."
    )
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("Пишу пост...")
    try:
        post = generate_post(user_text)
        context.user_data["last_post"] = post
        keyboard = [
            [InlineKeyboardButton("Опубликовать в канал", callback_data="publish")],
            [InlineKeyboardButton("Переделать", callback_data="redo")],
        ]
        await update.message.reply_text(post, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "publish":
        post = context.user_data.get("last_post", "")
        try:
            await context.bot.send_message(chat_id=CHANNEL, text=post, parse_mode="Markdown")
            await query.edit_message_text("Опубликовано!")
        except Exception as e:
            await query.edit_message_text(f"Ошибка публикации: {e}")
    elif query.data == "redo":
        await query.edit_message_text("Напиши ещё раз что происходит, переделаю!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
