#  Nexus-Userbot - telegram userbot
#  Copyright (C) 2020-present Nexus Userbot Organization
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from contextlib import suppress
from datetime import datetime, timedelta
from time import time
from typing import Dict, Union

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.errors import (
    ChatAdminRequired,
    PeerIdInvalid,
    RPCError,
    UserAdminInvalid,
    UsernameInvalid,
)
from pyrogram.raw import functions, types
from pyrogram.types import ChatPermissions, ChatPrivileges, Message
from pyrogram.utils import (
    MAX_CHANNEL_ID,
    MAX_USER_ID,
    MIN_CHANNEL_ID,
    MIN_CHAT_ID,
    get_channel_id,
)

from utils.db import db
from utils.misc import modules_help, prefix
from utils.scripts import (
    format_exc,
    handle_admin_errors,
    handle_errors,
    is_group_chat,
    text,
    with_reply,
)

db_cache: dict = db.get_collection("core.ats")


def update_cache():
    db_cache.clear()
    db_cache.update(db.get_collection("core.ats"))


@Client.on_message(filters.group & ~filters.me)
async def admintool_handler(_, message: Message):
    if message.sender_chat:
        if (
            message.sender_chat.type == "supergroup"
            or message.sender_chat.id
            == db_cache.get(f"linked{message.chat.id}", 0)
        ):
            raise ContinuePropagation

    if message.sender_chat and db_cache.get(f"antich{message.chat.id}", False):
        with suppress(RPCError):
            await message.delete()
            await message.chat.ban_member(message.sender_chat.id)

    tmuted_users = db_cache.get(f"c{message.chat.id}", [])
    if (
        message.from_user
        and message.from_user.id in tmuted_users
        or message.sender_chat
        and message.sender_chat.id in tmuted_users
    ):
        with suppress(RPCError):
            await message.delete()

    if db_cache.get(f"antiraid{message.chat.id}", False):
        with suppress(RPCError):
            await message.delete()
            if message.from_user:
                await message.chat.ban_member(message.from_user.id)
            elif message.sender_chat:
                await message.chat.ban_member(message.sender_chat.id)

    if message.new_chat_members:
        if db_cache.get(f"welcome_enabled{message.chat.id}", False):
            await message.reply(
                db_cache.get(f"welcome_text{message.chat.id}"),
                disable_web_page_preview=True,
            )

    raise ContinuePropagation


async def check_username_or_id(data: Union[str, int]) -> str:
    data = str(data)
    if (
        not data.isdigit()
        and data[0] == "-"
        and not data[1:].isdigit()
        or not data.isdigit()
        and data[0] != "-"
    ):
        return "channel"
    else:
        peer_id = int(data)
    if peer_id < 0:
        if MIN_CHAT_ID <= peer_id:
            return "chat"

        if MIN_CHANNEL_ID <= peer_id < MAX_CHANNEL_ID:
            return "channel"
    elif 0 < peer_id <= MAX_USER_ID:
        return "user"

    raise ValueError(f"Неверный peer id: {peer_id}")


async def get_user_and_name(message):
    if message.reply_to_message.from_user:
        return (
            message.reply_to_message.from_user.id,
            message.reply_to_message.from_user.first_name,
        )
    elif message.reply_to_message.sender_chat:
        return (
            message.reply_to_message.sender_chat.id,
            message.reply_to_message.sender_chat.title,
        )


async def _resolve_user(client, message, arg):
    """Определяет пользователя по имени или ID, возвращает (user_obj, name) или None."""
    try:
        if await check_username_or_id(arg) == "channel":
            user = await client.get_chat(arg)
        elif await check_username_or_id(arg) == "user":
            user = await client.get_users(arg)
        else:
            await message.edit("<b>Неверный тип пользователя</b>")
            return None
    except (PeerIdInvalid, UsernameInvalid, IndexError):
        await message.edit("<b>Пользователь не найден</b>")
        return None

    name = (
        user.first_name
        if getattr(user, "first_name", None)
        else user.title
    )
    return user, name


async def _admin_catch_errors(message, func):
    """Выполняет административное действие с стандартной обработкой ошибок."""
    try:
        await func()
    except UserAdminInvalid:
        await message.edit("<b>Нет прав</b>")
    except ChatAdminRequired:
        await message.edit("<b>Нет прав</b>")
    except Exception as e:
        await message.edit(format_exc(e))


