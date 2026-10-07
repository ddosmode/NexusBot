import asyncio
import logging
import os
import platform
import sqlite3
import subprocess
from pathlib import Path

from pyrogram import Client, errors, idle
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.raw.functions.account import DeleteAccount, GetAuthorizations

from utils import config
from utils.db import db
from utils.misc import gitrepo, userbot_version
from utils.scripts import load_module, restart
from utils.constants import PROJECT_NAME

script_path = os.path.dirname(os.path.realpath(__file__))
if script_path != os.getcwd():
    os.chdir(script_path)

app = Client(
    "my_account",
    api_id=config.api_id,
    api_hash=config.api_hash,
    hide_password=True,
    workdir=script_path,
    app_version=userbot_version,
    device_model=f"{PROJECT_NAME} @ {gitrepo.head.commit.hexsha[:7]}",
    system_version=platform.version() + " " + platform.machine(),
    sleep_threshold=30,
    test_mode=config.test_server,
    parse_mode=ParseMode.HTML,
)


async def main():
    logging.basicConfig(level=logging.INFO)
    DeleteAccount.__new__ = None

    try:
        await app.start()
    except sqlite3.OperationalError as e:
        if str(e) == "database is locked" and os.name == "posix":
            logging.warning(
                "Файл сессии заблокирован. Попытка убить блокирующий процесс..."
            )
            subprocess.run(["fuser", "-k", "my_account.session"])
            restart()
        raise
    except (errors.NotAcceptable, errors.Unauthorized) as e:
        logging.error(
            f"{e.__class__.__name__}: {e}\n"
            f"Перемещение файла сессии в my_account.session-old..."
        )
        os.rename("./my_account.session", "./my_account.session-old")
        restart()

    success_modules = 0
    failed_modules = 0

    for path in Path("modules").rglob("*.py"):
        try:
            await load_module(
                path.stem, app, core="custom_modules" not in path.parent.parts
            )
        except Exception:
            logging.warning(f"Не удалось импортировать модуль {path.stem}", exc_info=True)
            failed_modules += 1
        else:
            success_modules += 1

    logging.info(f"Импортировано {success_modules} модулей")
    if failed_modules:
        logging.warning(f"Не удалось импортировать {failed_modules} модулей")

    if info := db.get("core.updater", "restart_info"):
        text = {
            "restart": "<b>Перезапуск завершён!</b>",
            "update": "<b>Процесс обновления завершён!</b>",
        }[info["type"]]
        try:
            await app.edit_message_text(
                info["chat_id"], info["message_id"], text
            )
        except errors.RPCError:
            pass
        db.remove("core.updater", "restart_info")

    # required for sessionkiller module
    if db.get("core.sessionkiller", "enabled", False):
        db.set(
            "core.sessionkiller",
            "auths_hashes",
            [
                auth.hash
                for auth in (
                    await app.invoke(GetAuthorizations())
                ).authorizations
            ],
        )

    logging.info("NexusBot запущен!")

    await idle()

    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
