import os
import anthropic
import base64
import json
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
CHANNEL = os.environ.get("CHANNEL", "@gdetytamopyat")
TIMEZONE = ZoneInfo("Europe/Moscow")  # поменяй если нужно другой часовой пояс

EXAMPLE_POSTS = """
Пример 1:
У нас на углу живет бездомный.
Просто у него там местечко и он с него особо никуда не уходит. Сидит себе разговаривает сам с собой, такой знаете, в велосипедном шлеме.

Вчера в СП была желтая опасность. Лютый дождь, гроза, под которым я шла с зонтом в течение получаса и дома выжимала джинсы, а кроссовки даже не представляю, высохнут ли теперь в этой влажности.
В общем иду и смотрю, он лежит под одеялом просто под этим тропическим ливнем. А на улице что-то около 15 градусов.

Ну он же сосед, как кот, понимаете? Появилось желание его подкармливать. Тут все так делают. Эти ребята никогда не просят денег, если и просят что-то, то еду.

Пример 2:
Бразилиа вызывает смешанные чувства.

Я никак не могу отделаться от мысли, что попала в учебник по проектированию и одновременно антиутопическое кино.

Город великого эксперимента. На который любопытно взглянуть, но не жить в нем. Модернисты считали, что архитектура может создать лучшее общество.
Общество, судя по всему, так не думало 😅

Здесь не покидает ощущение «правильности». Одинаковые кварталы жилых домов, пятиметровые тротуары и шестиполосные дороги со сложными развязками, ряды министерских зданий, чистота и отдельность.

Но человек здесь лишний, ему просто нет места. Перейти огромную дорогу, ощущать себя среди километровых открытых пространств без тени. Это все не про человека. И поэтому машин тут теперь больше, чем людей.

Пример 3:
Ну что ж, мы в Сан-Пауло!

Город, которым пугают детей. И он правда жуткий, если снять квартиру немного не в том районе (да, было). Сейчас, поумнев, я решила жить рядом с легендарным парком Ибирапуэйра в районе Моэма. Это сразу меняет примерно все.

Сан-Пауло — это город миллионеров и негласная столица Бразилии. Тут лучшие мира сего передвигаются на вертолетах, а центр города утопает в бездомных и наркотиках.

Но есть другая сторона, в которую я и влюбилась. Это невероятная архитектура и искусство, джунгли из растений и домов, музеи и орхидеи, растущие сами по себе. Просто жгучая смесь азиатского мегаполиса и латиноамериканской маньяны.

Пример 4:
Сегодня я ела практически в книжном магазине на первом этаже Edifício Copan.

Спроектировал его наш любимый Оскар Нимейер, открылось в 1966 году. Здание в форме буквы S — целый город в форме волны: отдельный почтовый индекс, 1160 квартир, около 5000 жильцов и миллион магазинов на первом этаже.

Сейчас здание в лесах — фасад разрушался 20 лет и никому до этого не было дела. Теперь восстанавливают почти полностью на деньги жильцов.

А кафе называется Cuia, несколько лет подряд отмечается в гиде Мишлен. Вкусно. Рекомендасьон.
"""

SYSTEM_PROMPT = """Ты — помощник, который пишет посты для телеграм-канала о путешествиях от первого лица.

СТИЛЬ АВТОРА:
— Живой разговорный русский язык, как будто рассказываешь подруге
— Самоирония и внутренний монолог ("да, было", "да, я понимаю", "ну вот")
— Конкретные детали: цифры, названия мест на языке оригинала, реальные наблюдения
— Философские отступления — автор часто уходит в размышления о жизни, людях, восприятии
— Структура: зацепка → разворачивание истории → личное наблюдение или вывод
— Длина: 3-5 абзацев, не короче. Пост должен быть содержательным
— Умеренно эмодзи, только где уместно по смыслу
— Зачёркнутый текст через ~~текст~~ для иронии — использовать редко, только если очень в тему
— Названия мест на испанском/португальском где уместно

ЗАПРЕЩЕНО:
— Хэштеги
— Тире в начале абзаца
— Звёздочки, решётки и любое markdown-форматирование
— Списки с буллетами (только если это реально нужно по смыслу как в постах автора)
— Короткие посты из 1-2 абзацев
— Пафосные вступления ("Сегодня я расскажу вам...")
— Журналистский или туристический буклетный язык
— Слова: "удивительный", "невероятный", "потрясающий" без иронии

Пиши только текст поста, без пояснений."""