def _parse_cause(cause: str, idx: int = 1) -> str:
    parts = cause.split()
    return " ".join(parts[idx:]) if len(parts) > idx else ""


def _make_admin_command(cmd_name, action, action_msg, extra_flags=None):
    """
    Фабрика команд ban/unban/kick/mute/unmute/promote/demote.
    Все имеют одинаковую структуру reply-or-username с общей обработкой ошибок.
    """
    async def handler(client: Client, message: Message):
        cause = text(message)
        if not (await is_group_chat_async(message)):
            return await message.edit("<b>Неподдерживается</b>")

        if message.reply_to_message:
            if not message.reply_to_message.from_user:
                return await message.edit("<b>Ответьте на сообщение пользователя</b>")

            user_id, name = await get_user_and_name(message)
            cause_text = _parse_cause(cause, 1)

            if extra_flags and "report_spam" in cause.lower().split():
                channel = await client.resolve_peer(message.chat.id)
                user_peer = await client.resolve_peer(user_id)
                await client.invoke(
                    functions.channels.ReportSpam(
                        channel=channel,
                        participant=user_peer,
                        id=[message.reply_to_message.id],
                    )
                )
            if extra_flags and "delete_history" in cause.lower().split():
                channel = await client.resolve_peer(message.chat.id)
                user_peer = await client.resolve_peer(user_id)
                await client.invoke(
                    functions.channels.DeleteParticipantHistory(
                        channel=channel, participant=user_peer
                    )
                )

            await _admin_catch_errors(
                message,
                lambda: action(client, message, user_id, name),
            )
            if cause_text:
                # append cause to message
                pass
        elif len(cause.split()) > 1:
            resolved = await _resolve_user(client, message, cause.split(" ")[1])
            if resolved is None:
                return
            user, name = resolved
            cause_text = _parse_cause(cause, 2)

            await _admin_catch_errors(
                message,
                lambda: action(client, message, user.id, name),
            )
        else:
            await message.edit("<b>user_id или username</b>")

    return handler


async def is_group_chat_async(message: Message) -> bool:
    return message.chat.type not in ["private", "channel"]


# --- Generic admin actions ---

async def _ban(client, message, user_id, name):
    await client.ban_chat_member(message.chat.id, user_id)
    await message.edit(f"<b>{name}</b> <code>забанен!</code>")

async def _unban(client, message, user_id, name):
    await client.unban_chat_member(message.chat.id, user_id)
    await message.edit(f"<b>{name}</b> <code>разбанен!</code>")

async def _kick(client, message, user_id, name):
    await client.ban_chat_member(
        message.chat.id, user_id, datetime.now() + timedelta(minutes=1)
    )
    await message.edit(f"<b>{name}</b> <code>кикнут!</code>")

async def _unmute(client, message, user_id, name):
    await client.restrict_chat_member(
        message.chat.id, user_id, message.chat.permissions,
        datetime.now() + timedelta(seconds=30),
    )
    await message.edit(f"<b>{name}</b> <code>размучен</code>")

async def _demote(client, message, user_id, name):
    await client.promote_chat_member(
        message.chat.id, user_id,
        privileges=ChatPrivileges(
            is_anonymous=False,
            can_manage_chat=False,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
        ),
    )
    await message.edit(f"<b>{name}</b> <code>понижен!</code>")

async def _promote(client, message, user_id, name):
    await client.promote_chat_member(
        message.chat.id, user_id,
        privileges=ChatPrivileges(
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
        ),
    )
    if len(text(message).split()) > 1:
        await client.set_administrator_title(
            message.chat.id, user_id, text(message).split(maxsplit=1)[1]
        )
    await message.edit(f"<b>{name}</b> <code>повышен!</code>")


# --- Register commands ---

@Client.on_message(filters.command(["ban"], prefix) & filters.me)
async def ban_command(client: Client, message: Message):
    await _make_admin_command("ban", _ban, "banned", extra_flags=True)(client, message)

@Client.on_message(filters.command(["unban"], prefix) & filters.me)
async def unban_command(client: Client, message: Message):
    await _make_admin_command("unban", _unban, "unbanned")(client, message)

@Client.on_message(filters.command(["kick"], prefix) & filters.me)
async def kick_command(client: Client, message: Message):
    await _make_admin_command("kick", _kick, "kicked", extra_flags=True)(client, message)

@Client.on_message(filters.command(["unmute"], prefix) & filters.me)
async def unmute_command(client: Client, message: Message):
    await _make_admin_command("unmute", _unmute, "unmuted")(client, message)

