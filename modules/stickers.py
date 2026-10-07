#  Nexus-Userbot - telegram userbot
#  Copyright (C) 2020-present Nexus Userbot Organization
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pyrogram import Client, filters, types

from utils.misc import modules_help, prefix
from utils.scripts import (
    handle_errors,
    interact_with,
    interact_with_to_delete,
    resize_image,
    with_reply,
)


@Client.on_message(filters.command("kang", prefix) & filters.me)
@with_reply
async def kang(client: Client, message: types.Message):
    """Добавляет стикер в указанный набор.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Статус выводится через редактирование сообщения.
    """
    await message.edit("<b>Подождите...</b>")

    if len(message.command) < 2:
        await message.edit(
            "<b>Аргументы не указаны\n"
            f"Использование: <code>{prefix}kang [pack]* [emoji]</code></b>"
        )
        return

    pack = message.command[1]
    if len(message.command) >= 3:
        emoji = message.command[2]
    else:
        emoji = "🤔"

    await client.unblock_user("@stickers")
    await interact_with(await client.send_message("@stickers", "/cancel"))
    await interact_with(await client.send_message("@stickers", "/addsticker"))

    result = await interact_with(await client.send_message("@stickers", pack))
    if ".TGS" in result.text:
        await message.edit("<b>Анимированные наборы не поддерживаются</b>")
        return
    if "StickerExample.psd" not in result.text:
        await message.edit(
            "<b>Набор стикеров не существует. Создайте его через @Stickers бота (команда /newpack)</b>"
        )
        return

    try:
        path = await message.reply_to_message.download(in_memory=True)
    except ValueError:
        await message.edit(
            "<b>В ответе нет скачиваемого медиа</b>"
        )
        return

    resized = resize_image(path)

    await interact_with(await client.send_document("@stickers", resized))
    response = await interact_with(
        await client.send_message("@stickers", emoji)
    )
    if "/done" in response.text:
        # ok
        await interact_with(await client.send_message("@stickers", "/done"))
        await client.delete_messages("@stickers", interact_with_to_delete)
        await message.edit(
            f"<b>Стикер добавлен в <a href=https://t.me/addstickers/{pack}>набор</a></b>"
        )
    else:
        await message.edit(
            "<b>Что-то пошло не так. Проверьте историю с @stickers</b>"
        )
    interact_with_to_delete.clear()


@Client.on_message(
    filters.command(["stp", "s2p", "stick2png"], prefix) & filters.me
)
@with_reply
@handle_errors
async def stick2png(client: Client, message: types.Message):
    await message.edit("<b>Скачивание...</b>")

    file_io = await message.reply_to_message.download(in_memory=True)
    await client.send_document(
        message.chat.id, file_io, force_document=True
    )
    await message.delete()


@Client.on_message(filters.command(["resize"], prefix) & filters.me)
@with_reply
@handle_errors
async def resize_cmd(client: Client, message: types.Message):
    await message.edit("<b>Скачивание...</b>")

    size = int(message.command[1]) if len(message.command) > 1 else 512
    size2 = int(message.command[2]) if len(message.command) > 2 else None

    path = await message.reply_to_message.download(in_memory=True)
    resized = resize_image(path, size=size, size2=size2)

    await client.send_document(
        message.chat.id, resized, force_document=True
    )
    await message.delete()


modules_help["stickers"] = {
    "kang [reply]* [pack]* [emoji]": "Добавить стикер в указанный набор",
    "stp [reply]*": "Конвертировать стикер в PNG",
    "resize [reply]* [size] [size2]": "Изменить размер изображения до 512xN (или SIZExSIZE2)",
}
