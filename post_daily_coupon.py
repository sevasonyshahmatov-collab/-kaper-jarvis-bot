"""
КАПЕР ДЖАРВИС — бот автопостинга прогнозов дня в Telegram-канал.

Что делает:
1. Подключается к Google Таблице КХЛ через сервисный аккаунт.
2. Читает лист "прогнозы", берёт строки с сегодняшней датой.
3. Собирает из них красивый текстовый пост.
4. Отправляет пост в Telegram-канал через Bot API.

Секреты (передаются как переменные окружения — их задаёт GitHub Actions
из GitHub Secrets, см. workflow-файл):
  TELEGRAM_BOT_TOKEN         — токен бота от BotFather
  GOOGLE_SERVICE_ACCOUNT_JSON — весь JSON-ключ сервисного аккаунта целиком (текстом)
  TELEGRAM_CHANNEL_ID        — @username канала (например, @kaper_jarvis_khl)
  SPREADSHEET_ID             — ID таблицы КХЛ (из ссылки на неё)
"""

import os
import json
import sys
from datetime import datetime, timedelta, timezone

import requests
import gspread
from google.oauth2.service_account import Credentials

# ---------- настройки ----------
SHEET_NAME = "прогнозы"
MOSCOW_TZ = timezone(timedelta(hours=3))  # у нас вся таблица в московском времени


def get_today_str():
    """Сегодняшняя дата по Москве в формате dd.mm.yyyy — так же, как хранится в таблице."""
    return datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y")


def connect_to_sheet():
    """Открывает лист "прогнозы" в таблице КХЛ через сервисный аккаунт."""
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet_id = os.environ["SPREADSHEET_ID"]
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(SHEET_NAME)


def parse_date_cell(value):
    """Ячейка с датой может прийти и как 'dd.mm.yyyy' текстом, и как настоящая
    дата (тогда gspread обычно тоже отдаёт строку в формате ячейки, но на
    всякий случай подстрахуемся от разных вариантов)."""
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return value


def get_todays_matches(worksheet):
    """Возвращает список сегодняшних матчей как список словарей."""
    today = get_today_str()
    rows = worksheet.get_all_values()
    header = rows[0]

    def col(name):
        return header.index(name)

    matches = []
    for row in rows[1:]:
        if not row or len(row) <= col("Хозяева"):
            continue
        row_date = parse_date_cell(row[col("Дата")])
        if row_date != today:
            continue
        matches.append({
            "home": row[col("Хозяева")],
            "away": row[col("Гости")],
            "chance_home": row[col("Шансы Хозяев, %")],
            "chance_away": row[col("Шансы Гостей, %")],
            "winner": row[col("Наиболее вероятный победитель")],
        })
    return matches


def format_message(matches):
    """Собирает текст поста для Telegram (поддерживается HTML-разметка)."""
    today = get_today_str()
    if not matches:
        return f"🏒 <b>КХЛ, {today}</b>\n\nСегодня матчей нет — отдыхаем."

    lines = [f"🏒 <b>КХЛ, прогнозы на {today}</b>\n"]
    for m in matches:
        lines.append(
            f"<b>{m['home']} — {m['away']}</b>\n"
            f"Шансы: {m['chance_home']}% / {m['chance_away']}%\n"
            f"Прогноз: {m['winner']}\n"
        )
    lines.append("⚠️ Прогнозы — не финансовый совет, ставьте с умом.")
    return "\n".join(lines)


def send_to_telegram(text):
    """Отправляет готовый текст в канал через Bot API."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML",
    }
    response = requests.post(url, json=payload, timeout=30)
    if not response.ok:
        print("Ошибка отправки в Telegram:", response.status_code, response.text)
        sys.exit(1)
    print("Пост успешно отправлен.")


def main():
    worksheet = connect_to_sheet()
    matches = get_todays_matches(worksheet)
    text = format_message(matches)
    print("--- Текст поста ---")
    print(text)
    print("-------------------")
    send_to_telegram(text)


if __name__ == "__main__":
    main()
