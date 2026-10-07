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

# TODO: Добавить возможность завершать сессию по хэшу

import time
from datetime import datetime
from html import escape
from textwrap import dedent

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.errors import RPCError
from pyrogram.raw.functions.account import GetAuthorizations, ResetAuthorization
from pyrogram.raw.types import UpdateServiceNotification
from pyrogram.types import Message

from utils.db import db
from utils.misc import modules_help, prefix

auth_hashes = db.get("core.sessionkiller", "auths_hashes", [])


@Client.on_message(filters.command(["sessions"], prefix) & filters.me)
async def sessions_list(client: Client, message: Message):
    """Показывает список активных сессий аккаунта.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Список сессий отправляется ответами, команда удаляется.
    """
    formatted_sessions = []
    sessions = (await client.invoke(GetAuthorizations())).authorizations
    for num, session in enumerate(sessions, 1):
        formatted_sessions.append(
            (
                "<b>{num}</b>. <b>{model}</b> на <code>{platform}</code>\n"
                "<b>Хэш:</b> {hash}\n"
                "<b>Имя приложения:</b> <code>{app_name}</code> v.{version}\n"
                "<b>Создана (последняя активность):</b> {created} ({last_activity})\n"
                "<b>IP и локация:</b> <code>{ip}</code> (<i>{location}</i>)\n"
                "<b>Официальное приложение:</b> <code>{official}</code>\n"
                "<b>2FA принят:</b> <code>{password_pending}</code>\n"
                "<b>Может принимать звонки / секретные чаты:</b> {calls} / {secret_chats}"
            ).format(
                num=num,
                model=escape(session.device_model),
                platform=escape(
                    session.platform
                    if session.platform != ""
                    else "неизвестная платформа"
                ),
                hash=session.hash,
                app_name=escape(session.app_name),
                version=escape(
                    session.app_version
                    if session.app_version != ""
                    else "неизвестно"
                ),
                created=datetime.fromtimestamp(
                    session.date_created
                ).isoformat(),
                last_activity=datetime.fromtimestamp(
                    session.date_active
                ).isoformat(),
                ip=session.ip,
                location=session.country,
                official="✅" if session.official_app else "❌",
                password_pending="❌" if session.password_pending else "✅",
                calls="❌" if session.call_requests_disabled else "✅",
                secret_chats=(
                    "❌" if session.encrypted_requests_disabled else "✅"
                ),
            )
        )
    answer = "<b>Активные сессии вашего аккаунта:</b>\n\n"
    chunk = []
    for s in formatted_sessions:
        chunk.append(s)
        if len(chunk) == 5:
            answer += "\n\n".join(chunk)
            await message.reply(answer)
            answer = ""
            chunk.clear()
    if len(chunk):
        await message.reply("\n\n".join(chunk))
    await message.delete()


@Client.on_message(
    filters.command(["sessionkiller", "sk"], prefix) & filters.me
)
async def sessionkiller(client: Client, message: Message):
    """Включает/выключает автоматическое завершение новых сессий.

    Args:
        client: Клиент Pyrogram.
        message: Сообщение, вызвавшее команду.

    Returns:
        None: Статус выводится через редактирование сообщения.
    """
    if len(message.command) == 1:
        if db.get("core.sessionkiller", "enabled", False):
            await message.edit(
                "<b>Статус sessionkiller: включён\n"
                f"Отключить: <code>{prefix}sessionkiller disable</code></b>"
            )
        else:
            await message.edit(
                "<b>Статус sessionkiller: выключен\n"
                f"Включить: <code>{prefix}sessionkiller enable</code></b>"
            )
    elif message.command[1] in ["enable", "on", "1", "yes", "true"]:
        db.set("core.sessionkiller", "enabled", True)
        await message.edit("<b>Sessionkiller включён!</b>")
        db.set(
            "core.sessionkiller",
            "auths_hashes",
            [
                auth.hash
                for auth in (
                    await client.invoke(GetAuthorizations())
                ).authorizations
            ],
        )

    elif message.command[1] in ["disable", "off", "0", "no", "false"]:
        db.set("core.sessionkiller", "enabled", False)
        await message.edit("<b>Sessionkiller выключен!</b>")
    else:
        await message.edit(
            f"<b>Использование: {prefix}sessionkiller [enable|disable]</b>"
        )


@Client.on_raw_update()
async def check_new_login(
    client: Client, update: UpdateServiceNotification, _, __
):
    """Проверяет новые входы в аккаунт и завершает их при включённом sessionkiller.

    Args:
        client: Клиент Pyrogram.
        update: Сырой апдейт от Telegram.
        _: Не используется.
        __: Не используется.

    Returns:
        None: Подозрительная сессия завершается, отчёт отправляется в избранное.
    """
    if not isinstance(
        update, UpdateServiceNotification
    ) or not update.type.startswith("auth"):
        raise ContinuePropagation
    if not db.get("core.sessionkiller", "enabled", False):
        raise ContinuePropagation
    authorizations = (await client.invoke(GetAuthorizations()))[
        "authorizations"
    ]
    for auth in authorizations:
        if auth.current:
            continue
        if auth["hash"] not in auth_hashes:
            # обнаружен новый неожиданный вход
            try:
                await client.invoke(ResetAuthorization(hash=auth.hash))
            except RPCError:
                info_text = (
                    "Кто-то пытался войти в ваш аккаунт. Вы видите этот отчёт, потому что включили эту функцию. "
                    "Но я не смог завершить сессию атакующего и "
                    "⚠ <b>вы должны сбросить её вручную</b>. Смените пароль 2FA "
                    "(если включено), или установите его.\n"
                )
            else:
                info_text = (
                    "Кто-то пытался войти в ваш аккаунт. Так как функция включена, "
                    "я удалил сессию атакующего из вашего аккаунта. "
                    "Смените пароль 2FA (если включено), или установите его.\n"
                )
            logined_time = datetime.utcfromtimestamp(
                auth.date_created
            ).strftime("%d-%m-%Y %H-%M-%S UTC")
            full_report = (
                "<b>!!! ТРЕБУЕТСЯ ДЕЙСТВИЕ !!!</b>\n"
                + info_text
                + "Ниже информация об атакующем, которую мне удалось получить.\n\n"
                f"Уникальный хэш авторизации: <code>{auth.hash}</code> (больше недействителен)\n"
                f"Модель устройства: <code>{escape(auth.device_model)}</code>\n"
                f"Платформа: <code>{escape(auth.platform)}</code>\n"
                f"API ID: <code>{auth.api_id}</code>\n"
                f"Имя приложения: <code>{escape(auth.app_name)}</code>\n"
                f"Версия приложения: <code>{auth.app_version}</code>\n"
                f"Вход выполнен: <code>{logined_time}</code>\n"
                f"IP: <code>{auth.ip}</code>\n"
                f"Страна: <code>{auth.country}</code>\n"
                f'Официальное приложение: <b>{"да" if auth.official_app else "нет"}</b>\n\n'
                f"<b>Это вы? Введите <code>{prefix}sk off</code> и попробуйте "
                f"войти снова.</b>"
            )
            # планируем отправку отчёта, чтобы пользователь получил уведомление
            schedule_date = int(time.time() + 15)
            await client.send_message(
                "me", full_report, schedule_date=schedule_date
            )
            return


modules_help["sessions"] = {
    "sessionkiller [enable|disable]": "При включении каждая новая сессия будет завершена.\n"
    "Полезно для дополнительной защиты аккаунта",
    "sessions": "Показать все сессии аккаунта",
}
