"""
Броски и вратари КХЛ с QuantHockey -> Google-таблица «КАПЕР ДЖАРВИС КХЛ».

Зачем отдельный скрипт на GitHub, а не функция в самой таблице: QuantHockey
отвечает кодом 403 на запросы из Google Apps Script (21.09.2026). Таблица
подписывает каждый свой запрос как «Google-Apps-Script», и эту подпись нельзя
убрать. С GitHub запрос уходит обычным образом.

Что делает (раз в день по расписанию или вручную кнопкой на GitHub):
  1. Берёт общую страницу вратарей лиги: процент отражённых, отражено,
     броски в створ, игры. Из неё же — ссылки на страницы клубов.
  2. С каждой страницы клуба берёт броски в створ полевых игроков — их сумма
     и есть броски самой команды.
  3. Пишет в таблицу:
       «Статистика_команд» — броски за игру, броски соперника, доля бросков,
                            % отражённых команды, основной и второй вратарь;
       «Вратари_КХЛ»       — все вратари лиги;
       «Статистика_история» — снимок дня (не чаще одного в день), чтобы потом
                            самопроверка могла честно оценить пользу бросков;
       Data!K «Броски за игру» — настоящими числами вместо фиктивных.

Главное правило: если сайт не ответил или разметка изменилась так, что данные
не разобрать, скрипт НИЧЕГО не пишет в таблицу и завершается с ошибкой —
лучше пустой столбец, чем неверные числа в модели. На GitHub такой запуск
будет отмечен красным, а в журнале будет видно, что пошло не так.

Таблицы на сайте разбираются по НАЗВАНИЯМ столбцов (SOG, SV%, GP...), а не
по порядку, — перестановка колонок на сайте ничего не сломает.
"""
import os
import re
import sys
import json
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

GOALIES_URL = "https://www.quanthockey.com/khl/seasons/khl-goalies-stats.html"
SITE = "https://www.quanthockey.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

SHEET_TEAM_STATS = "Статистика_команд"
SHEET_GOALIES = "Вратари_КХЛ"
SHEET_HISTORY = "Статистика_история"
SHEET_RESULTS = "результаты матчей"
SHEET_DATA = "Data"

MSK = timezone(timedelta(hours=3))

# ключевое слово из адреса страницы клуба -> название команды в таблице
TEAM_KEYS = [
    ("ak-bars", "Ак Барс"), ("lokomotiv", "Локомотив"), ("torpedo", "Торпедо"), ("amur", "Амур"),
    ("severstal", "Северсталь"), ("barys", "Барыс"), ("metallurg", "Металлург"), ("lada", "Лада"),
    ("dynamo-moscow", "Динамо Москва"), ("dinamo-minsk", "Динамо Минск"), ("admiral", "Адмирал"),
    ("cska", "ЦСКА"), ("ska", "СКА"), ("salavat", "Салават Юлаев"), ("spartak", "Спартак"),
    ("avangard", "Авангард"), ("sochi", "Сочи"), ("sibir", "Сибирь"), ("avtomobilist", "Автомобилист"),
    ("neftekhimik", "Нефтехимик"), ("traktor", "Трактор"), ("shanghai", "Шанхайские Драконы"),
]


class StatsError(Exception):
    """Данные получить или разобрать не удалось — в таблицу ничего не пишем."""


# ----------------------------------------------------------------- разбор сайта
def team_from_href(href):
    m = re.search(r"/teams/([a-z0-9-]+?)-players", href or "", re.I)
    if not m:
        return None
    slug = m.group(1).lower()
    for key, name in TEAM_KEYS:
        # ключ должен стоять отдельным словом адреса: 'ska' не должно совпасть с 'cska'
        if re.search(r"(^|-)" + re.escape(key) + r"(-|$)", slug):
            return name
    return None


def parse_number(text):
    """'93,4' / '.934' / '93.4%' / ' 29 ' -> число; прочерк и пусто -> None (а не 0)."""
    if text is None:
        return None
    s = str(text).replace("\xa0", "").replace(" ", "").replace("%", "").replace(",", ".")
    if not re.fullmatch(r"-?\d*\.?\d+", s):
        return None
    return float(s)


