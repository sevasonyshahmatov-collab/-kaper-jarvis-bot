"""
КАПЕР ДЖАРВИС — агент-разведчик.

Раз в день проверяет ближайшие ещё не сыгранные матчи КХЛ, для каждого
через Claude (с включённым веб-поиском) ищет свежий контекст — травмы,
дисквалификации, смену тренера, необычный мотивационный фон — и записывает
короткую сводку на отдельный лист "Контекст и новости" в той же таблице.

ВАЖНО: этот агент только ЧИТАЕТ данные о матчах и ПИШЕТ в свой собственный
лист "Контекст и новости". Он никогда не трогает Data, Elo, прогнозы,
Купон дня и другие листы с формулами — так и задумано.

Секреты (переменные окружения, задаются через GitHub Secrets):
  ANTHROPIC_API_KEY           — ключ Anthropic
  GOOGLE_SERVICE_ACCOUNT_JSON — JSON-ключ сервисного аккаунта целиком
  SPREADSHEET_ID              — ID таблицы КХЛ
"""

import os
import json
from datetime import datetime, timedelta, timezone

import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic

MOSCOW_TZ = timezone(timedelta(hours=3))
DAYS_AHEAD = 2  # смотрим на матчи в ближайшие N дней (сегодня + завтра)
CONTEXT_SHEET_NAME = "Контекст и новости"
PREDICTIONS_SHEET_NAME = "прогнозы"
RESULTS_SHEET_NAME = "результаты матчей"

MODEL = "claude-sonnet-5"  # для экономии можно заменить на claude-haiku-4-5-20251001


def connect_to_spreadsheet():
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]  # нужна и запись, не только чтение
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(os.environ["SPREADSHEET_ID"])


def parse_date(value):
    """Дата в таблице может быть текстом 'дд.мм.гггг' или числом (Google Sheets serial)."""
    if not value:
        return None
    value = str(value).strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def get_upcoming_matches(spreadsheet):
    """Берёт из листа результатов матчи со статусом "Запланирован" в ближайшие DAYS_AHEAD дней."""
    ws = spreadsheet.worksheet(RESULTS_SHEET_NAME)
    rows = ws.get_all_values()
    header = rows[0]
    col = {name: header.index(name) for name in ("Дата", "Статус", "Хозяева", "Гости")}

    today = datetime.now(MOSCOW_TZ).date()
    cutoff = today + timedelta(days=DAYS_AHEAD)

    matches = []
    for row in rows[1:]:
        if len(row) <= col["Гости"]:
            continue
        if row[col["Статус"]].strip() != "Запланирован":
            continue
        match_date = parse_date(row[col["Дата"]])
        if not match_date or not (today <= match_date <= cutoff):
            continue
        matches.append({
            "date": match_date.strftime("%d.%m.%Y"),
            "home": row[col["Хозяева"]].strip(),
            "away": row[col["Гости"]].strip(),
        })
    return matches


def research_match(client, home, away, date_str):
    """Просит Claude найти свежий контекст по конкретному матчу через веб-поиск."""
    prompt = (
        f"Найди свежие новости (за последние 1-2 недели) о хоккейных клубах КХЛ "
        f"«{home}» и «{away}» перед их матчем {date_str}. Меня интересует конкретно: "
        f"травмы и дисквалификации ключевых игроков, смена тренера или тренерского штаба, "
        f"необычный мотивационный контекст (кризис, конфликт, важность матча для турнирного положения). "
        f"Если по какой-то из этих тем ничего значимого не нашлось — так и скажи, не выдумывай. "
        f"Ответь коротко, 3-5 предложений, по существу, без общих фраз о команде."
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    # собираем весь текстовый вывод (может быть несколько text-блоков вперемешку с поиском)
    text_parts = [block.text for block in response.content if block.type == "text"]
    return " ".join(text_parts).strip()


def write_context(spreadsheet, results):
    """Пишет находки на лист "Контекст и новости", создавая его при необходимости."""
    try:
        ws = spreadsheet.worksheet(CONTEXT_SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=CONTEXT_SHEET_NAME, rows=500, cols=5)
        ws.append_row(["Дата обновления", "Дата матча", "Матч", "Сводка"])

    now_str = datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
    rows_to_add = [
        [now_str, r["date"], f"{r['home']} — {r['away']}", r["summary"]]
        for r in results
    ]
    if rows_to_add:
        ws.append_rows(rows_to_add)


def main():
    spreadsheet = connect_to_spreadsheet()
    matches = get_upcoming_matches(spreadsheet)
    print(f"Найдено предстоящих матчей для разведки: {len(matches)}")

    if not matches:
        print("Матчей в ближайшие дни нет — заканчиваем без записи.")
        return

    client = Anthropic()  # берёт ANTHROPIC_API_KEY из переменной окружения сама
    results = []
    for m in matches:
        print(f"Ищу контекст: {m['home']} — {m['away']} ({m['date']})")
        summary = research_match(client, m["home"], m["away"], m["date"])
        results.append({**m, "summary": summary})
        print(f"  -> {summary[:120]}...")

    write_context(spreadsheet, results)
    print("Готово, записано в лист «Контекст и новости».")


if __name__ == "__main__":
    main()
