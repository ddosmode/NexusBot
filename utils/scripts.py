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
import importlib
import os
import re
import subprocess
import sys
import traceback
from io import BytesIO
from types import ModuleType
from typing import Dict

from PIL import Image
from pyrogram import Client, errors, types
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

from .misc import modules_help, prefix, requirements_list

META_COMMENTS = re.compile(r"^ *# *meta +(\S+) *: *(.*?)\s*$", re.MULTILINE)
interact_with_to_delete = []


def text(message: types.Message) -> str:
    """Находит текст в объекте `types.Message`."""
    return message.text if message.text else message.caption


def restart() -> None:
    if "LAVHOST" in os.environ:
        os.system("lavhost restart")
    else:
        os.execvp(sys.executable, [sys.executable, "main.py"])


def format_exc(e: Exception, suffix="") -> str:
    traceback.print_exc()
    if isinstance(e, errors.RPCError):
        return (
            f"<b>Ошибка Telegram API!</b>\n"
            f"<code>[{e.CODE} {e.ID or e.NAME}] — {e.MESSAGE.format(value=e.value)}</code>\n\n<b>{suffix}</b>"
        )
    return (
        f"<b>Ошибка!</b>\n"
        f"<code>{e.__class__.__name__}: {e}</code>\n\n<b>{suffix}</b>"
    )


def with_reply(func):
    async def wrapped(client: Client, message: types.Message):
        if not message.reply_to_message:
            await message.edit("<b>Требуется ответ на сообщение</b>")
        else:
            return await func(client, message)

    return wrapped


def handle_errors(func):
    async def wrapped(client: Client, message: types.Message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except Exception as e:
            await message.edit(format_exc(e))
    return wrapped


def handle_admin_errors(func):
    """Ловит ошибки, связанные с правами администратора, с понятными сообщениями."""
    async def wrapped(client: Client, message: types.Message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except (UserAdminInvalid, ChatAdminRequired):
            await message.edit("<b>Нет прав</b>")
        except Exception as e:
            await message.edit(format_exc(e))
    return wrapped


def is_group_chat(message: types.Message) -> bool:
    return message.chat.type not in ["private", "channel"]


def admin_cause(message: types.Message, idx: int = 1) -> str:
    """Извлекает текст причины из команды, пропуская имя команды и аргумент пользователя."""
    cause = text(message).split()
    return " ".join(cause[idx:]) if len(cause) > idx else ""


async def interact_with(message: types.Message) -> types.Message:
    """
    Проверяет историю переписки с ботом и возвращает ответ бота.

    Пример:
    .. code-block:: python
        bot_msg = await interact_with(await bot.send_message("@BotFather", "/start"))
    :param message: уже отправленное боту сообщение
    :return: ответ бота
    """

    await asyncio.sleep(1)
    # noinspection PyProtectedMember
    response = [
        msg
        async for msg in message._client.get_chat_history(
            message.chat.id, limit=1
        )
    ]
    seconds_waiting = 0

    while response[0].from_user.is_self:
        seconds_waiting += 1
        if seconds_waiting >= 5:
            raise RuntimeError("Бот не ответил за 5 секунд")

        await asyncio.sleep(1)
        # noinspection PyProtectedMember
        response = [
            msg
            async for msg in message._client.get_chat_history(
                message.chat.id, limit=1
            )
        ]

    interact_with_to_delete.append(message.id)
    interact_with_to_delete.append(response[0].id)

    return response[0]


def format_module_help(module_name: str, full=True):
    commands = modules_help[module_name]

    help_text = (
        f"<b>Справка по модулю |{module_name}|\n\nИспользование:</b>\n"
        if full
        else "<b>Использование:</b>\n"
    )

    for command, desc in commands.items():
        cmd = command.split(maxsplit=1)
        args = " <code>" + cmd[1] + "</code>" if len(cmd) > 1 else ""
        help_text += f"<code>{prefix}{cmd[0]}</code>{args} — <i>{desc}</i>\n"

    return help_text


def format_small_module_help(module_name: str, full=True):
    commands = modules_help[module_name]

    help_text = (
        f"<b>Справка по модулю |{module_name}|\n\nСписок команд:\n"
        if full
        else "<b>Список команд:\n"
    )
    for command, desc in commands.items():
        cmd = command.split(maxsplit=1)
        args = " <code>" + cmd[1] + "</code>" if len(cmd) > 1 else ""
        help_text += f"<code>{prefix}{cmd[0]}</code>{args}\n"
    help_text += (
        f"\nПолное использование: <code>{prefix}help {module_name}</code></b>"
    )

    return help_text


def import_library(library_name: str, package_name: str = None):
    """
    Загружает библиотеку, или устанавливает её при случае ImportError
    :param library_name: имя библиотеки (пример импорта...)
    :param package_name: название пакета в PyPi (pip install пример)
    :return: загруженный модуль
    """
    if package_name is None:
        package_name = library_name
    requirements_list.append(package_name)

    try:
        return importlib.import_module(library_name)
    except ImportError:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name]
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Не удалось установить библиотеку {package_name} (pip вернул код {completed.returncode})"
            )
        return importlib.import_module(library_name)


