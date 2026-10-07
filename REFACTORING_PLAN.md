# Рефакторинг: устранение дублирования кода в Nexus-Userbot

## Цель
Заменить дублирующиеся паттерны на переиспользуемые константы и хелперы без изменения функционала.

## Этапы

### 1. utils/constants.py (готово)
- `GITHUB_REPO`, `CHANNEL`, `MODULES_CHANNEL`, `CHAT`
- `DEFAULT_API_ID`, `DEFAULT_API_HASH`
- `CUSTOM_MODULES_RAW_URL`, `CUSTOM_MODULES_API_URL`
- `MONGODB_URL_HELP`

### 2. utils/scripts.py (готово)
- `@handle_errors` — декоратор для try/except с format_exc
- `is_group_chat(message)` — проверка типа чата
- `admin_cause(message, idx)` — извлечение причины из команды

### 3. modules/admintool.py (1347 строк → ~350 строк)
- Переписать ban/unban/kick/mute/unmute/promote/demote через общий `_admin_command` хелпер
- tmute/tunmute/kickdel/antich/ro/unro/antiraid/welcome/report_spam/pin/unpin — оставить как есть
- Использовать `@handle_errors`, `is_group_chat`, `admin_cause`

### 4. modules/support.py
- Использовать константы из utils.constants

### 5. modules/loader.py (готово)
- Использовать `CUSTOM_MODULES_RAW_URL`/`CUSTOM_MODULES_API_URL`

### 6. main.py
- Использовать константу для device_model

### 7. Проверка
- `python3 -m py_compile` на всех изменённых файлах
- Проверить импорт модулей

## Принятые решения
- requirements.txt URL pyrogram не меняется (функциональная зависимость)
- tmute/tunmute остаются отдельными (логика с БД)
