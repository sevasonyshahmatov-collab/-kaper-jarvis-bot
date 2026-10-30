# -*- coding: utf-8 -*-
"""Какие прогнозы ушли в канал: строки бота в team/INBOX.md («опубликовано владельцем: ММДД-N», «… (по расписанию)»),
текст ставки и кэф — из team/picks/SENT.md, правки владельца в боте поверх, дополнительно — строки team/PICKS.md
(прогнозы, опубликованные мимо бота). Всё — в один вид:
  {pid, league: 'KHL'|'NHL', home, away, start: datetime МСК, bet, kef: float|None, src: 'inbox'|'sent'|'picks', note}

Правки (строки «правка владельца в боте: ММДД-N — …»):
  • «новый текст поста; Прогноз: …; Кэф: …» и быстрые «прогноз → «…»», «кэф → …» меняют черновик;
  • «вернул прежний текст» — откат на шаг;
  • в канал попадает черновик в момент публикации; правка после публикации меняет канал, только если в строке
    «(и в канале)» (так пишет бот, apps-script/project/Код.js teamEditLog_).
  Правки ««1,64» → «1,66»» и «поправить ММДД-N …: заменить …» текстом не разбираем — номер уходит владельцу в «проверьте».
"""
import os
import re
from datetime import datetime, timedelta

from data import MSK
from settle import canon

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PID = r'\d{4}-\d+'
LEAGUE = {'КХЛ': 'KHL', 'НХЛ': 'NHL'}


def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def _year_for(day, month, ref):
    """Год для «дд.ММ» — ближайший к ref."""
    best = None
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = datetime(y, month, day, tzinfo=MSK)
        except ValueError:
            continue
        if best is None or abs((d - ref).total_seconds()) < abs((best - ref).total_seconds()):
            best = d
    return best.year


def _stamp(s, ref):
    m = re.match(r'(\d\d)\.(\d\d) (\d\d):(\d\d)', s)
    d, mo, hh, mm = (int(x) for x in m.groups())
    return datetime(_year_for(d, mo, ref), mo, d, hh, mm, tzinfo=MSK)


def _kef(s):
    m = re.search(r'(\d+)[,.](\d+)', str(s or ''))
    return round(float(m.group(1) + '.' + m.group(2)), 2) if m else None


def _clean_bet(s):
    s = re.sub(r'\s*\((?:[^)]*(?:владел|повтор|проб|исправ)[^)]*)\)', '', str(s or '')).strip()
    return re.sub(r'\s+', ' ', s)


def parse_sent(text, ref):
    """team/picks/SENT.md → {pid: прогноз}."""
    out = {}
    for line in text.splitlines():
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) < 5 or not re.fullmatch(PID, c[0]):
            continue
        m = re.match(r'(.+?)\s+[—–-]\s+(.+?),\s*(\d\d)\.(\d\d)\s+(\d\d):(\d\d)', c[2])
        if not m:
            continue
        home, away = canon(m.group(1)), canon(m.group(2))
        d, mo, hh, mm = (int(x) for x in m.groups()[2:])
        start = datetime(_year_for(d, mo, ref), mo, d, hh, mm, tzinfo=MSK)
        out[c[0]] = dict(pid=c[0], league=LEAGUE.get(c[1], c[1]), home=home, away=away, start=start, bet=_clean_bet(c[3]),
                         kef=_kef(c[4]), src='sent', note='', raw_bet=c[3])
    return out


