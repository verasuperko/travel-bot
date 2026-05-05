import os
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
CHANNEL = os.environ.get("CHANNEL", "@gdetytamopyat")

EXAMPLE_POSTS = """Пример 1:
Торрес Дель Пайне — вот зачем я снова решила ехать в Патагонию. Я решила сходить сжатую версию W за 3 дня ~~не советую повторять~~. Краткая сводка: ~65км, дождь 3/3, радуга 3/3, слезы 3/3, мокрые ноги 2/3, горячий душ 3/3.

Пример 2:
Стартует все около 5 утра, на рассвете нас привезли на границу. Оказалось, что сама граница закрыта до 8, а до этого необходимо позавтракать в горах на морозе. Ради этого стоило вставать в 4:30 🤡 Реально нереально!

Пример 3:
Она такая «ваааау прикинь! Мы в Чили!», а я ей «А чего такого?» Не жизнь, а невероятное чудо! Тонкой нитью хочу перманентно это ощущение внутри ✨"""

def generate_post(user_text):
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Ты помощник для написания постов в телеграм-канал о путешествиях. Пиши в точном стиле автора.

СТИЛЬ (реальные посты автора):
{EXAMPLE_POSTS}

ХАРАКТЕРИСТИКИ СТИЛЯ:
- Живой разговорный язык
- Зачёркнутый текст для сарказма: ~~вот так~~
- Эмодзи умеренно (🤡 🫠 ✨)
- Самоирония и личные эмоции
- Конкретные детали: цифры, часы, км
- Без хэштегов
- Без тире в начале абзацев

Напиши пост про: {user_text}

Только текст поста, без предисловий."""
    response = model.generate_content(prompt)
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
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(post, reply_markup=reply_markup)
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
