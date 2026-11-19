# -*- coding: utf-8 -*-
"""Страница хоккейного матча — четыре блока «перед матчем» (владелец 19.11: «сделать что-то полезное для пользователей»).
Вызывается из seo/build_match.py (match_page, вид 2). Только реальные данные сайта, ничего не выдумываем:
  1. «Отдых и дорога»  — дни отдыха, второй матч за два дня, серия выездов/домашних, перелёт и разница во времени
                          (assets/data/teams.json: матчи клуба; города клубов — таблица CITY ниже, расстояние — по прямой).
  2. «Кто в форме»     — лучшие игроки клубов по очкам за 5 последних матчей команды (hockey/data/<лига>_players.json, лог по матчам).
  3. «Дома и в гостях» — хозяева дома, гости на выезде: победы, шайбы за игру, тотал больше 5,5, овертаймы (матчи регулярки сезона).
  4. «Вратари»         — цифры вратарей клубов за сезон (teams.json pl.gk). Кто выйдет в старте, заранее не объявляют.
Каждый блок пропадает, если данных для него нет."""
import html as H
import json
import math
import os

esc = lambda s: H.escape(str(s), quote=True)  # noqa: E731
HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.dirname(HERE)

# город клуба: (часовой пояс UTC зимой, широта, долгота). Шанхай не ставим: где «Драконы» играют дома в этом сезоне — не проверено.
CITY = {
    'dinamo_msk': (3, 55.79, 37.56), 'cska': (3, 55.80, 37.52), 'spartak': (3, 55.82, 37.44), 'lokomotiv': (3, 57.63, 39.87),
    'torpedo': (3, 56.33, 44.00), 'ska': (3, 59.94, 30.31), 'severstal': (3, 59.13, 37.90), 'lada': (4, 53.51, 49.42),
    'sochi': (3, 43.40, 39.96), 'dinamo_minsk': (3, 53.90, 27.56), 'akbars': (3, 55.79, 49.12), 'neftekhimik': (3, 55.64, 51.82),
    'salavat': (5, 54.74, 55.97), 'traktor': (5, 55.16, 61.40), 'metallurg': (5, 53.41, 58.98), 'avtomobilist': (5, 56.84, 60.61),
    'avangard': (6, 54.99, 73.37), 'sibir': (7, 55.03, 82.92), 'barys': (5, 51.17, 71.45), 'amur': (10, 48.48, 135.08),
    'admiral': (10, 43.12, 131.89),
    'nhl_bos': (-5, 42.37, -71.06), 'nhl_buf': (-5, 42.88, -78.88), 'nhl_det': (-5, 42.33, -83.05), 'nhl_fla': (-5, 26.16, -80.33),
    'nhl_mtl': (-5, 45.50, -73.57), 'nhl_ott': (-5, 45.30, -75.93), 'nhl_tbl': (-5, 27.94, -82.45), 'nhl_tor': (-5, 43.64, -79.38),
    'nhl_car': (-5, 35.80, -78.72), 'nhl_cbj': (-5, 39.97, -83.01), 'nhl_njd': (-5, 40.73, -74.17), 'nhl_nyi': (-5, 40.71, -73.73),
    'nhl_nyr': (-5, 40.75, -73.99), 'nhl_phi': (-5, 39.90, -75.17), 'nhl_pit': (-5, 40.44, -79.99), 'nhl_wsh': (-5, 38.90, -77.02),
    'nhl_chi': (-6, 41.88, -87.67), 'nhl_col': (-7, 39.75, -105.00), 'dallas': (-6, 32.79, -96.81), 'minnesota': (-6, 44.94, -93.10),
    'nhl_nsh': (-6, 36.16, -86.78), 'nhl_stl': (-6, 38.63, -90.20), 'nhl_uta': (-7, 40.77, -111.90), 'nhl_wpg': (-6, 49.89, -97.14),
    'nhl_ana': (-8, 33.81, -117.88), 'nhl_cgy': (-7, 51.04, -114.05), 'nhl_edm': (-7, 53.55, -113.50), 'nhl_lak': (-8, 34.04, -118.27),
    'nhl_sjs': (-8, 37.33, -121.90), 'nhl_sea': (-8, 47.62, -122.35), 'nhl_van': (-8, 49.28, -123.11), 'nhl_vgk': (-8, 36.10, -115.18),
}
NHL_AB = {'dallas': 'DAL', 'minnesota': 'MIN'}


