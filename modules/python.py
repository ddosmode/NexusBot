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

from contextlib import redirect_stdout
from io import StringIO

from pyrogram import Client, filters
from pyrogram.types import Message

# noinspection PyUnresolvedReferences
from utils.db import db

# noinspection PyUnresolvedReferences
from utils.misc import modules_help, prefix
from utils.scripts import format_exc


# noinspection PyUnusedLocal
@Client.on_message(
    filters.command(["ex", "exec", "py", "exnoedit"], prefix) & filters.me
)
def user_exec(client: Client, message: Message):
    """Выполняет Python-код.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Результат выводится через редактирование или ответом.
    """
    if len(message.command) == 1:
        message.edit("<b>Код для выполнения не указан</b>")
        return

    reply = message.reply_to_message

    code = message.text.split(maxsplit=1)[1]
    stdout = StringIO()

    message.edit("<b>Выполняю...</b>")

    try:
        with redirect_stdout(stdout):
            exec(code)
        text = (
            "<b>Код:</b>\n"
            f"<pre language=python>{code}</pre>\n\n"
            "<b>Результат</b>:\n"
            f"<code>{stdout.getvalue()}</code>"
        )
        if message.command[0] == "exnoedit":
            message.reply(text)
        else:
            message.edit(text)
    except Exception as e:
        message.edit(format_exc(e, f"Код был <code>{code}</code>"))


# noinspection PyUnusedLocal
@Client.on_message(filters.command(["ev", "eval"], prefix) & filters.me)
def user_eval(client: Client, message: Message):
    """Вычисляет Python-выражение.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Результат выводится через редактирование сообщения.
    """
    if len(message.command) == 1:
        message.edit("<b>Выражение для вычисления не указано</b>")
        return

    reply = message.reply_to_message

    code = message.text.split(maxsplit=1)[1]

    try:
        result = eval(code)
        message.edit(
            "<b>Выражение:</b>\n"
            f"<pre language=python>{code}</pre>\n\n"
            "<b>Результат</b>:\n"
            f"<code>{result}</code>"
        )
    except Exception as e:
        message.edit(format_exc(e, f"Код был <code>{code}</code>"))


modules_help["python"] = {
    "ex [python code]": "Выполнить Python-код",
    "exnoedit [python code]": "Выполнить Python-код и вернуть результат ответом",
    "eval [python code]": "Вычислить Python-выражение",
}
