# -*- coding: utf-8 -*-
"""Единая настройка адреса и индексации сайта v3a. Меняется только здесь (или переменными окружения в Actions).

SITE_ORIGIN       адрес сайта без слэша в конце. Домена пока нет (решение владельца 05.11), стоит заглушка.
                  Когда домен появится: заменить здесь (или задать SITE_ORIGIN в окружении) и запустить `python3 seo/build_seo.py`.
PUBLIC_ORIGIN     адрес, по которому сайт открывается СЕЙЧАС: для картинок превью ссылок (og:image, twitter:image) — Telegram
                  и соцсети скачивают картинку по полному адресу. Пока домена нет — github.io; canonical и sitemap по-прежнему
                  на SITE_ORIGIN (canonical на github.io не ставим). С доменом — то же, что SITE_ORIGIN.
INDEXING_OPEN     False: на всех страницах meta robots noindex, robots.txt закрывает сайт целиком.
                  True: noindex убирается, robots.txt открывает сайт и указывает на sitemap.xml. Включать только по решению владельца.
"""
import os

SITE_ORIGIN = os.environ.get('SITE_ORIGIN', 'https://jarvibet.example').rstrip('/')
PUBLIC_ORIGIN = os.environ.get('SITE_PUBLIC_ORIGIN', SITE_ORIGIN if 'jarvibet.example' not in SITE_ORIGIN
                               else 'https://sevasonyshahmatov-collab.github.io').rstrip('/')
INDEXING_OPEN = os.environ.get('SITE_INDEXING_OPEN', '0') == '1'
SITE_NAME = 'JARVIS'
TELEGRAM = 'https://t.me/jarvibet'