def plural(n, a, b, c):
    n = abs(int(n)); k, j = n % 100, n % 10
    return c if 10 < k < 20 else a if j == 1 else b if 1 < j < 5 else c


def mins(t):
    """'ГГГГ-ММ-ДД ЧЧ:ММ' (МСК) → минуты от эпохи (для разницы между матчами)."""
    import datetime
    try:
        return datetime.datetime.strptime(t[:16], '%Y-%m-%d %H:%M').timestamp() / 60
    except ValueError:
        return None


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[2], b[1], b[2]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


class Extra:
    def __init__(self, B, crest):
        self.B, self.crest = B, crest
        self.T = B.TEAMS['teams']
        self.start = {}
        try:
            with open(os.path.join(V3A, 'team', 'season.json'), encoding='utf-8') as f:
                se = json.load(f)
            for lg in ('khl', 'nhl'):
                ds = [g['d'] for t in (se.get(lg) or {}).values() for g in t.get('games', []) if g.get('d')]
                if ds:
                    self.start[lg] = min(ds)[:10]
        except Exception:  # noqa: BLE001
            pass
        self.P = {}
        for lg in ('khl', 'nhl'):
            try:
                with open(os.path.join(V3A, 'hockey', 'data', '%s_players.json' % lg), encoding='utf-8') as f:
                    self.P[lg] = json.load(f).get('players') or []
            except Exception:  # noqa: BLE001
                self.P[lg] = []

    # ── данные ──
    def games(self, tid, lg, before, played_only=True):
        """Матчи клуба этого сезона (без предсезонки) до начала матча, по времени."""
        t = self.T.get(tid) or {}
        s0 = self.start.get(lg, '0000')
        out = [g for g in t.get('games', []) if g.get('d', '') >= s0 and g['d'] < before and (not played_only or 'gf' in g)]
        out.sort(key=lambda g: g['d'])
        return out

    def nm(self, tid):
        return (self.T.get(tid) or {}).get('name') or tid

    def head(self, m, tid, from_dir, px=30):
        return '%s<span>%s</span>' % (self.crest(m, tid, from_dir, px), esc(self.nm(tid)))

    # ── 1. Отдых и дорога ──
    def rest(self, m, side):
        tid = m[side]; lg = m['lg']
        host = m['h']
        gs = self.games(tid, lg, m['t'][:16], played_only=False)
        if not gs:
            return None
        prev = gs[-1]
        t0, t1 = mins(prev['d']), mins(m['t'])
        if t0 is None or t1 is None:
            return None
        gap_h = (t1 - t0) / 60
        r = {'tid': tid, 'b2b': gap_h < 30, 'rest': max(0, int(round(gap_h / 24)) - 1), 'prev': prev,
             'wk': 1 + sum(1 for g in gs if t1 - (mins(g['d']) or 0) < 7 * 24 * 60)}
        home_now = side == 'h'
        n = 1
        for g in reversed(gs):
            if (g.get('h') == 1) == home_now:
                n += 1
            else:
                break
        r['streak'] = n
        r['home'] = home_now
        prev_host = tid if prev.get('h') == 1 else prev.get('o')
        a, b = CITY.get(prev_host), CITY.get(host)
        r['same'] = prev_host == host
        if a and b and prev_host != host:
            r['km'] = int(round(km(a, b) / 50.0) * 50)
            r['tz'] = b[0] - a[0]
        return r

    def rest_block(self, m, from_dir):
        rs = [self.rest(m, s) for s in ('h', 'a')]
        if not all(rs):
            return ''
        cards, said = [], []
        for r in rs:
            tid = r['tid']
            p = r['prev']
            hn, an = (self.nm(tid), self.nm(p['o'])) if p.get('h') == 1 else (self.nm(p['o']), self.nm(tid))
            sc = ''
            if 'gf' in p:
                hs, as_ = (p['gf'], p['ga']) if p.get('h') == 1 else (p['ga'], p['gf'])
                sc = ' %d:%d%s' % (hs, as_, (' ' + p['x']) if p.get('x') else '')
            tiles = []
            if r['b2b']:
                tiles.append(('warn', '2-й', 'матч за два дня', 'Вчера тоже играли — без дня отдыха'))
                said.append('%s играет второй день подряд' % self.nm(tid))
            else:
                d = r['rest']
                tiles.append(('', str(d), plural(d, 'день отдыха', 'дня отдыха', 'дней отдыха'), ''))
                said.append('у %s %d %s отдыха' % ('хозяев' if r['home'] else 'гостей', d, plural(d, 'день', 'дня', 'дней')))
            tiles.append(('warn' if r['wk'] >= 4 else '', str(r['wk']), plural(r['wk'], 'матч', 'матча', 'матчей') + ' за 7 дней', 'включая этот'))
            st = r['streak']
            if r['home']:
                tiles.append(('', '%d-й' % st, 'домашний матч подряд', ''))
            else:
                tiles.append(('warn' if st >= 4 else '', '%d-й' % st, 'выездной матч подряд', ''))
            if r.get('km'):
                tz = r['tz']
                tzs = 'без смены часового пояса' if tz == 0 else 'разница во времени %s%d ч' % ('+' if tz > 0 else '−', abs(tz))
                tiles.append(('warn' if r['km'] >= 2500 or abs(tz) >= 3 else '', '{:,}'.format(r['km']).replace(',', ' '), 'км перелёт', tzs))
            elif r.get('same'):
                tiles.append(('', '0', 'км перелёт', 'прошлый матч — на этой же арене'))
            ti = ''.join('<li class="%s"><b class="num">%s</b><span>%s</span>%s</li>'
                         % (c, esc(v), esc(lbl), ('<small>%s</small>' % esc(sub)) if sub else '') for c, v, lbl, sub in tiles)
            cards.append('<div class="mq-card"><h3>%s<em>%s</em></h3><ul class="mq-tiles">%s</ul>'
                         '<p class="mq-prev">Прошлый матч: %s.%s, %s — %s%s</p></div>'
                         % (self.head(m, tid, from_dir), 'хозяева' if r['home'] else 'гости', ti,
                            esc(p['d'][8:10]), esc(p['d'][5:7]), esc(hn), esc(an), esc(sc)))
        if not rs[0]['b2b'] and not rs[1]['b2b'] and rs[0]['rest'] == rs[1]['rest']:
            d = rs[0]['rest']
            lead = 'У обеих команд по %d %s отдыха.' % (d, plural(d, 'дню', 'дня', 'дней')) if d else 'Обе команды отдыхали меньше суток.'
        else:
            lead = said[0][0].upper() + said[0][1:] + ', ' + said[1] + '.'
        return ('<section class="fc-sec mq" aria-labelledby="mq-rest"><div class="wrap"><h2 id="mq-rest">Отдых и дорога</h2>'
                '<p class="mq-lead">%s</p><div class="mq-two">%s</div>'
                '<p class="mq-note">Перелёт — по прямой между городами прошлого и этого матча. Время отдыха считаем от начала прошлого матча.</p>'
                '</div></section>\n' % (esc(lead), ''.join(cards)))

    # ── 2. Кто в форме ──
    def hot(self, m, tid):
        lg = m['lg']
        last = self.games(tid, lg, m['t'][:16])[-5:]
        if len(last) < 3:
            return None, 0
        days = {g['d'][:10] for g in last}
        ab = NHL_AB.get(tid, tid[4:].upper() if tid.startswith('nhl_') else tid)
        rows = []
        for p in self.P.get(lg, []):
            g = a = gp = 0
            for r in p.get('log') or []:
                if r[1] != ab or r[0][:10] not in days:
                    continue
                gp += 1; g += r[4] or 0; a += r[5] or 0
            if g + a > 0:
                rows.append({'id': p.get('id'), 'n': p.get('n', ''), 'g': g, 'a': a, 'pts': g + a})
        rows.sort(key=lambda x: (-x['pts'], -x['g'], x['n']))
        return rows[:5], len(last)

    def hot_block(self, m, from_dir):
        pre = '../' * self.B.depth(from_dir)
        cols = []
        for side in ('h', 'a'):
            tid = m[side]
            rows, n = self.hot(m, tid)
            if not rows:
                continue
            tr = ''.join('<tr><td><a href="%shockey/player.html?lg=%s&amp;id=%s">%s</a></td><td>%d</td><td>%d</td><td class="pt">%d</td></tr>'
                         % (pre, m['lg'], esc(r['id']), esc(r['n']), r['g'], r['a'], r['pts']) for r in rows)
            cols.append('<div class="mq-card"><h3>%s<em>за %d %s</em></h3><table class="mq-t"><thead><tr><th>Игрок</th>'
                        '<th title="Голы">Г</th><th title="Передачи">П</th><th title="Очки: голы + передачи">О</th></tr></thead><tbody>%s</tbody></table></div>'
                        % (self.head(m, tid, from_dir), n, plural(n, 'последний матч', 'последних матча', 'последних матчей'), tr))
        if not cols:
            return ''
        return ('<section class="fc-sec mq" aria-labelledby="mq-hot"><div class="wrap"><h2 id="mq-hot">Кто в форме</h2>'
                '<p class="mq-lead">Больше всего очков (голы + передачи) в последних матчах команды.</p><div class="mq-two">%s</div></div></section>\n'
                % ''.join(cols))

    # ── 3. Дома и в гостях ──
    def split(self, m, tid, home):
        gs = [g for g in self.games(tid, m['lg'], m['t'][:16]) if (g.get('h') == 1) == home]
        n = len(gs)
        if n < 3:
            return None
        w = sum(1 for g in gs if g['gf'] > g['ga'])
        return {'n': n, 'w': w, 'l': n - w, 'gf': sum(g['gf'] for g in gs) / n, 'ga': sum(g['ga'] for g in gs) / n,
                'o55': sum(1 for g in gs if g['gf'] + g['ga'] > 5), 'ot': sum(1 for g in gs if g.get('x'))}

    def homeaway_block(self, m, from_dir):
        h, a = self.split(m, m['h'], True), self.split(m, m['a'], False)
        if not h or not a:
            return ''
        pc = lambda k, v: '%d<small>%%</small>' % round(v[k] / v['n'] * 100)  # noqa: E731
        f = lambda x: ('%.1f' % x).replace('.', ',')  # noqa: E731
        rows = [('Матчей', str(h['n']), str(a['n']), None),
                ('Побед', '%d<small> из %d</small>' % (h['w'], h['n']), '%d<small> из %d</small>' % (a['w'], a['n']), (h['w'] / h['n'], a['w'] / a['n'], 1)),
                ('Забивают за игру', f(h['gf']), f(a['gf']), (h['gf'], a['gf'], 1)),
                ('Пропускают за игру', f(h['ga']), f(a['ga']), (h['ga'], a['ga'], -1)),
                ('Тотал больше 5,5', pc('o55', h), pc('o55', a), None),
                ('Доходили до овертайма', pc('ot', h), pc('ot', a), None)]
        tr = []
        for lbl, x, y, cmp in rows:
            bx = by = ''
            if cmp and abs(cmp[0] - cmp[1]) > 1e-9:
                better_h = (cmp[0] > cmp[1]) == (cmp[2] > 0)
                bx, by = (' class="b"', '') if better_h else ('', ' class="b"')
            tr.append('<tr><th scope="row">%s</th><td%s>%s</td><td%s>%s</td></tr>' % (esc(lbl), bx, x, by, y))
        return ('<section class="fc-sec mq" aria-labelledby="mq-ha"><div class="wrap"><h2 id="mq-ha">Дома и в гостях</h2>'
                '<p class="mq-lead">Хозяева — в своих домашних матчах, гости — в выездных. Регулярный чемпионат этого сезона.</p>'
                '<div class="tabscroll"><table class="mq-ha"><thead><tr><th></th><th scope="col"><span class="mq-th">%s<small>дома</small></span></th>'
                '<th scope="col"><span class="mq-th">%s<small>в гостях</small></span></th></tr></thead><tbody>%s</tbody></table></div>'
                '<p class="mq-note">Жирным — лучшее из двух. Овертайм — с буллитами.</p></div></section>\n'
                % (self.head(m, m['h'], from_dir, 26), self.head(m, m['a'], from_dir, 26), ''.join(tr)))

    # ── 4. Вратари ──
    def goalies_block(self, m, from_dir):
        cols = []
        for side in ('h', 'a'):
            tid = m[side]
            gk = [g for g in ((self.T.get(tid) or {}).get('pl') or {}).get('gk') or [] if (g.get('gp') or 0) > 0]
            gk.sort(key=lambda g: -(g.get('gp') or 0))
            gk = [g for g in gk if (g.get('gp') or 0) >= 2][:3] or gk[:1]   # вратарь с одной игрой — шум (50 % отражённых и т. п.)
            if not gk:
                continue
            f = lambda x, d=1: ('%.*f' % (d, x)).replace('.', ',') if x is not None else '—'  # noqa: E731
            tr = ''.join('<tr><td>%s%s</td><td>%d</td><td class="pt">%s<small>%%</small></td><td>%s</td><td class="so">%s</td></tr>'
                         % (esc(g.get('n', '')), (' <small class="no">№%s</small>' % esc(g['no'])) if g.get('no') not in (None, '') else '',
                            g.get('gp') or 0, f(g.get('sv')), f(g.get('gaa'), 2), g.get('so') or 0) for g in gk)
            cols.append('<div class="mq-card"><h3>%s</h3><table class="mq-t mq-g"><thead><tr><th>Вратарь</th><th title="Игры">И</th>'
                        '<th title="Процент отражённых бросков">Отражено</th><th title="Пропущено шайб за игру">Пропуск.</th>'
                        '<th class="so" title="Матчи на ноль">На ноль</th></tr></thead><tbody>%s</tbody></table></div>' % (self.head(m, tid, from_dir), tr))
        if not cols:
            return ''
        return ('<section class="fc-sec mq" aria-labelledby="mq-gk"><div class="wrap"><h2 id="mq-gk">Вратари</h2>'
                '<p class="mq-lead">Цифры за сезон. Кто выйдет в старте, клубы обычно объявляют только перед игрой.</p><div class="mq-two">%s</div>'
                '<p class="mq-note">Отражено — доля отражённых бросков. Пропуск. — пропущено шайб в среднем за игру.</p></div></section>\n'
                % ''.join(cols))

    def blocks(self, m, from_dir):
        """→ dict: rest, hot, ha, gk — готовые секции (пустая строка, если данных нет или не хоккей)."""
        out = {'rest': '', 'hot': '', 'ha': '', 'gk': ''}
        if m.get('sport') != 'hockey' or m.get('lg') not in ('khl', 'nhl'):
            return out
        for k, fn in (('rest', self.rest_block), ('hot', self.hot_block), ('ha', self.homeaway_block), ('gk', self.goalies_block)):
            try:
                out[k] = fn(m, from_dir)
            except Exception as e:  # noqa: BLE001
                print('match_extra %s %s: %r' % (fn.__name__, m.get('key'), e))
        return out
