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

import datetime
import sys

from pyrogram import Client, errors

from utils import config
from utils.constants import (
    CHANNEL,
    CHAT,
    MODULES_CHANNEL,
)

if __name__ == "__main__":
    app = Client(
        "my_account",
        api_id=config.api_id,
        api_hash=config.api_hash,
        hide_password=True,
        test_mode=config.test_server,
    )

    if config.db_type in ["mongo", "mongodb"]:
        from pymongo import MongoClient, errors

        db = MongoClient(config.db_url)
        try:
            db.server_info()
        except errors.ConnectionFailure as e:
            raise RuntimeError(
                "Сервер MongoDB недоступен! "
                f"Указан URL: {config.db_url}. "
                "Введите действительный URL и перезапустите установку"
            ) from e

    install_type = sys.argv[1] if len(sys.argv) > 1 else "3"
    if install_type == "1":
        restart = "pm2 restart nexus"
    elif install_type == "2":
        restart = "sudo systemctl restart nexus"
    else:
        restart = "cd NexusBot/ && python main.py"

    app.start()
    try:
        app.send_message(
            "me",
            f"<b>[{datetime.datetime.now()}] NexusBot запущен! \n"
            f"Канал: {CHANNEL}\n"
            f"Пользовательские модули: {MODULES_CHANNEL}\n"
            f"Чат [RU]: {CHAT}\n"
            f"Для перезапуска введите:</b>\n"
            f"<code>{restart}</code>",
        )
    except errors.RPCError:
        pass
    app.stop()
