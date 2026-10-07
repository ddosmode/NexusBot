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

import os
from subprocess import PIPE, Popen, TimeoutExpired
from time import perf_counter

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.misc import modules_help, prefix


@Client.on_message(filters.command(["shell", "sh"], prefix) & filters.me)
async def shell(_, message: Message):
    """Выполняет команду в оболочке.

    Args:
        _: Клиент (не используется).
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Результат выполнения выводится через редактирование сообщения.
    """
    if len(message.command) < 2:
        return await message.edit("<b>Укажите команду в тексте сообщения</b>")
    cmd_text = message.text.split(maxsplit=1)[1]
    cmd_obj = Popen(
        cmd_text,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    )

    char = "#" if os.getuid() == 0 else "$"
    text = f"<b>{char}</b> <code>{cmd_text}</code>\n\n"

    await message.edit(text + "<b>Выполняю...</b>")
    try:
        start_time = perf_counter()
        stdout, stderr = cmd_obj.communicate(timeout=60)
    except TimeoutExpired:
        text += "<b>Превышено время ожидания (60 секунд)</b>"
    else:
        stop_time = perf_counter()
        if stdout:
            text += f"<b>Вывод:</b>\n<code>{stdout}</code>\n\n"
        if stderr:
            text += f"<b>Ошибка:</b>\n<code>{stderr}</code>\n\n"
        text += f"<b>Завершено за {round(stop_time - start_time, 5)}с. с кодом {cmd_obj.returncode}</b>"
    await message.edit(text)
    cmd_obj.kill()


modules_help["shell"] = {"sh [command]*": "Выполнить команду в оболочке"}
