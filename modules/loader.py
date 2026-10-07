import os

import requests
from pyrogram import Client, filters
from pyrogram.types import Message

from utils.config import modules_repo_branch
from utils.misc import modules_help, prefix
from utils.scripts import (
    format_exc,
    format_module_help,
    handle_errors,
    load_module,
    restart,
    unload_module,
)
from utils.constants import (
    CUSTOM_MODULES_RAW_URL,
    CUSTOM_MODULES_API_URL,
)

BASE_PATH = os.path.abspath(os.getcwd())


@Client.on_message(filters.command(["loadmod", "lm"], prefix) & filters.me)
async def loadmod(client: Client, message: Message):
    if len(message.command) == 1:
        await message.edit("<b>Укажите модуль для загрузки</b>")
        return

    module_name = message.command[1].lower()
    resp = requests.get(
        CUSTOM_MODULES_RAW_URL
        + f"/custom_modules/{modules_repo_branch}/{module_name}.py"
    )
    if not resp.ok:
        await message.edit(
            f"<b>Модуль <code>{module_name}</code> не найден</b>"
        )
        return

    if not os.path.exists(f"{BASE_PATH}/modules/custom_modules"):
        os.mkdir(f"{BASE_PATH}/modules/custom_modules")

    with open(f"./modules/custom_modules/{module_name}.py", "wb") as f:
        f.write(resp.content)

    try:
        module = await load_module(module_name, client, message)
    except Exception as e:
        os.remove(f"./modules/custom_modules/{module_name}.py")
        return await message.edit(format_exc(e))

    await message.edit(
        f"<b>Модуль <code>{module_name}</code> загружен!</b>\n\n"
        f"{format_module_help(module_name, False)}"
    )


@Client.on_message(filters.command(["unloadmod", "ulm"], prefix) & filters.me)
@handle_errors
async def unload_mods(client: Client, message: Message):
    if len(message.command) <= 1:
        return await message.edit("<b>Укажите модуль для выгрузки</b>")

    module_name = message.command[1].lower()

    if os.path.exists(f"{BASE_PATH}/modules/custom_modules/{module_name}.py"):
        await unload_module(module_name, client)
        os.remove(f"{BASE_PATH}/modules/custom_modules/{module_name}.py")
        await message.edit(
            f"<b>Модуль <code>{module_name}</code> удалён!</b>"
        )
    elif os.path.exists(f"{BASE_PATH}/modules/{module_name}.py"):
        await message.edit(
            "<b>Запрещено удалять встроенные модули, это сломает обновления</b>"
        )
    else:
        await message.edit(
            f"<b>Модуль <code>{module_name}</code> не найден</b>"
        )


@Client.on_message(filters.command(["loadallmods"], prefix) & filters.me)
async def load_all_mods(client: Client, message: Message):
    await message.edit("<b>Получение информации...</b>")

    if not os.path.exists(f"{BASE_PATH}/modules/custom_modules"):
        os.mkdir(f"{BASE_PATH}/modules/custom_modules")

    modules_list = requests.get(
        CUSTOM_MODULES_API_URL,
        params={"ref": modules_repo_branch},
    ).json()

    new_modules = {}
    for module_info in modules_list:
        if not module_info["name"].endswith(".py"):
            continue
        if os.path.exists(
            f'{BASE_PATH}/modules/custom_modules/{module_info["name"]}'
        ):
            continue
        new_modules[module_info["name"][:-3]] = module_info["download_url"]
    if not new_modules:
        return await message.edit("<b>Все модули уже загружены</b>")

    await message.edit(
        f"<b>Загрузка новых модулей (может занять много времени): "
        f'{" ".join(new_modules.keys())}</b>'
    )

    for module_name, url in new_modules.items():
        with open(f"./modules/custom_modules/{module_name}.py", "wb") as f:
            f.write(requests.get(url).content)

        await load_module(module_name, client)

    await message.edit(
        f'<b>Успешно загружены новые модули: {" ".join(new_modules.keys())}</b>'
    )


@Client.on_message(filters.command(["updateallmods"], prefix) & filters.me)
async def updateallmods(_, message: Message):
    await message.edit("<b>Обновление модулей...</b>")

    if not os.path.exists(f"{BASE_PATH}/modules/custom_modules"):
        os.mkdir(f"{BASE_PATH}/modules/custom_modules")

    modules_installed = list(os.walk("modules/custom_modules"))[0][2]

    if not modules_installed:
        return await message.edit("<b>У вас не установлено ни одного модуля</b>")

    for module_name in modules_installed:
        if not module_name.endswith(".py"):
            continue

        resp = requests.get(
            CUSTOM_MODULES_RAW_URL
            + f"/custom_modules/{modules_repo_branch}/{module_name}"
        )
        if not resp.ok:
            modules_installed.remove(module_name)
            continue

        with open(f"./modules/custom_modules/{module_name}", "wb") as f:
            f.write(resp.content)

    await message.edit(
        f"<b>Успешно обновлено модулей: {len(modules_installed)}</b>"
    )

    restart()


modules_help["loader"] = {
    "loadmod [module_name]*": (
        "Скачать модуль.\n"
        "Поддерживаются только модули из официального репозитория custom_modules"
    ),
    "unloadmod [module_name]*": "Удалить модуль",
    "loadallmods": "Загрузить все пользовательские модули (на свой страх и риск)",
    "updateallmods": "Обновить все загруженные пользовательские модули",
}