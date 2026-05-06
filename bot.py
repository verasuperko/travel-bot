import os
import anthropic
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
CHANNEL = os.environ.get("CHANNEL", "@gdetytamopyat")

EXAMPLE_POSTS = (
    "Пример 1:\n"
    "Торрес Дель Пайне. Сходила W за 3 дня ~~не советую повторять~~. Итого: ~65км, дождь 3/3, радуга 3/3, слезы 3/3.\n\n"
    "Пример 2:\n"
    "Стартует все около 5 утра. Граница закрыта до 8. Ради этого стоило вставать в 4:30 🤡\n\n"
    "Пример 3:\n"
    "Она: ваааау прикинь! Мы в Чили! Я: а чего такого? Не жизнь, а невероятное чудо! ✨"
)

def generate_post(user_text, image_data=None, image_type=None):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt = (
        "Пиши посты для телеграм-канала о путешествиях в стиле автора.\n\n"
        "Примеры постов:\n" + EXAMPLE_POSTS +
        "\n\nСтиль: живой разговорный язык, самоирония. "
        "Используй только ~~зачёркнутый~~ для сарказма, больше никакого форматирования. "
        "Раздели пост на 2-3 абзаца. Эмодзи умеренно, без хэштегов, без тире в начале абзацев.\n\n"
        "Напиши пост про: " + (user_text or "то что изображено на фото") +
        "\n\nТолько текст поста."
    )
    content = []
    if image_data:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_type,
                "data": image_data
            }
        })
    content.append({"type": "text", "text": prompt})
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": content}]
    )
    return message.content[0].text

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    await update.message.reply_text("Смотрю на фото и пишу пост...")
    try:
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()
        image_data = base64.standard_b64encode(file_bytes).decode("utf-8")
        post = generate_post(caption, image_data, "image/jpeg")
        context.user_data["last_post"] = post
        context.user_data["last_photo_id"] = photo.file_id
        context.user_data["waiting_edit"] = False
        keyboard = [
            [InlineKeyboardButton("Опубликовать в канал", callback_data="publish")],
            [InlineKeyboardButton("Редактировать", callback_data="edit")],
            [InlineKeyboardButton("Переделать", callback_data="redo_photo")],
        ]
        await update.message.reply_text(post, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if context.user_data.get("waiting_edit"):
        context.user_data["waiting_edit"] = False
        context.user_data["last_post"] = user_text
        keyboard = [
            [InlineKeyboardButton("Опубликовать в канал", callback_data="publish")],
            [InlineKeyboardButton("Редактировать ещё раз", callback_data="edit")],
        ]
        await update.message.reply_text("Вот твой отредактированный пост:", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text(user_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await update.message.reply_text("Пишу пост...")
    try:
        post = generate_post(user_text)
        context.user_data["last_post"] = post
        context.user_data["waiting_edit"] = False
        keyboard = [
            [InlineKeyboardButton("Опубликовать в канал", callback_data="publish")],
            [InlineKeyboardButton("Редактировать", callback_data="edit")],
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
        photo_id = context.user_data.get("last_photo_id")
        try:
            if photo_id:
                await context.bot.send_photo(chat_id=CHANNEL, photo=photo_id, caption=post, )
            else:
                await context.bot.send_message(chat_id=CHANNEL, text=post, )
            context.user_data["last_photo_id"] = None
            await query.edit_message_text("Опубликовано!")
        except Exception as e:
            await query.edit_message_text(f"Ошибка публикации: {e}")
    elif query.data == "edit":
        context.user_data["waiting_edit"] = True
        await query.edit_message_text("Скопируй текст ниже, отредактируй и пришли мне:")
        await context.bot.send_message(chat_id=query.message.chat_id, text=context.user_data.get("last_post", ""))
    elif query.data == "redo":
        await query.edit_message_text("Напиши ещё раз что происходит, переделаю!")
    elif query.data == "redo_photo":
        await query.edit_message_text("Пришли фото ещё раз или напиши что добавить!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