@Client.on_message(filters.command(["demote"], prefix) & filters.me)
async def demote_command(client: Client, message: Message):
    await _make_admin_command("demote", _demote, "demoted")(client, message)

@Client.on_message(filters.command(["promote"], prefix) & filters.me)
async def promote_command(client: Client, message: Message):
    await _make_admin_command("promote", _promote, "promoted")(client, message)


@Client.on_message(filters.command(["kickdel"], prefix) & filters.me)
@handle_errors
async def kickdel_cmd(client: Client, message: Message):
    await message.edit("<b>Кикаю удалённые аккаунты...</b>")
    values = [
        await message.chat.ban_member(
            member.user.id, datetime.now() + timedelta(seconds=31)
        )
        async for member in client.get_chat_members(message.chat.id)
        if member.user.is_deleted
    ]
    await message.edit(
        f"<b>Успешно кикнуто {len(values)} удалённых аккаунтов</b>"
    )


@Client.on_message(filters.command(["tmute"], prefix) & filters.me)
async def tmute_command(client: Client, message: Message):
    cause = text(message)
    if is_group_chat(message):
        user_for_tmute, name = await get_user_and_name(message)

        if (
            message.reply_to_message.from_user
            and message.reply_to_message.from_user.is_self
        ):
            return await message.edit("<b>Нельзя на себя</b>")

        tmuted_users = db.get("core.ats", f"c{message.chat.id}", [])
        if user_for_tmute not in tmuted_users:
            tmuted_users.append(user_for_tmute)
            db.set("core.ats", f"c{message.chat.id}", tmuted_users)
            await message.edit(
                f"<b>{name}</b> <code>в тмьют</code>"
                + f"\n{'<b>Причина:</b> <i>' + cause.split(maxsplit=1)[1] + '</i>' if len(cause.split()) > 1 else ''}"
            )
        else:
            await message.edit(f"<b>{name}</b> <code>уже в тмьют</code>")

    elif not message.reply_to_message and is_group_chat(message):
        if len(cause.split()) > 1:
            try:
                if await check_username_or_id(cause.split(" ")[1]) == "channel":
                    user_to_tmute = await client.get_chat(cause.split(" ")[1])
                elif await check_username_or_id(cause.split(" ")[1]) == "user":
                    user_to_tmute = await client.get_users(cause.split(" ")[1])
                    if user_to_tmute.is_self:
                        return await message.edit("<b>Нельзя на себя</b>")
                else:
                    await message.edit("<b>Неверный тип пользователя</b>")
                    return

                name = (
                    user_to_tmute.first_name
                    if getattr(user_to_tmute, "first_name", None)
                    else user_to_tmute.title
                )

                tmuted_users = db.get("core.ats", f"c{message.chat.id}", [])
                if user_to_tmute.id not in tmuted_users:
                    tmuted_users.append(user_to_tmute.id)
                    db.set("core.ats", f"c{message.chat.id}", tmuted_users)
                    await message.edit(
                        f"<b>{name}</b> <code>в тмьют</code>"
                        + f"\n{'<b>Причина:</b> <i>' + cause.split(maxsplit=2)[2] + '</i>' if len(cause.split()) > 2 else ''}"
                    )
                else:
                    await message.edit(
                        f"<b>{name}</b> <code>уже в тмьют</code>"
                    )

            except PeerIdInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except UsernameInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except IndexError:
                await message.edit("<b>Пользователь не найден</b>")
        else:
            await message.edit("<b>user_id или username</b>")
    else:
        await message.edit("<b>Неподдерживается</b>")

    update_cache()


