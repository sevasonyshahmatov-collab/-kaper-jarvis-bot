# -*- coding: utf-8 -*-
"""Единая настройка адреса и индексации сайта v3a. Меняется только здесь (или переменными окружения в Actions).

SITE_ORIGIN       адрес сайта без слэша в конце. Домена пока нет (решение владельца 05.11), стоит заглушка.
                  Когда домен появится: заменить здесь (или задать SITE_ORIGIN в окружении) и запустить `python3 seo/build_seo.py`.
INDEXING_OPEN     False: на всех страницах meta robots noindex, robots.txt закрывает сайт целиком.
                  True: noindex убирается, robots.txt открывает сайт и указывает на sitemap.xml. Включать только по решению владельца.
"""
import os

SITE_ORIGIN = os.environ.get('SITE_ORIGIN', 'https://jarvibet.example').rstrip('/')
INDEXING_OPEN = os.environ.get('SITE_INDEXING_OPEN', '0') == '1'
SITE_NAME = 'JARVIS'
TELEGRAM = 'https://t.me/jarvibet'
