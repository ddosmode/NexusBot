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

from time import perf_counter

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.misc import modules_help, prefix


@Client.on_message(filters.command(["ping", "p"], prefix) & filters.me)
async def ping(_, message: Message):
    """Проверяет пинг до серверов Telegram.

    Args:
        _: Клиент (не используется).
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Результат выводится через редактирование сообщения.
    """
    start = perf_counter()
    await message.edit("<b>Понг!</b>")
    end = perf_counter()
    await message.edit(f"<b>Понг! {int((end - start) * 1000)}мс</b>")


modules_help["ping"] = {
    "ping": "Проверить пинг до серверов Telegram",
}