def generate_post(user_text, image_data=None, image_type=None):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    user_prompt = (
        "Вот примеры постов автора:\n" + EXAMPLE_POSTS +
        "\n\nНапиши пост про: " + (user_text or "то что изображено на фото") +
        "\n\nТолько текст поста, без пояснений."
    )
    content = []
    if image_data:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": image_type, "data": image_data}
        })
    content.append({"type": "text", "text": user_prompt})
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    return message.content[0].text


# ── Хранилище очереди (в памяти, сбрасывается при рестарте) ──────────────────
# Для продакшена стоит заменить на sqlite или redis
scheduled_posts = {}  # {post_id: {"text": ..., "photo_id": ..., "dt": datetime, "task": asyncio.Task}}
_post_counter = 0

def next_post_id():
    global _post_counter
    _post_counter += 1
    return str(_post_counter)


def format_queue() -> str:
    if not scheduled_posts:
        return "Очередь пуста."
    lines = ["📋 Запланированные посты:\n"]
    for pid, data in sorted(scheduled_posts.items(), key=lambda x: x[1]["dt"]):
        dt_str = data["dt"].strftime("%d.%m.%Y %H:%M")
        preview = data["text"][:80].replace("\n", " ")
        has_photo = "🖼 " if data.get("photo_id") else ""
        lines.append(f"#{pid} | {dt_str} | {has_photo}{preview}...")
    return "\n".join(lines)


def queue_keyboard(post_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"schedit_{post_id}"),
         InlineKeyboardButton("❌ Отменить", callback_data=f"schcancel_{post_id}")]
    ])


async def publish_scheduled(app, post_id: str, chat_id: int):
    """Публикует запланированный пост в канал."""
    data = scheduled_posts.get(post_id)
    if not data:
        return
    try:
        if data.get("photo_id"):
            await app.bot.send_photo(chat_id=CHANNEL, photo=data["photo_id"], caption=data["text"])
        else:
            await app.bot.send_message(chat_id=CHANNEL, text=data["text"])
        await app.bot.send_message(chat_id=chat_id, text=f"✅ Пост #{post_id} опубликован в канал!")
    except Exception as e:
        await app.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка публикации поста #{post_id}: {e}")
    finally:
        scheduled_posts.pop(post_id, None)


async def schedule_post(app, post_id: str, chat_id: int, dt: datetime):
    """Ждёт нужного времени и публикует."""
    now = datetime.now(TIMEZONE)
    delay = (dt - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    await publish_scheduled(app, post_id, chat_id)


# ── Handlers ──────────────────────────────────────────────────────────────────

def post_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data="publish")],
        [InlineKeyboardButton("🕐 Запланировать", callback_data="schedule")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("🔄 Переделать", callback_data="redo")],
    ])