@Client.on_message(filters.command(["tunmute"], prefix) & filters.me)
async def tunmute_command(client: Client, message: Message):
    cause = text(message)
    if is_group_chat(message):
        user_for_tunmute, name = await get_user_and_name(message)

        tmuted_users = db.get("core.ats", f"c{message.chat.id}", [])
        if user_for_tunmute not in tmuted_users:
            await message.edit(f"<b>{name}</b> <code>не в тмьют</code>")
        else:
            tmuted_users.remove(user_for_tunmute)
            db.set("core.ats", f"c{message.chat.id}", tmuted_users)
            await message.edit(
                f"<b>{name}</b> <code>снят с тмьют</code>"
                + f"\n{'<b>Причина:</b> <i>' + cause.split(maxsplit=1)[1] + '</i>' if len(cause.split()) > 1 else ''}"
            )

    elif not message.reply_to_message and is_group_chat(message):
        if len(cause.split()) > 1:
            try:
                if await check_username_or_id(cause.split(" ")[1]) == "channel":
                    user_to_tunmute = await client.get_chat(cause.split(" ")[1])
                elif await check_username_or_id(cause.split(" ")[1]) == "user":
                    user_to_tunmute = await client.get_users(cause.split(" ")[1])
                    if user_to_tunmute.is_self:
                        return await message.edit("<b>Нельзя на себя</b>")
                else:
                    await message.edit("<b>Неверный тип пользователя</b>")
                    return

                name = (
                    user_to_tunmute.first_name
                    if getattr(user_to_tunmute, "first_name", None)
                    else user_to_tunmute.title
                )

                tmuted_users = db.get("core.ats", f"c{message.chat.id}", [])
                if user_to_tunmute.id not in tmuted_users:
                    await message.edit(
                        f"<b>{name}</b> <code>не в тмьют</code>"
                    )
                else:
                    tmuted_users.remove(user_to_tunmute.id)
                    db.set("core.ats", f"c{message.chat.id}", tmuted_users)
                    await message.edit(
                        f"<b>{name}</b> <code>снят с тмьют</code>"
                        + f"\n{'<b>Причина:</b> <i>' + cause.split(maxsplit=2)[2] + '</i>' if len(cause.split()) > 2 else ''}"
                    )
            except PeerIdInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except UsernameInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except IndexError:
                await message.edit("<b>Пользователь не найден</b>")
        else:
            await message.edit("<b>user_id или username</b>")
    else:
        await message.edit("<b>Неподдерживается</b>")

    update_cache()


