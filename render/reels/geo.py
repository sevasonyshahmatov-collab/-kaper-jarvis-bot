# -*- coding: utf-8 -*-
"""Карта США для формата «Погода»: штаты из us-atlas (TopoJSON, проекция Albers USA 975×610, лицензия ISC —
data/LICENSE-us-atlas.txt; границы — US Census, общественное достояние) и та же проекция для городов."""
import json
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'us-states-albers-10m.json')

CITIES = {   # долгота, широта
    'Бостон': (-71.06, 42.36), 'Филадельфия': (-75.17, 39.95), 'Нью-Йорк': (-74.0, 40.71), 'Нью-Джерси': (-74.17, 40.73),
    'Вашингтон': (-77.04, 38.9), 'Питтсбург': (-79.99, 40.44), 'Баффало': (-78.88, 42.89), 'Детройт': (-83.05, 42.33),
    'Чикаго': (-87.63, 41.88), 'Коламбус': (-82.99, 39.96), 'Каролина': (-78.64, 35.78), 'Тампа-Бэй': (-82.46, 27.95),
    'Флорида': (-80.25, 26.16), 'Нэшвилл': (-86.78, 36.16), 'Сент-Луис': (-90.2, 38.63), 'Миннесота': (-93.09, 44.95),
    'Даллас': (-96.8, 32.78), 'Колорадо': (-104.99, 39.74), 'Юта': (-111.89, 40.76), 'Вегас': (-115.14, 36.17),
    'Анахайм': (-117.91, 33.84), 'Лос-Анджелес': (-118.24, 34.05), 'Сан-Хосе': (-121.89, 37.34), 'Сиэтл': (-122.33, 47.61),
}


def albers_usa(lon, lat):
    """d3.geoAlbersUsa().scale(1300).translate([487.5, 305]) для материковой части."""
    y0, y1 = math.radians(29.5), math.radians(45.5)
    sy0 = math.sin(y0)
    n = (sy0 + math.sin(y1)) / 2
    c = 1 + sy0 * (2 * n - sy0)
    r0 = math.sqrt(c) / n

    def raw(lam, phi):
        r = math.sqrt(c - 2 * n * math.sin(phi)) / n
        return r * math.sin(lam * n), r0 - r * math.cos(lam * n)

    cx, cy = raw(math.radians(-0.6), math.radians(38.7))
    x, y = raw(math.radians(lon + 96), math.radians(lat))
    k = 1300
    return 487.5 + k * (x - cx), 305 - k * (y - cy)


def states():
    """→ {название штата: [кольцо [(x, y), ...], ...]} в координатах 975×610."""
    topo = json.load(open(DATA))
    sc, tr = topo['transform']['scale'], topo['transform']['translate']
    arcs = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(a if not out else a[1:])
        return out

    res = {}
    for g in topo['objects']['states']['geometries']:
        name = g.get('properties', {}).get('name', g.get('id'))
        polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
        res[name] = [ring(r) for p in polys for r in p]
    return res