def post_keyboard_photo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data="publish")],
        [InlineKeyboardButton("🕐 Запланировать", callback_data="schedule")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("🔄 Переделать", callback_data="redo_photo")],
    ])


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    await update.message.reply_text("Смотрю на фото, пишу пост...")
    try:
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()
        image_data = base64.standard_b64encode(file_bytes).decode("utf-8")
        post = generate_post(caption, image_data, "image/jpeg")
        context.user_data["last_post"] = post
        context.user_data["last_photo_id"] = photo.file_id
        context.user_data["waiting_edit"] = False
        context.user_data["waiting_schedule"] = False
        await update.message.reply_text(post, reply_markup=post_keyboard_photo())
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # Ждём отредактированный текст
    if context.user_data.get("waiting_edit"):
        context.user_data["waiting_edit"] = False
        context.user_data["last_post"] = user_text
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data="publish")],
            [InlineKeyboardButton("🕐 Запланировать", callback_data="schedule")],
            [InlineKeyboardButton("✏️ Редактировать ещё раз", callback_data="edit")],
        ])
        await update.message.reply_text("Отредактированный пост:", reply_markup=kb)
        await update.message.reply_text(user_text, reply_markup=kb)
        return

    # Ждём дату/время для планирования
    if context.user_data.get("waiting_schedule"):
        # Ожидаем формат: DD.MM.YYYY HH:MM
        try:
            dt_naive = datetime.strptime(user_text.strip(), "%d.%m.%Y %H:%M")
            dt = dt_naive.replace(tzinfo=TIMEZONE)
            now = datetime.now(TIMEZONE)
            if dt <= now:
                await update.message.reply_text("Это время уже прошло. Введи дату и время в будущем (ДД.ММ.ГГГГ ЧЧ:ММ):")
                return
            post_id = next_post_id()
            post_text = context.user_data.get("last_post", "")
            photo_id = context.user_data.get("last_photo_id")
            task = asyncio.create_task(
                schedule_post(context.application, post_id, update.effective_chat.id, dt)
            )
            scheduled_posts[post_id] = {
                "text": post_text,
                "photo_id": photo_id,
                "dt": dt,
                "task": task,
                "chat_id": update.effective_chat.id,
            }
            context.user_data["waiting_schedule"] = False
            context.user_data["last_photo_id"] = None
            dt_str = dt.strftime("%d.%m.%Y в %H:%M")
            await update.message.reply_text(
                f"✅ Пост #{post_id} запланирован на {dt_str} (МСК).",
                reply_markup=queue_keyboard(post_id)
            )
        except ValueError:
            await update.message.reply_text("Не понял формат. Введи дату и время вот так: 25.07.2025 10:00")
        return

    # Ждём новый текст для редактирования запланированного поста
    if context.user_data.get("waiting_schedit"):
        pid = context.user_data.pop("waiting_schedit")
        if pid in scheduled_posts:
            scheduled_posts[pid]["text"] = user_text
            await update.message.reply_text(
                f"✅ Текст поста #{pid} обновлён.",
                reply_markup=queue_keyboard(pid)
            )
        else:
            await update.message.reply_text("Пост не найден (возможно, уже опубликован).")
        return

    # Обычное сообщение — генерируем пост
    await update.message.reply_text("Пишу пост...")
    try:
        post = generate_post(user_text)
        context.user_data["last_post"] = post
        context.user_data["last_photo_id"] = None
        context.user_data["waiting_edit"] = False
        context.user_data["waiting_schedule"] = False
        await update.message.reply_text(post, reply_markup=post_keyboard())
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Опубликовать сейчас ───────────────────────────────────────────────────
    if data == "publish":
        post = context.user_data.get("last_post", "")
        photo_id = context.user_data.get("last_photo_id")
        try:
            if photo_id:
                await context.bot.send_photo(chat_id=CHANNEL, photo=photo_id, caption=post)
            else:
                await context.bot.send_message(chat_id=CHANNEL, text=post)
            context.user_data["last_photo_id"] = None
            await query.edit_message_text("✅ Опубликовано!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка публикации: {e}")

    # ── Запланировать ─────────────────────────────────────────────────────────
    elif data == "schedule":
        context.user_data["waiting_schedule"] = True
        await query.edit_message_text(
            "Введи дату и время публикации в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 25.07.2025 10:00\n"
            "(время московское)"
        )

    # ── Редактировать текущий пост ────────────────────────────────────────────
    elif data == "edit":
        context.user_data["waiting_edit"] = True
        await query.edit_message_text("Скопируй текст ниже, отредактируй и пришли мне:")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=context.user_data.get("last_post", "")
        )

    # ── Переделать ────────────────────────────────────────────────────────────
    elif data == "redo":
        await query.edit_message_text("Напиши ещё раз что происходит — переделаю!")

    elif data == "redo_photo":
        await query.edit_message_text("Пришли фото ещё раз или напиши что добавить!")

    # ── Редактировать запланированный пост ───────────────────────────────────
    elif data.startswith("schedit_"):
        pid = data.split("_", 1)[1]
        if pid not in scheduled_posts:
            await query.edit_message_text("Пост не найден.")
            return
        context.user_data["waiting_schedit"] = pid
        post_text = scheduled_posts[pid]["text"]
        await query.edit_message_text(f"Скопируй текст поста #{pid}, отредактируй и пришли:")
        await context.bot.send_message(chat_id=query.message.chat_id, text=post_text)

    # ── Отменить запланированный пост ────────────────────────────────────────
    elif data.startswith("schcancel_"):
        pid = data.split("_", 1)[1]
        if pid in scheduled_posts:
            scheduled_posts[pid]["task"].cancel()
            scheduled_posts.pop(pid)
            await query.edit_message_text(f"❌ Пост #{pid} отменён.")
        else:
            await query.edit_message_text("Пост не найден (возможно, уже опубликован).")


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список запланированных постов."""
    text = format_queue()
    if not scheduled_posts:
        await update.message.reply_text(text)
        return
    # Кнопки для каждого поста
    buttons = []
    for pid in sorted(scheduled_posts.keys()):
        dt_str = scheduled_posts[pid]["dt"].strftime("%d.%m %H:%M")
        buttons.append([
            InlineKeyboardButton(f"✏️ #{pid} ({dt_str})", callback_data=f"schedit_{pid}"),
            InlineKeyboardButton("❌", callback_data=f"schcancel_{pid}"),
        ])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли мне текст или фото — напишу пост для канала.\n\n"
        "/queue — посмотреть запланированные посты"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