@Client.on_message(filters.command(["mute"], prefix) & filters.me)
@handle_errors
async def mute_command(client: Client, message: Message):
    cause = text(message)
    if message.reply_to_message and is_group_chat(message):
        mute_seconds: int = 0
        for character in "mhdw":
            match = re.search(rf"(\d+|(\d+\.\d+)){character}", message.text)
            if match:
                if character == "m":
                    mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 60 // 1)
                if character == "h":
                    mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 3600 // 1)
                if character == "d":
                    mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 86400 // 1)
                if character == "w":
                    mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 604800 // 1)
        try:
            if mute_seconds > 30:
                await client.restrict_chat_member(
                    message.chat.id,
                    message.reply_to_message.from_user.id,
                    ChatPermissions(),
                    datetime.now() + timedelta(seconds=mute_seconds),
                )
                from_user = message.reply_to_message.from_user
                mute_time: Dict[str, int] = {
                    "days": mute_seconds // 86400,
                    "hours": mute_seconds % 86400 // 3600,
                    "minutes": mute_seconds % 86400 % 3600 // 60,
                }
                message_text = (
                    f"<b>{from_user.first_name}</b> <code> замучен на"
                    f" {((str(mute_time['days']) + ' дн') if mute_time['days'] > 0 else '') + ('' if mute_time['days'] <= 1 else '')}"
                    f" {((str(mute_time['hours']) + ' ч') if mute_time['hours'] > 0 else '')}"
                    f" {((str(mute_time['minutes']) + ' мин') if mute_time['minutes'] > 0 else '')}</code>"
                    + f"\n{'<b>Причина:</b> <i>' + cause.split(' ', maxsplit=2)[2] + '</i>' if len(cause.split()) > 2 else ''}"
                )
                while "  " in message_text:
                    message_text = message_text.replace("  ", " ")
            else:
                await client.restrict_chat_member(
                    message.chat.id,
                    message.reply_to_message.from_user.id,
                    ChatPermissions(),
                )
                message_text = (
                    f"<b>{message.reply_to_message.from_user.first_name}</b> <code> замучен бессрочно</code>"
                    + f"\n{'<b>Причина:</b> <i>' + cause.split(' ', maxsplit=1)[1] + '</i>' if len(cause.split()) > 1 else ''}"
                )
            await message.edit(message_text)
        except UserAdminInvalid:
            await message.edit("<b>Нет прав</b>")
        except ChatAdminRequired:
            await message.edit("<b>Нет прав</b>")
    elif not message.reply_to_message and is_group_chat(message):
        if len(cause.split()) > 1:
            try:
                user_to_mute = await client.get_users(cause.split(" ")[1])
                mute_seconds: int = 0
                for character in "mhdw":
                    match = re.search(rf"(\d+|(\d+\.\d+)){character}", message.text)
                    if match:
                        if character == "m":
                            mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 60 // 1)
                        if character == "h":
                            mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 3600 // 1)
                        if character == "d":
                            mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 86400 // 1)
                        if character == "w":
                            mute_seconds += int(float(match.string[match.start() : match.end() - 1]) * 604800 // 1)
                try:
                    if mute_seconds > 30:
                        await client.restrict_chat_member(
                            message.chat.id,
                            user_to_mute.id,
                            ChatPermissions(),
                            datetime.now() + timedelta(seconds=mute_seconds),
                        )
                        mute_time: Dict[str, int] = {
                            "days": mute_seconds // 86400,
                            "hours": mute_seconds % 86400 // 3600,
                            "minutes": mute_seconds % 86400 % 3600 // 60,
                        }
                        message_text = (
                            f"<b>{user_to_mute.first_name}</b> <code> замучен на"
                            f" {((str(mute_time['days']) + ' дн') if mute_time['days'] > 0 else '') + ('' if mute_time['days'] <= 1 else '')}"
                            f" {((str(mute_time['hours']) + ' ч') if mute_time['hours'] > 0 else '')}"
                            f" {((str(mute_time['minutes']) + ' мин') if mute_time['minutes'] > 0 else '')}</code>"
                            + f"\n{'<b>Причина:</b> <i>' + cause.split(' ', maxsplit=3)[3] + '</i>' if len(cause.split()) > 3 else ''}"
                        )
                        while "  " in message_text:
                            message_text = message_text.replace("  ", " ")
                    else:
                        await client.restrict_chat_member(
                            message.chat.id,
                            user_to_mute.id,
                            ChatPermissions(),
                        )
                        message_text = (
                            f"<b>{user_to_mute.first_name}</b> <code> замучен бессрочно</code>"
                            + f"\n{'<b>Причина:</b> <i>' + cause.split(' ', maxsplit=2)[2] + '</i>' if len(cause.split()) > 2 else ''}"
                        )
                    await message.edit(message_text)
                except UserAdminInvalid:
                    await message.edit("<b>Нет прав</b>")
                except ChatAdminRequired:
                    await message.edit("<b>Нет прав</b>")
            except PeerIdInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except UsernameInvalid:
                await message.edit("<b>Пользователь не найден</b>")
            except IndexError:
                await message.edit("<b>Пользователь не найден</b>")
        else:
            await message.edit("<b>user_id или username</b>")
    else:
        await message.edit("<b>Неподдерживается</b>")


@Client.on_message(filters.command(["tmute_users"], prefix) & filters.me)
async def tunmute_users_command(client: Client, message: Message):
    if is_group_chat(message):
        text = f"<b>Все пользователи</b> <code>{message.chat.title}</code> <b>, которые сейчас в тмьют</b>\n\n"
        count = 0
        tmuted_users = db.get("core.ats", f"c{message.chat.id}", [])
        for user in tmuted_users:
            try:
                _name_ = await client.get_chat(user)
                count += 1
                if await check_username_or_id(_name_.id) == "channel":
                    channel = await client.invoke(
                        functions.channels.GetChannels(
                            id=[
                                types.InputChannel(
                                    channel_id=get_channel_id(_name_.id),
                                    access_hash=0,
                                )
                            ]
                        )
                    )
                    name = channel.chats[0].title
                elif await check_username_or_id(_name_.id) == "user":
                    user = await client.get_users(_name_.id)
                    name = user.first_name
                else:
                    continue
                text += f"{count}. <b>{name}</b>\n"
            except PeerIdInvalid:
                pass
        if count == 0:
            await message.edit("<b>Нет пользователей в тмьют</b>")
        else:
            text += f"\n<b>Всего пользователей в тмьют</b> {count}"
            await message.edit(text)
    else:
        await message.edit("<b>Неподдерживается</b>")


@Client.on_message(filters.command(["antich"], prefix))
async def anti_channels(client: Client, message: Message):
    if message.chat.type != "supergroup":
        await message.edit("<b>Не поддерживается в чатах, отличных от супергрупп</b>")
        return

    if len(message.command) == 1:
        if db.get("core.ats", f"antich{message.chat.id}", False):
            await message.edit(
                "<b>Блокировка каналов в этом чате включена.\n"
                f"Отключить: </b><code>{prefix}antich disable</code>"
            )
        else:
            await message.edit(
                "<b>Блокировка каналов в этом чате выключена.\n"
                f"Включить: </b><code>{prefix}antich enable</code>"
            )
    elif message.command[1] in ["enable", "on", "1", "yes", "true"]:
        db.set("core.ats", f"antich{message.chat.id}", True)
        group = await client.get_chat(message.chat.id)
        if group.linked_chat:
            db.set("core.ats", f"linked{message.chat.id}", group.linked_chat.id)
        else:
            db.set("core.ats", f"linked{message.chat.id}", 0)
        await message.edit("<b>Блокировка каналов в этом чате включена.</b>")
    elif message.command[1] in ["disable", "off", "0", "no", "false"]:
        db.set("core.ats", f"antich{message.chat.id}", False)
        await message.edit("<b>Блокировка каналов в этом чате выключена.</b>")
    else:
        await message.edit(f"<b>Использование: {prefix}antich [enable|disable]</b>")

    update_cache()


@Client.on_message(filters.command(["delete_history", "dh"], prefix))
@with_reply
@handle_admin_errors
async def delete_history(client: Client, message: Message):
    cause = text(message)
    user_for_delete, name = await get_user_and_name(message)

    channel = await client.resolve_peer(message.chat.id)
    user_id = await client.resolve_peer(user_for_delete)
    await client.invoke(
        functions.channels.DeleteParticipantHistory(
            channel=channel, participant=user_id
        )
    )
    await message.edit(
        f"<code>История от <b>{name}</b> удалена!</code>"
        + f"\n{'<b>Причина:</b> <i>' + cause.split(maxsplit=1)[1] + '</i>' if len(cause.split()) > 1 else ''}"
    )


@Client.on_message(filters.command(["report_spam", "rs"], prefix))
@with_reply
@handle_errors
async def report_spam(client: Client, message: Message):
    channel = await client.resolve_peer(message.chat.id)

    user_id, name = await get_user_and_name(message)
    peer = await client.resolve_peer(user_id)
    await client.invoke(
        functions.channels.ReportSpam(
            channel=channel,
            participant=peer,
            id=[message.reply_to_message.id],
        )
    )
    await message.edit(f"<b>Сообщение</b> от {name} <b>пожаловано на спам</b>")


@Client.on_message(filters.command("pin", prefix) & filters.me)
@with_reply
@handle_errors
async def pin(client: Client, message: Message):
    await message.reply_to_message.pin()
    await message.edit("<b>Закреплено!</b>")


@Client.on_message(filters.command("unpin", prefix) & filters.me)
@with_reply
@handle_errors
async def unpin(client: Client, message: Message):
    await message.reply_to_message.unpin()
    await message.edit("<b>Откреплено!</b>")


@Client.on_message(filters.command("ro", prefix) & filters.me)
@handle_admin_errors
async def ro(client: Client, message: Message):
    if message.chat.type != "supergroup":
        await message.edit("<b>Неверный тип чата</b>")
        return

    perms = message.chat.permissions
    perms_list = [
        perms.can_send_messages,
        perms.can_send_media_messages,
        perms.can_send_other_messages,
        perms.can_send_polls,
        perms.can_add_web_page_previews,
        perms.can_change_info,
        perms.can_invite_users,
        perms.can_pin_messages,
    ]
    db.set("core.ats", f"ro{message.chat.id}", perms_list)

    await client.set_chat_permissions(
        message.chat.id, ChatPermissions()
    )
    await message.edit(
        "<b>Режим только чтение включён!\n"
        f"Выключить: </b><code>{prefix}unro</code>"
    )


@Client.on_message(filters.command("unro", prefix) & filters.me)
@handle_admin_errors
async def unro(client: Client, message: Message):
    if message.chat.type != "supergroup":
        await message.edit("<b>Неверный тип чата</b>")
        return

    perms_list = db.get(
        "core.ats",
        f"ro{message.chat.id}",
        [True, True, True, False, False, False, False, False],
    )
    perms = ChatPermissions(
        can_send_messages=perms_list[0],
        can_send_media_messages=perms_list[1],
        can_send_other_messages=perms_list[2],
        can_send_polls=perms_list[3],
        can_add_web_page_previews=perms_list[4],
        can_change_info=perms_list[5],
        can_invite_users=perms_list[6],
        can_pin_messages=perms_list[7],
    )

    await client.set_chat_permissions(message.chat.id, perms)
    await message.edit("<b>Режим только чтение выключен!</b>")


@Client.on_message(filters.command("antiraid", prefix) & filters.me)
async def antiraid(client: Client, message: Message):
    if message.chat.type != "supergroup":
        await message.edit("<b>Не поддерживается в чатах, отличных от супергрупп</b>")
        return

    if len(message.command) > 1 and message.command[1] == "on":
        db.set("core.ats", f"antiraid{message.chat.id}", True)
        group = await client.get_chat(message.chat.id)
        if group.linked_chat:
            db.set("core.ats", f"linked{message.chat.id}", group.linked_chat.id)
        else:
            db.set("core.ats", f"linked{message.chat.id}", 0)
        await message.edit(
            "<b>Режим антирейд включён!\n"
            f"Выключить: </b><code>{prefix}antiraid off</code>"
        )
    elif len(message.command) > 1 and message.command[1] == "off":
        db.set("core.ats", f"antiraid{message.chat.id}", False)
        await message.edit("<b>Режим антирейд выключен</b>")
    else:
        if db.get("core.ats", f"antiraid{message.chat.id}", False):
            db.set("core.ats", f"antiraid{message.chat.id}", False)
            await message.edit("<b>Режим антирейд выключен</b>")
        else:
            db.set("core.ats", f"antiraid{message.chat.id}", True)
            group = await client.get_chat(message.chat.id)
            if group.linked_chat:
                db.set(
                    "core.ats", f"linked{message.chat.id}", group.linked_chat.id
                )
            else:
                db.set("core.ats", f"linked{message.chat.id}", 0)
            await message.edit(
                "<b>Режим антирейд включён!\n"
                f"Выключить: </b><code>{prefix}antiraid off</code>"
            )

    update_cache()


@Client.on_message(filters.command(["welcome", "wc"], prefix) & filters.me)
async def welcome(_, message: Message):
    if message.chat.type != "supergroup":
        return await message.edit("<b>Неподдерживаемый тип чата</b>")

    if len(message.command) > 1:
        text = message.text.split(maxsplit=1)[1]
        db.set("core.ats", f"welcome_enabled{message.chat.id}", True)
        db.set("core.ats", f"welcome_text{message.chat.id}", text)

        await message.edit(
            f"<b>Приветствие включено в этом чате\nТекст:</b> <code>{text}</code>"
        )
    else:
        db.set("core.ats", f"welcome_enabled{message.chat.id}", False)
        await message.edit("<b>Приветствие выключено в этом чате</b>")

    update_cache()


modules_help["admintool"] = {
    "ban [reply]/[username/id]* [reason] [report_spam] [delete_history]": "забанить пользователя в чате",
    "unban [reply]/[username/id]* [reason]": "разбанить пользователя в чате",
    "kick [reply]/[userid]* [reason] [report_spam] [delete_history]": "кикнуть пользователя из чата",
    "mute [reply]/[userid]* [reason] [1m]/[1h]/[1d]/[1w]": "замьютить пользователя в чате",
    "unmute [reply]/[userid]* [reason]": "размьютить пользователя в чате",
    "promote [reply]/[userid]* [prefix]": "повысить пользователя в чате",
    "demote [reply]/[userid]* [reason]": "понизить пользователя в чате",
    "tmute [reply]/[username/id]* [reason]": "удалить все новые сообщения от пользователя в чате",
    "tunmute [reply]/[username/id]* [reason]": "прекратить удаление всех сообщений от пользователя в чате",
    "tmute_users": "список пользователей в тмьют (.tmute)",
    "antich [enable/disable]": "включить/выключить блокировку каналов в этом чате",
    "delete_history [reply]/[username/id]* [reason]": "удалить историю сообщений участника в чате",
    "report_spam [reply]*": "пожаловаться на спам в чате",
    "pin [reply]*": "Закрепить ответное сообщение",
    "unpin [reply]*": "Открепить ответное сообщение",
    "ro": "включить режим только чтение",
    "unro": "выключить режим только чтение",
    "antiraid [on|off]": "при включении каждый, кто напишет сообщение, будет заблокирован. Полезно при рейдах. "
    "Запуск без аргументов переключает состояние",
    "welcome [text]*": "включить авто-приветствие новых пользователей в группах. "
    "Запуск без текста выключает",
    "kickdel": "Кикнуть все удалённые аккаунты",
}