def find_table(html, must_have, must_not_have=()):
    """Ищет таблицу, в строке заголовков которой есть все нужные столбцы и нет запрещённых.
    Возвращает (индексы столбцов, строки), где строка — список (текст, ссылка)."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for td in tr.find_all(["th", "td"]):
                a = td.find("a", href=True)
                cells.append((td.get_text(" ", strip=True), a["href"] if a else ""))
            if cells:
                rows.append(cells)
        for h in range(min(3, len(rows))):
            idx = {c[0].strip().upper(): i for i, c in enumerate(rows[h])}
            if all(k in idx for k in must_have) and not any(k in idx for k in must_not_have):
                return idx, rows[h + 1:]
    return None


def fetch(url, session):
    r = session.get(url, headers=HEADERS, timeout=30)
    return r.status_code, r.text


def parse_goalies(html):
    found = find_table(html, ["NAME", "TEAM", "GP", "SV%", "SV", "SOG"])
    if not found:
        raise StatsError("на странице вратарей не нашлась таблица со столбцами Name/Team/GP/SV%/SV/SOG")
    idx, rows = found
    goalies, team_pages, unmapped = [], {}, set()
    for row in rows:
        if len(row) <= max(idx.values()):
            continue
        team_text, team_href = row[idx["TEAM"]]
        team = team_from_href(team_href)
        if not team:
            if team_text:
                unmapped.add(team_text)
            continue
        if team_href and team not in team_pages:
            team_pages[team] = team_href if team_href.startswith("http") else SITE + team_href
        sv, sog, gp = (parse_number(row[idx[k]][0]) for k in ("SV", "SOG", "GP"))
        if sv is None or sog is None or gp is None:
            continue
        gaa = parse_number(row[idx["GAA"]][0]) if "GAA" in idx else None
        goalies.append({"name": row[idx["NAME"]][0], "team": team, "gp": int(gp),
                        "sv": sv, "sog": sog, "pct": sv / sog if sog > 0 else None, "gaa": gaa})
    if len(goalies) < 22:
        raise StatsError(f"разобрано только {len(goalies)} вратарей; не сопоставлены: {', '.join(sorted(unmapped)) or '—'}")
    return goalies, team_pages, unmapped


def parse_team_shots(html):
    """Сумма бросков в створ полевых игроков клуба (таблица с SOG, но без SV%)."""
    found = find_table(html, ["NAME", "SOG"], ["SV%"])
    if not found:
        return None
    idx, rows = found
    vals = [parse_number(r[idx["SOG"]][0]) for r in rows if len(r) > idx["SOG"]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


# ----------------------------------------------------------------- расчёт
def build_rows(goalies, shots_for, games_played, today):
    by_team = {}
    for g in goalies:
        b = by_team.setdefault(g["team"], {"sv": 0.0, "sog": 0.0, "list": []})
        b["sv"] += g["sv"]; b["sog"] += g["sog"]; b["list"].append(g)

    stats, history, warnings = [], [], []
    for team in sorted(by_team):
        b = by_team[team]
        b["list"].sort(key=lambda g: (-g["gp"], -g["sog"]))
        gp = games_played.get(team) or max(g["gp"] for g in b["list"])
        sa = b["sog"] / gp if gp else None
        sf = shots_for[team] / gp if (team in shots_for and gp) else None
        share = sf / (sf + sa) if (sf is not None and sa is not None and sf + sa > 0) else None
        team_pct = b["sv"] / b["sog"] if b["sog"] > 0 else None
        if sf is not None and not (15 <= sf <= 50):
            warnings.append(f"{team}: {sf:.1f} бросков за игру — подозрительно")
        g1 = b["list"][0] if b["list"] else None
        g2 = b["list"][1] if len(b["list"]) > 1 else None
        r = lambda x, d: "" if x is None else round(x, d)
        stats.append([team, gp, r(sf, 1), r(sa, 1), r(share, 3), r(team_pct, 3),
                      g1["name"] if g1 else "", g1["gp"] if g1 else "", r(g1["pct"], 3) if g1 else "",
                      g2["name"] if g2 else "", g2["gp"] if g2 else "", r(g2["pct"], 3) if g2 else ""])
        history.append([today.strftime("%d.%m.%Y"), team, r(sf, 1), r(sa, 1), r(share, 3), r(team_pct, 3)])
    return stats, history, warnings


def collect(session=None, sleep=0.7):
    """Забирает всё с сайта. Бросает StatsError, если данные неполные."""
    session = session or requests.Session()
    code, html = fetch(GOALIES_URL, session)
    if code != 200:
        raise StatsError(f"страница вратарей ответила кодом {code}")
    goalies, team_pages, unmapped = parse_goalies(html)

    shots_for, failed = {}, []
    for team, url in sorted(team_pages.items()):
        try:
            c, h = fetch(url, session)
        except requests.RequestException as e:
            failed.append(f"{team} ({e.__class__.__name__})"); continue
        total = parse_team_shots(h) if c == 200 else None
        if total is None:
            failed.append(f"{team} (код {c})" if c != 200 else f"{team} (таблица не найдена)")
        else:
            shots_for[team] = total
        time.sleep(sleep)  # вежливая пауза между запросами к сайту
    if len(shots_for) < len(team_pages) // 2:
        raise StatsError(f"броски команды получены только для {len(shots_for)} клубов из {len(team_pages)}: {', '.join(failed)}")
    return goalies, shots_for, failed, unmapped


# ----------------------------------------------------------------- таблица
def open_spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(os.environ["SPREADSHEET_ID"])


def get_or_create(ss, title, rows=100, cols=12):
    import gspread
    try:
        return ss.worksheet(title)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=title, rows=rows, cols=cols)


def games_played_from_sheet(ss):
    values = ss.worksheet(SHEET_RESULTS).get_all_values()
    head = values[0]
    cs, ch, ca = head.index("Статус"), head.index("Хозяева"), head.index("Гости")
    games = {}
    for row in values[1:]:
        if len(row) > max(cs, ch, ca) and row[cs].strip() == "Сыгран":
            for t in (row[ch].strip(), row[ca].strip()):
                games[t] = games.get(t, 0) + 1
    return games


def write_all(ss, stats, history, goalies, today):
    pct = {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}

    st = get_or_create(ss, SHEET_TEAM_STATS)
    st.clear()
    st.update(range_name="A1", values=[[
        "Команда", "Игр", "Бросков за игру", "Бросков соперника за игру", "Доля бросков",
        "% отражённых (команда)", "Основной вратарь", "Игр", "% отражённых",
        "Второй вратарь", "Игр", "% отражённых"]] + stats)
    n = len(stats) + 1
    st.format("A1:L1", {"textFormat": {"bold": True}})
    for rng in (f"E2:F{n}", f"I2:I{n}", f"L2:L{n}"):
        st.format(rng, pct)
    st.update(range_name=f"A{n + 2}", values=[[
        f"Источник: QuantHockey. Обновлено {today:%d.%m.%Y %H:%M} (МСК) скриптом на GitHub. "
        "Доля бросков выше 50% — команда бросает больше соперников: это устойчивый признак "
        "реальной силы, даже когда голы пока не идут."]])
    st.freeze(rows=1)

    gs = get_or_create(ss, SHEET_GOALIES, rows=120, cols=7)
    gs.clear()
    goalies_sorted = sorted(goalies, key=lambda g: (g["team"], -g["gp"]))
    gs.update(range_name="A1", values=[["Вратарь", "Команда", "Игр", "% отражённых", "Отражено",
                                        "Бросков в створ", "Коэф. надёжности"]] +
              [[g["name"], g["team"], g["gp"], round(g["pct"], 3) if g["pct"] is not None else "",
                g["sv"], g["sog"], g["gaa"] if g["gaa"] is not None else ""] for g in goalies_sorted])
    gs.format("A1:G1", {"textFormat": {"bold": True}})
    gs.format(f"D2:D{len(goalies) + 1}", pct)
    gs.freeze(rows=1)

    hs = get_or_create(ss, SHEET_HISTORY, rows=2000, cols=6)
    existing = hs.get_all_values()
    if not existing:
        hs.update(range_name="A1", values=[["Дата", "Команда", "Бросков за игру",
                                            "Бросков соперника за игру", "Доля бросков", "% отражённых"]])
        existing = [["Дата"]]
    added = False
    if not (len(existing) > 1 and existing[-1][0] == today.strftime("%d.%m.%Y")):
        hs.append_rows(history, value_input_option="USER_ENTERED")
        added = True

    data = ss.worksheet(SHEET_DATA)
    names = [r[0].strip() if r else "" for r in data.get("A2:A23")]
    by_team = {row[0]: row[2] for row in stats}
    data.update(range_name="K1", values=[["Броски за игру"]])
    data.update(range_name="K2", values=[[by_team.get(n, "")] for n in names])
    return added


def main():
    today = datetime.now(MSK)
    try:
        goalies, shots_for, failed, unmapped = collect()
    except (StatsError, requests.RequestException) as e:
        print(f"ОШИБКА: {e}\nВ таблицу ничего не записано.", file=sys.stderr)
        sys.exit(1)

    ss = open_spreadsheet()
    stats, history, warnings = build_rows(goalies, shots_for, games_played_from_sheet(ss), today)
    added = write_all(ss, stats, history, goalies, today)

    print(f"Вратарей: {len(goalies)}; команд: {len(stats)}; броски самой команды: {len(shots_for)} клубов.")
    print("Снимок в историю: " + ("добавлен" if added else "за сегодня уже был, второй не добавлен"))
    if failed:
        print("Не удалось взять броски клубов: " + ", ".join(failed))
    if unmapped:
        print("Не сопоставлены сокращения: " + ", ".join(sorted(unmapped)))
    for w in warnings:
        print("Проверьте: " + w)


if __name__ == "__main__":
    main()