def parse_inbox(text, ref):
    """→ (опубликовано {pid: время}, правки [(время, pid, {bet?, kef?, undo?}, в канале?)], непонятное [строки])."""
    pub, edits, unclear = {}, [], []
    for line in text.splitlines():
        m = re.match(r'- \[[ x]\] (\d\d\.\d\d \d\d:\d\d) · (.*)$', line.strip())
        if not m:
            continue
        ts, body = _stamp(m.group(1), ref), m.group(2)
        p = re.match(r'опубликовано владельцем(?: \(по расписанию\))?: (%s)\b' % PID, body)
        if p:
            pub.setdefault(p.group(1), ts)
            continue
        e = re.match(r'правка владельца в боте( \(и в канале\))?: (%s) — (.*)$' % PID, body)
        if e:
            ch, pid, what = bool(e.group(1)), e.group(2), e.group(3)
            ch_ = {}
            if 'вернул прежний текст' in what:
                ch_['undo'] = True
            mb = re.search(r'Прогноз:\s*([^;]+)', what) or re.search(r'прогноз → «([^»]+)»', what)
            mk = re.search(r'Кэф:\s*([^;]+)', what) or re.search(r'кэф → (\S+)', what)
            if mb:
                ch_['bet'] = _clean_bet(mb.group(1))
            if mk and _kef(mk.group(1)):
                ch_['kef'] = _kef(mk.group(1))
            if ch_:
                edits.append((ts, pid, ch_, ch))
            elif not re.search(r'текст прогноза|концовка|шапка|хэштеги|убран', what):
                unclear.append('%s: %s' % (pid, what))
            continue
        f = re.match(r'поправить (%s) .*?: (.*)$' % PID, body)
        if f and re.search(r'прогноз|кэф|тотал|фора|победа', f.group(2), re.I):
            unclear.append('%s: «%s» (просьба текстом — проверьте, что ушло в канал)' % (f.group(1), f.group(2)[:80]))
    return pub, edits, unclear


def channel_version(row, pub_ts, edits):
    """Ставка и кэф, которые на самом деле в канале (см. описание модуля)."""
    draft = [dict(bet=row['bet'], kef=row['kef'])]
    chan = None
    for ts, pid, ch, in_ch in sorted((e for e in edits if e[1] == row['pid']), key=lambda e: e[0]):
        if chan is None and ts > pub_ts:
            chan = [dict(draft[-1])]
        if ch.get('undo'):
            if len(draft) > 1:
                draft.pop()
            if chan is not None and in_ch and len(chan) > 1:
                chan.pop()
            continue
        new = dict(draft[-1], **{k: v for k, v in ch.items() if k in ('bet', 'kef')})
        draft.append(new)
        if chan is not None and in_ch:
            chan.append(dict(chan[-1], **{k: v for k, v in ch.items() if k in ('bet', 'kef')}))
    v = (chan or draft)[-1]
    changed = v['bet'] != row['bet'] or v['kef'] != row['kef']
    return v['bet'], v['kef'], changed


def parse_picks_md(text, ref):
    """team/PICKS.md → прогнозы без номера (дата — дата матча; время неизвестно)."""
    out = []
    for line in text.splitlines():
        m = re.match(r'- (\d{4})-(\d\d)-(\d\d) \| (КХЛ|НХЛ) \| (.+?) [—–-] (.+?) \| (.+?) \| (.+?)(?: \| (.*))?$', line.strip())
        if not m:
            continue
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        lg = LEAGUE[m.group(4)]
        start = datetime(y, mo, d, 17 if lg == 'KHL' else 3, 0, tzinfo=MSK)
        out.append(dict(pid='', league=lg, home=canon(m.group(5)), away=canon(m.group(6)), start=start, bet=_clean_bet(m.group(7)),
                        kef=_kef(m.group(8)), src='picks', note=m.group(9) or '', exact_time=False))
    return out


