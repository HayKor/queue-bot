from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from . import db
from . import keyboard as kb

router = Router()

async def is_admin(message: Message) -> bool:
    if message.chat.type == "private":
        return True
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["creator", "administrator"]

def generate_queue_text(queue_name: str, members: list) -> str:
    text = f"📋 <b>Очередь: {queue_name}</b>\n\n"
    if not members:
        text += "Очередь пуста. Будь первым!"
    else:
        for m in members:
            # Экранируем HTML-символы на случай, если у кого-то в имени теги
            safe_name = m['full_name'].replace('<', '&lt;').replace('>', '&gt;')
            text += f"{m['position']}. {safe_name}\n"
    return text

@router.message(Command("create"))
async def cmd_create(message: Message):
    if not await is_admin(message):
        return await message.reply("Только администраторы могут создавать очередь.")

    queue_name = message.text.replace("/create", "").strip() or "Новая очередь"
    queue_id = db.create_queue(message.chat.id, queue_name)

    text = generate_queue_text(queue_name, [])
    sent_msg = await message.answer(text, reply_markup=kb.get_join_keyboard(queue_id), parse_mode="HTML")
    db.set_queue_message(queue_id, sent_msg.message_id)
    
    # Удаляем саму команду /create, чтобы не мусорить в чате
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("join_"))
async def cb_join(callback: CallbackQuery):
    queue_id = int(callback.data.split("_")[1])
    full_name = callback.from_user.full_name

    if db.join_queue(queue_id, callback.from_user.id, full_name):
        members = db.get_queue_members(queue_id)
        with db.get_connection() as conn:
            q = conn.execute("SELECT name FROM queues WHERE id = ?", (queue_id,)).fetchone()

        text = generate_queue_text(q["name"], members)
        try:
            await callback.message.edit_text(text, reply_markup=kb.get_join_keyboard(queue_id), parse_mode="HTML")
            await callback.answer("Вы успешно заняли очередь!")
        except TelegramBadRequest:
            pass # Сообщение не изменилось
    else:
        await callback.answer("Вы уже находитесь в этой очереди!", show_alert=True)

# Вспомогательная функция: получает ID очереди, на сообщение которой ответили
async def get_queue_from_reply(message: Message):
    if not message.reply_to_message:
        await message.reply("Ответьте этой командой на сообщение с нужной очередью!")
        return None
    queue = db.get_queue_by_message(message.chat.id, message.reply_to_message.message_id)
    if not queue:
        await message.reply("Очередь не найдена. Отвечайте на сообщение бота со списком.")
        return None
    return queue

async def update_queue_message(message: Message, queue_id: int, queue_name: str, message_id: int):
    members = db.get_queue_members(queue_id)
    text = generate_queue_text(queue_name, members)
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=text,
            reply_markup=kb.get_join_keyboard(queue_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@router.message(Command("pop"))
async def cmd_pop(message: Message):
    if not await is_admin(message): return
    queue = await get_queue_from_reply(message)
    if not queue: return

    args = message.text.split()
    count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

    db.pop_members(queue["id"], count)
    await update_queue_message(message, queue["id"], queue["name"], queue["message_id"])
    await message.delete()

@router.message(Command("swap"))
async def cmd_swap(message: Message):
    if not await is_admin(message): return
    queue = await get_queue_from_reply(message)
    if not queue: return

    args = message.text.split()
    if len(args) < 3 or not args[1].isdigit() or not args[2].isdigit():
        return await message.reply("Формат: /swap <место1> <место2>")

    if db.swap_members(queue["id"], int(args[1]), int(args[2])):
        await update_queue_message(message, queue["id"], queue["name"], queue["message_id"])
    await message.delete()

@router.message(Command("insert"))
async def cmd_insert(message: Message):
    if not await is_admin(message): return
    queue = await get_queue_from_reply(message)
    if not queue: return

    args = message.text.split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit():
        return await message.reply("Формат: /insert <место> <Имя Фамилия>")

    db.insert_member(queue["id"], int(args[1]), args[2])
    await update_queue_message(message, queue["id"], queue["name"], queue["message_id"])
    await message.delete()
