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

import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.misc import modules_help, prefix


@Client.on_message(
    filters.command(["spam", "statspam", "slowspam"], prefix) & filters.me
)
async def spam(client: Client, message: Message):
    """Запускает спам с задержкой.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Сообщения отправляются и/или удаляются в зависимости от типа.
    """
    amount = int(message.command[1])
    text = " ".join(message.command[2:])
    spam_type = message.command[0]

    await message.delete()

    for msg in range(amount):
        if message.reply_to_message:
            sent = await message.reply_to_message.reply(text)
        else:
            sent = await client.send_message(message.chat.id, text)

        if spam_type == "statspam":
            await asyncio.sleep(0.1)
            await sent.delete()
        elif spam_type == "spam":
            await asyncio.sleep(0.1)
        elif spam_type == "slowspam":
            await asyncio.sleep(0.9)


@Client.on_message(filters.command("fastspam", prefix) & filters.me)
async def fastspam(client: Client, message: Message):
    """Запускает быстрый спам без задержек.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Сообщения отправляются параллельно.
    """
    amount = int(message.command[1])
    text = " ".join(message.command[2:])

    await message.delete()

    coros = []
    for msg in range(amount):
        if message.reply_to_message:
            coros.append(message.reply_to_message.reply(text))
        else:
            coros.append(client.send_message(message.chat.id, text))
    await asyncio.wait(coros)


modules_help["spam"] = {
    "spam [amount] [text]": "Запустить спам",
    "statspam [amount] [text]": "Отправлять и удалять",
    "fastspam [amount] [text]": "Запустить быстрый спам",
    "slowspam [amount] [text]": "Запустить медленный спам",
}
