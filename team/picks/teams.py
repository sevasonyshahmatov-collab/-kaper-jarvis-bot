# -*- coding: utf-8 -*-
"""Названия команд для ежедневных прогнозов: КХЛ (id приложения КХЛ, слова у Pinnacle) и НХЛ (аббревиатура → русское
название как в таблице НХЛ, английское, слова у Pinnacle)."""
import re

KHL_IDS = {8: 'Динамо Москва', 10: 'Авангард', 12: 'Амур', 16: 'ЦСКА', 18: 'Спартак', 22: 'Торпедо', 24: 'Сибирь', 26: 'Локомотив',
           28: 'Трактор', 30: 'Металлург', 32: 'Салават Юлаев', 36: 'Нефтехимик', 38: 'Динамо Минск', 40: 'Ак Барс', 42: 'Северсталь',
           44: 'СКА', 46: 'Барыс', 56: 'Автомобилист', 61: 'Адмирал', 105: 'Лада', 113: 'Сочи', 315: 'Шанхайские Драконы'}

KHL_PIN = {'Динамо Москва': r'(dynamo|dinamo) mosc', 'Динамо Минск': r'minsk', 'ЦСКА': r'\bcska\b', 'СКА': r'\bska\b',
           'Спартак': r'spartak', 'Торпедо': r'torpedo', 'Сибирь': r'sibir', 'Локомотив': r'lokomotiv', 'Трактор': r'traktor|tractor',
           'Металлург': r'metallurg', 'Салават Юлаев': r'salavat', 'Нефтехимик': r'neftekhimik', 'Ак Барс': r'ak bars',
           'Северсталь': r'severstal', 'Барыс': r'barys', 'Автомобилист': r'avtomobilist', 'Адмирал': r'admiral',
           'Лада': r'\blada\b', 'Сочи': r'sochi', 'Шанхайские Драконы': r'shanghai|kunlun', 'Авангард': r'avangard',
           'Амур': r'\bamur\b'}

NHL = {  # аббревиатура: (как в таблице НХЛ, английское, слова у Pinnacle)
    'ANA': ('Анахайм', 'Anaheim Ducks', r'ducks'), 'BOS': ('Бостон', 'Boston Bruins', r'bruins'),
    'BUF': ('Баффало', 'Buffalo Sabres', r'sabres'), 'CGY': ('Калгари', 'Calgary Flames', r'flames'),
    'CAR': ('Каролина', 'Carolina Hurricanes', r'hurricanes'), 'CHI': ('Чикаго', 'Chicago Blackhawks', r'blackhawks'),
    'COL': ('Колорадо', 'Colorado Avalanche', r'avalanche'), 'CBJ': ('Коламбус', 'Columbus Blue Jackets', r'blue jackets'),
    'DAL': ('Даллас', 'Dallas Stars', r'\bstars\b'), 'DET': ('Детройт', 'Detroit Red Wings', r'red wings'),
    'EDM': ('Эдмонтон', 'Edmonton Oilers', r'oilers'), 'FLA': ('Флорида', 'Florida Panthers', r'panthers'),
    'LAK': ('Лос-Анджелес', 'Los Angeles Kings', r'\bkings\b'), 'MIN': ('Миннесота', 'Minnesota Wild', r'\bwild\b'),
    'MTL': ('Монреаль', 'Montreal Canadiens', r'canadiens'), 'NSH': ('Нэшвилл', 'Nashville Predators', r'predators'),
    'NJD': ('Нью-Джерси', 'New Jersey Devils', r'devils'), 'NYI': ('Айлендерс', 'New York Islanders', r'islanders'),
    'NYR': ('Рейнджерс', 'New York Rangers', r'rangers'), 'OTT': ('Оттава', 'Ottawa Senators', r'senators'),
    'PHI': ('Филадельфия', 'Philadelphia Flyers', r'flyers'), 'PIT': ('Питтсбург', 'Pittsburgh Penguins', r'penguins'),
    'SJS': ('Сан-Хосе', 'San Jose Sharks', r'sharks'), 'SEA': ('Сиэтл', 'Seattle Kraken', r'kraken'),
    'STL': ('Сент-Луис', 'St. Louis Blues', r'\bblues\b'), 'TBL': ('Тампа-Бэй', 'Tampa Bay Lightning', r'lightning'),
    'TOR': ('Торонто', 'Toronto Maple Leafs', r'maple leafs'), 'UTA': ('Юта', 'Utah Mammoth', r'mammoth|\butah\b'),
    'VAN': ('Ванкувер', 'Vancouver Canucks', r'canucks'), 'VGK': ('Вегас', 'Vegas Golden Knights', r'golden knights'),
    'WSH': ('Вашингтон', 'Washington Capitals', r'capitals'), 'WPG': ('Виннипег', 'Winnipeg Jets', r'\bjets\b'),
}
NHL_RU = {ab: v[0] for ab, v in NHL.items()}
NHL_PIN = {v[0]: v[2] for v in NHL.values()}


def pin_team(name, league):
    """Название у Pinnacle → русское (как в наших данных) или None."""
    s = str(name or '').lower()
    for ru, rx in (KHL_PIN if league == 'khl' else NHL_PIN).items():
        if re.search(rx, s):
            return ru
    return None


# Фонбет (линия по-русски, 31.10): «Металлург Мг», «Динамо Мн», «Детройт», «Нью-Йорк Рейнджерс»… → наши названия.
KHL_FON = {'ЦСКА': r'\bцска\b', 'СКА': r'(?<!ц)\bска\b', 'Спартак': r'спартак', 'Торпедо': r'торпедо', 'Сибирь': r'сибирь',
           'Локомотив': r'локомотив', 'Трактор': r'трактор', 'Металлург': r'металлург', 'Салават Юлаев': r'салават',
           'Нефтехимик': r'нефтехимик', 'Ак Барс': r'ак барс', 'Северсталь': r'северсталь', 'Барыс': r'барыс',
           'Автомобилист': r'автомобилист', 'Адмирал': r'адмирал', 'Лада': r'\bлада\b', 'Сочи': r'сочи',
           'Шанхайские Драконы': r'шанха|драко|дрэгон|куньлун', 'Авангард': r'авангард', 'Амур': r'\bамур\b'}
NHL_FON = {ru: (r'айлендерс' if ru == 'Айлендерс' else r'рейнджерс' if ru == 'Рейнджерс' else r'тампа' if ru == 'Тампа-Бэй'
                else r'^' + re.escape(ru.lower().replace('ё', 'е')).replace(r'\-', r'[\- ]'))
           for ru in NHL_PIN}


def fon_team(name, league):
    """Название у Фонбета → русское (как в наших данных) или None."""
    s = re.sub(r'\s+', ' ', str(name or '').lower().replace('ё', 'е')).strip()
    if league == 'khl':
        if 'динамо' in s:
            return 'Динамо Минск' if re.search(r'\bмн\b|минск', s) else 'Динамо Москва'
        for ru, rx in KHL_FON.items():
            if re.search(rx, s):
                return ru
        return None
    for ru, rx in NHL_FON.items():
        if re.search(rx, s):
            return ru
    return None