def resize_image(
    input_img, output=None, img_type="PNG", size: int = 512, size2: int = None
):
    if output is None:
        output = BytesIO()
        output.name = f"sticker.{img_type.lower()}"

    with Image.open(input_img) as img:
        # Раньше здесь использовался thumbnail(size), но он возвращает
        # размер *максимум* 512х512, вместо того чтобы делать одну сторону
        # ровно 512, поэтому размеры приходится вычислять вручную :(
        if size2 is not None:
            size = (size, size2)
        elif img.width == img.height:
            size = (size, size)
        elif img.width < img.height:
            size = (max(size * img.width // img.height, 1), size)
        else:
            size = (size, max(size * img.height // img.width, 1))

        img.resize(size).save(output, img_type)

    return output


async def load_module(
    module_name: str,
    client: Client,
    message: types.Message = None,
    core=False,
) -> ModuleType:
    if module_name in modules_help and not core:
        await unload_module(module_name, client)

    path = f"modules.{'custom_modules.' if not core else ''}{module_name}"

    with open(f"{path.replace('.', '/')}.py", encoding="utf-8") as f:
        code = f.read()
    meta = parse_meta_comments(code)

    packages = meta.get("requires", "").split()
    requirements_list.extend(packages)

    try:
        module = importlib.import_module(path)
    except ImportError as e:
        if core:
            # Ядро не должно поднимать ImportError
            raise

        if not packages:
            raise

        if message:
            await message.edit(
                f"<b>Установка зависимостей: {' '.join(packages)}</b>"
            )

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            *packages,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=120)
        except asyncio.TimeoutError:
            if message:
                await message.edit(
                    "<b>Таймаут при установке зависимостей. Установите их вручную</b>"
                )
            raise TimeoutError("таймаут при установке зависимостей") from e

        if proc.returncode != 0:
            if message:
                await message.edit(
                    f"<b>Не удалось установить зависимости (pip вернул код {proc.returncode}). "
                    f"Проверьте логи для получения дополнительной информации</b>"
                )
            raise RuntimeError("не удалось установить зависимости") from e

        module = importlib.import_module(path)

    for name, obj in vars(module).items():
        if type(getattr(obj, "handlers", [])) == list:
            for handler, group in getattr(obj, "handlers", []):
                client.add_handler(handler, group)

    module.__meta__ = meta

    return module


async def unload_module(module_name: str, client: Client) -> bool:
    path = "modules.custom_modules." + module_name
    if path not in sys.modules:
        return False

    module = importlib.import_module(path)

    for name, obj in vars(module).items():
        for handler, group in getattr(obj, "handlers", []):
            client.remove_handler(handler, group)

    del modules_help[module_name]
    del sys.modules[path]

    return True


def parse_meta_comments(code: str) -> Dict[str, str]:
    try:
        groups = META_COMMENTS.search(code).groups()
    except AttributeError:
        return {}

    return {groups[i]: groups[i + 1] for i in range(0, len(groups), 2)}
