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
import time
from datetime import datetime, timedelta, timezone

import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic, APIStatusError

MOSCOW_TZ = timezone(timedelta(hours=3))
DAYS_AHEAD = 1  # только сегодняшние матчи — на 2 дня вперёд почти всё дублировалось назавтра
CONTEXT_SHEET_NAME = "Контекст и новости"
PREDICTIONS_SHEET_NAME = "прогнозы"
RESULTS_SHEET_NAME = "результаты матчей"
DEDUPE_HOURS = 20  # не разведывать один и тот же матч повторно чаще, чем раз в столько часов
CLOSE_MATCH_MIN_CHANCE = 40  # разведываем только матчи, где у аутсайдера от 40% и выше (т.е. не хуже 60/40)

MODEL = "claude-haiku-4-5-20251001"  # дешевле Sonnet, для этой задачи (найти + коротко резюмировать) достаточно


def get_win_chances(spreadsheet):
    """Читает лист "прогнозы" и возвращает словарь "дата|хозяева|гости" -> (шансы хозяев, шансы гостей)."""
    ws = spreadsheet.worksheet(PREDICTIONS_SHEET_NAME)
    rows = ws.get_all_values()
    header = rows[0]
    col = {name: header.index(name) for name in ("Дата", "Хозяева", "Гости", "Шансы Хозяев, %", "Шансы Гостей, %")}

    chances = {}
    for row in rows[1:]:
        if len(row) <= col["Шансы Гостей, %"]:
            continue
        match_date = parse_date(row[col["Дата"]])
        if not match_date:
            continue
        home, away = row[col["Хозяева"]].strip(), row[col["Гости"]].strip()
        try:
            ch = float(row[col["Шансы Хозяев, %"]].replace(",", "."))
            ca = float(row[col["Шансы Гостей, %"]].replace(",", "."))
        except (ValueError, AttributeError):
            continue
        chances[f"{match_date.strftime('%d.%m.%Y')}|{home}|{away}"] = (ch, ca)
    return chances


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


def get_recently_researched(spreadsheet):
    """Возвращает множество ключей "дата|хозяева|гости" для матчей, которые уже
    разведывались за последние DEDUPE_HOURS часов — их пропускаем, чтобы не
    платить дважды за один и тот же (скорее всего, не изменившийся) контекст."""
    try:
        ws = spreadsheet.worksheet(CONTEXT_SHEET_NAME)
    except gspread.WorksheetNotFound:
        return set()

    rows = ws.get_all_values()
    if len(rows) < 2:
        return set()
    header = rows[0]
    col = {name: header.index(name) for name in ("Дата обновления", "Дата матча", "Матч")}

    now = datetime.now(MOSCOW_TZ)
    recent = set()
    for row in rows[1:]:
        if len(row) <= col["Матч"]:
            continue
        try:
            updated_at = datetime.strptime(row[col["Дата обновления"]], "%d.%m.%Y %H:%M").replace(tzinfo=MOSCOW_TZ)
        except ValueError:
            continue
        if (now - updated_at).total_seconds() > DEDUPE_HOURS * 3600:
            continue
        match_str = row[col["Матч"]]
        if " — " not in match_str:
            continue
        home, away = match_str.split(" — ", 1)
        recent.add(f"{row[col['Дата матча']]}|{home}|{away}")
    return recent


def research_match(client, home, away, date_str):
    """Просит Claude найти свежий контекст по конкретному матчу через веб-поиск.
    При превышении лимита обращений к серверным инструментам — ждёт и повторяет
    попытку (до 3 раз), это временное ограничение, а не постоянный запрет."""
    prompt = (
        f"Найди свежие новости (за последние 1-2 недели) о хоккейных клубах КХЛ "
        f"«{home}» и «{away}» перед их матчем {date_str}. Меня интересует конкретно: "
        f"травмы и дисквалификации ключевых игроков, смена тренера или тренерского штаба, "
        f"необычный мотивационный контекст (кризис, конфликт, важность матча для турнирного положения). "
        f"Если по какой-то из этих тем ничего значимого не нашлось — так и скажи, не выдумывай. "
        f"Ответь коротко, 3-5 предложений, по существу, без общих фраз о команде."
    )

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
                messages=[{"role": "user", "content": prompt}],
            )
            text_parts = [block.text for block in response.content if block.type == "text"]
            text = " ".join(text_parts).strip()
            if text:
                return text
            return "(агент не вернул текстовый ответ по этому матчу — возможно, стоит проверить вручную)"
        except APIStatusError as e:
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                wait = 20 * (attempt + 1)
                print(f"  Похоже на превышение лимита запросов, жду {wait} сек. и пробую снова...")
                time.sleep(wait)
                continue
            return f"(ошибка при обращении к Claude: {e})"
    return "(не удалось получить ответ после нескольких попыток — лимит запросов не сбросился вовремя)"


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
    print(f"Найдено предстоящих матчей: {len(matches)}")

    chances = get_win_chances(spreadsheet)
    close_matches = []
    for m in matches:
        key = f"{m['date']}|{m['home']}|{m['away']}"
        ch, ca = chances.get(key, (None, None))
        if ch is None:
            continue  # нет прогноза для этого матча — пропускаем, разведывать нечего сравнивать
        if min(ch, ca) >= CLOSE_MATCH_MIN_CHANCE:
            close_matches.append(m)
    print(f"Из них близких по прогнозу (аутсайдер {CLOSE_MATCH_MIN_CHANCE}%+): {len(close_matches)}")
    matches = close_matches

    recently_done = get_recently_researched(spreadsheet)
    matches = [m for m in matches if f"{m['date']}|{m['home']}|{m['away']}" not in recently_done]
    print(f"После отсечения уже разведанных за последние {DEDUPE_HOURS} ч.: {len(matches)}")

    if not matches:
        print("Новых близких матчей для разведки нет — заканчиваем без записи.")
        return

    client = Anthropic()  # берёт ANTHROPIC_API_KEY из переменной окружения сама
    results = []
    for i, m in enumerate(matches):
        print(f"Ищу контекст: {m['home']} — {m['away']} ({m['date']})")
        summary = research_match(client, m["home"], m["away"], m["date"])
        results.append({**m, "summary": summary})
        print(f"  -> {summary[:120]}...")
        if i < len(matches) - 1:
            time.sleep(8)  # небольшая пауза между матчами, чтобы не упираться в лимит запросов

    write_context(spreadsheet, results)
    print("Готово, записано в лист «Контекст и новости».")


if __name__ == "__main__":
    main()