class Ledger:
    def __init__(self, ref, root=ROOT, inbox=None, sent=None, picks=None):
        """ref — дата/время утра (МСК): по нему угадываем год в «дд.ММ». Тексты можно передать прямо (проверки)."""
        self.ref = ref
        sent = _read(os.path.join(root, 'team', 'picks', 'SENT.md')) if sent is None else sent
        inbox = _read(os.path.join(root, 'team', 'INBOX.md')) if inbox is None else inbox
        picks = _read(os.path.join(root, 'team', 'PICKS.md')) if picks is None else picks
        self.inbox_text = inbox                                # для выбора владельца в утреннем опросе (ask.selection)
        self.sent = parse_sent(sent, ref)
        self.pub, self.edits, self.unclear = parse_inbox(inbox, ref)
        self.picks_md = parse_picks_md(picks, ref)

    def published(self, t0, t1, note_from=None):
        """Опубликованные прогнозы на матчи с началом в [t0, t1): один на матч — последний опубликованный.
        → (прогнозы, заметки владельцу — только о матчах с началом от note_from)."""
        notes, by_match = [], {}
        note_from = note_from or t0
        for pid, ts in sorted(self.pub.items(), key=lambda x: x[1]):
            row = self.sent.get(pid)
            if not row:
                if t0 - timedelta(days=2) <= ts < t1:
                    notes.append('%s опубликован, но его нет в SENT.md — в итоги не вошёл' % pid)
                continue
            if row['league'] not in ('KHL', 'NHL'):              # футбол — свой учёт (лист «Футбол», docs/handoff/FOOTBALL_BOT.md)
                continue
            if not (t0 <= row['start'] < t1):
                continue
            bet, kef, changed = channel_version(row, ts, self.edits)
            p = dict(row, bet=bet, kef=kef, src='inbox', published=ts, edited=changed)
            key = (p['league'], p['home'], p['away'], p['start'].date())
            if key in by_match and p['start'] >= note_from:
                notes.append('%s — %s опубликован дважды (%s и %s): в итогах последний вариант, %s'
                             % (p['home'], p['away'], by_match[key]['pid'], pid, pid))
            by_match[key] = p
        for p in self.picks_md:                                # прогнозы мимо бота
            if not (t0 - timedelta(hours=14) <= p['start'] < t1 + timedelta(hours=10)):
                continue
            if any((x['league'], x['home'], x['away']) == (p['league'], p['home'], p['away']) for x in by_match.values()):
                continue
            if re.search(r'уточн|не подводить', p['note']):
                if p['start'] >= note_from:
                    notes.append('PICKS.md: %s — %s «%s» — помечен «уточнить», в итоги не беру' % (p['home'], p['away'], p['bet']))
                continue
            by_match[(p['league'], p['home'], p['away'], p['start'].date())] = dict(p)
        for u in self.unclear:
            pid = u.split(':')[0]
            if any(x.get('pid') == pid and x['start'] >= note_from for x in by_match.values()):
                notes.append('правка %s — проверьте вручную' % u)
        return sorted(by_match.values(), key=lambda p: p['start']), notes

    def chosen(self, pids):
        """Прогнозы по номерам, которые владелец отметил в утреннем опросе: ставка и кэф — как в канале, если опубликован
        через бота, иначе последний вариант черновика (правки владельца в боте). → (прогнозы, заметки)."""
        out, notes = [], []
        far = datetime(2100, 1, 1, tzinfo=MSK)
        for pid in pids:
            row = self.sent.get(pid)
            if not row:
                notes.append('%s нет в SENT.md — в итоги не вошёл' % pid)
                continue
            ts = self.pub.get(pid)
            bet, kef, changed = channel_version(row, ts or far, self.edits)
            out.append(dict(row, bet=bet, kef=kef, src='ask', published=ts, edited=changed))
        return out, notes

    def sent_only(self, t0, t1):
        """Запасной вариант: отправленные владельцу (не опубликованные) на матчи в [t0, t1), один на матч — последний номер."""
        by_match = {}
        for pid, row in sorted(self.sent.items(), key=lambda x: (x[1]['start'], int(x[0].split('-')[1]))):
            if t0 <= row['start'] < t1:
                by_match[(row['league'], row['home'], row['away'], row['start'].date())] = dict(row, src='sent')
        return sorted(by_match.values(), key=lambda p: p['start'])
