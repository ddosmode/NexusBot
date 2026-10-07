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

import datetime
import random

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
from pyrogram import Client, filters
from pyrogram.types import Message

from utils.misc import (
    gitrepo,
    modules_help,
    prefix,
    python_version,
    userbot_version,
)
from utils.constants import (
    GITHUB_REPO,
    CHANNEL,
    MODULES_CHANNEL,
    CHAT,
)


@Client.on_message(filters.command(["support", "repo"], prefix) & filters.me)
async def support(_, message: Message):
    devs = ["@john_ph0nk", "@fuccsoc2"]
    random.shuffle(devs)

    commands_count = float(
        len([cmd for module in modules_help for cmd in module])
    )

    await message.edit(
        f"<b>NexusBot\n\n"
        f"GitHub: <a href={GITHUB_REPO}>{GITHUB_REPO.split('/')[-1]}</a>\n"
        f"Репозиторий пользовательских модулей: <a href={GITHUB_REPO}/custom_modules>"
        f"{GITHUB_REPO.split('/')[-1]}/custom_modules</a>\n"
        f"Лицензия: <a href={GITHUB_REPO}/blob/master/LICENSE>GNU GPL v3</a>\n\n"
        f"Канал: {CHANNEL}\n"
        f"Пользовательские модули: {MODULES_CHANNEL}\n"
        f"Чат [RU]: {CHAT}\n"
        f"Основные разработчики: {', '.join(devs)}\n\n"
        f"Версия Python: {python_version}\n"
        f"Количество модулей: {len(modules_help) / 1}\n"
        f"Количество команд: {commands_count}</b>",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command(["version", "ver"], prefix) & filters.me)
async def version(client: Client, message: Message):
    changelog = ""
    ub_version = ".".join(userbot_version.split(".")[:2])
    async for m in client.search_messages(
        "Nexus_Userb0t", query=ub_version + "."
    ):
        if ub_version in m.text:
            changelog = m.id

    await message.delete()

    remote_url = list(gitrepo.remote().urls)[0]
    commit_time = (
        datetime.datetime.fromtimestamp(gitrepo.head.commit.committed_date)
        .astimezone(datetime.timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    await message.reply(
        f"<b>Версия NexusBot: {userbot_version}\n"
        f"Чейнджлог </b><i><a href=https://t.me/Nexus_Userb0t/{changelog}>в канале</a></i>.<b>\n"
        f"Чейнджлоги пишут </b><i>"
        f"<a href=tg://user?id=318865588>\u2060</a>"
        f"<a href=tg://user?id=293490416>♿️</a>"
        f"<a href=https://t.me/acnxua>asphuy</a>"
        f"<a href=https://t.me/artemjj2>♿️</a></i>\n\n"
        + (
            f"<b>Ветка: <a href={remote_url}/tree/{gitrepo.active_branch}>{gitrepo.active_branch}</a>\n"
            if gitrepo.active_branch != "master"
            else ""
        )
        + f"Коммит: <a href={remote_url}/commit/{gitrepo.head.commit.hexsha}>"
        f"{gitrepo.head.commit.hexsha[:7]}</a> by {gitrepo.head.commit.author.name}\n"
        f"Время коммита: {commit_time}</b>",
    )


modules_help["support"] = {
    "support": "Информация о юзерботе",
    "version": "Проверить версию юзербота",
}
