# -*- coding: utf-8 -*-
"""Движок разнообразия утренних постов: какая подача (макет) и какие фразы из банков team/daily/texts.py в какой день.

Память — без файла. Выбор на день D — детерминированная функция даты: движок «проигрывает» календарь с EPOCH до D
и в каждый день по каждому банку берёт фразу, которой не было последние `window` дней (из подходящих — случайно,
но генератор засеян именем банка и датой). Поэтому:
  • выбор любого прошедшего дня пересчитывается заново где угодно (в Actions, в сессии, в проверке) — коммитить
    историю не нужно, а у itogi.yml и нет права писать в репозиторий (permissions: contents: read);
  • повторный запуск того же дня даёт те же тексты; пропущенный день ничего не ломает;
  • гарантия «фраза не повторяется N дней» держится, пока банк не меняли; после правки банка возможен один повтор
    на стыке (фразы опознаются по тексту, поэтому дописанные фразы не сдвигают остальные).

Банк: имя → Bank(items, per_day=1, window=7, when=None). when(day, layouts) → False — банк в этот день не крутим
(например, вопросы «Q&A» — только в дни, когда выпал макет qa; «понедельник» — по понедельникам). Банки, нужные
только при каких-то данных (плохой день, дерби), крутим каждый день: их выбор от данных не зависит, иначе прошлое
не пересчитать.
"""
import random
from datetime import date, timedelta

EPOCH = date(2026, 10, 1)


class Bank:
    def __init__(self, items, per_day=1, window=7, when=None, exclude_same_day=None):
        self.items = list(dict.fromkeys(items))           # без дублей, порядок сохраняем
        self.per_day, self.window, self.when = per_day, window, when
        self.exclude_same_day = exclude_same_day          # имя банка, чей выбор в тот же день исключить (макет итогов ≠ макет утра)
        assert len(self.items) >= per_day, 'в банке меньше фраз, чем нужно в день'


class Plan:
    """Выбор на один день: plan.one('m.hello'), plan.many('addr'), plan.layout('m')."""

    def __init__(self, day, picks):
        self.day, self.picks = day, picks

    def many(self, bank):
        return list(self.picks.get(bank) or [])

    def one(self, bank, i=0):
        v = self.picks.get(bank) or []
        if not v:
            raise KeyError('банк %s в этот день не крутился (when)' % bank)
        return v[i % len(v)]

    def layout(self, kind):
        return self.one('%s.layout' % kind)


class Engine:
    def __init__(self, banks, epoch=EPOCH):
        self.banks, self.epoch = banks, epoch
        self._last = {}            # банк → {фраза: последний день}
        self._days = {}            # день → Plan
        self._upto = None
        # макеты — первыми: от них зависят when у банков вопросов и т. п.
        self.order = sorted(banks, key=lambda n: (not n.endswith('.layout'), n))

    def _choose(self, name, bank, day, layouts, taken, variant):
        last = self._last.setdefault(name, {})
        excl = set(taken.get(bank.exclude_same_day) or []) if bank.exclude_same_day else set()
        fresh = [x for x in bank.items if x not in excl and (x not in last or (day - last[x]).days >= bank.window)]
        rng = random.Random('%s|%s|%s' % (name, day.isoformat(), variant))
        if len(fresh) >= bank.per_day:
            got = rng.sample(fresh, bank.per_day)
        else:                                              # банк мал — добираем давно не использованными
            rest = sorted((x for x in bank.items if x not in fresh and x not in excl), key=lambda x: (last.get(x, date.min), rng.random()))
            got = fresh + rest[:bank.per_day - len(fresh)]
        for x in got:
            last[x] = day
        return got

    def plan(self, day, variant=0):
        """Выбор на day. variant > 0 — другой вариант этого дня (прошлое не меняет; завтрашний пересчёт про него не знает)."""
        if day < self.epoch:
            raise ValueError('день раньше EPOCH %s' % self.epoch)
        if self._upto is None or self._upto < day - timedelta(days=1):
            d = self.epoch if self._upto is None else self._upto + timedelta(days=1)
            while d < day:
                self._days[d] = self._play(d, 0)
                self._upto = d
                d += timedelta(days=1)
        if day in self._days and variant == 0:
            return self._days[day]
        if variant:
            saved = {k: dict(v) for k, v in self._last.items()}
            p = self._play(day, variant)
            self._last = saved
            return p
        p = self._play(day, 0)
        self._days[day], self._upto = p, max(self._upto or day, day)
        return p

    def _play(self, day, variant):
        taken, layouts = {}, {}
        for name in self.order:
            b = self.banks[name]
            if b.when and not b.when(day, layouts):
                continue
            taken[name] = self._choose(name, b, day, layouts, taken, variant)
            if name.endswith('.layout'):
                layouts[name.split('.')[0]] = taken[name][0]
        return Plan(day, taken)
