# Сайт прогнозов (пробный запуск поиска)

Владелец 22.10: «пробный запуск поиска — давай попробуем, если бесплатно». Сайт бесплатный: GitHub Pages из
**отдельного открытого репозитория** (основной репозиторий закрытый — из него Pages бесплатно не публикует).
Свой домен (`jarvibet.ru` и т. п., 200–900 ₽ в год) — по желанию, потом.

## Что на сайте
- **Главная** — лендинг `landing.html` (тот же, что в артефакте). На сайте в блок «Матчи дня», табло «Прогноз дня» и бегущую
  строку итогов подставляются настоящие матчи и итоги (`window.__TODAY`, `__TL`, `__RES`); без них — примеры.
  Слайды «Внутри таблицы» — пока примеры данных (подписано «Пример данных»).
- **/prognozy/** — все прогнозы: ближайшие сверху, ниже сыгранные со счётом и знаком, честный итог «за 30 дней».
- **/prognozy/<день>-<хозяева>-<гости>.html** — страница матча: прогноз и кэф, вероятность, линия П1·Х·П2, форма команд,
  10 000 розыгрышей и «цифра матча», другие матчи дня; после матча — счёт и «зашёл / не зашёл». Разметка schema.org
  (SportsEvent, хлебные крошки) — для поиска.
- `sitemap.xml`, `robots.txt`, ключ IndexNow (`<ключ>.txt`) — Яндекс узнаёт о новых страницах за часы.

## Как обновляется
Задание `.github/workflows/site.yml`, без Claude: 03:23 МСК — прогнозы КХЛ дня и НХЛ ближайшей ночи (тот же расчёт, что у
шортсов) и итоги вчера; 10:23 МСК — итоги ночи НХЛ. Изменившиеся страницы отправляются в Яндекс (IndexNow).
Данные дней лежат в репозитории сайта, `data/<лига>-<день>.json`. ~5 мин Actions в день (~150 в месяц).

## Настройка владельцем (один раз, ~15 минут)
1. GitHub → **New repository**: имя, например `jarvibet`; **Public**; галочка **Add a README file** → Create.
2. В новом репозитории: **Settings → Pages** → Source: **Deploy from a branch**, Branch: **main**, папка **/(root)** → Save.
   Адрес сайта будет `https://<ваш логин>.github.io/jarvibet/`.
3. Токен записи только в этот репозиторий: аватар → **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**. Repository access: **Only select repositories** → `jarvibet`;
   Permissions → Repository → **Contents: Read and write**. Срок — 1 год. Скопировать токен.
4. В основном репозитории `-kaper-jarvis-bot`: **Settings → Secrets and variables → Actions**:
   - вкладка **Secrets** → New repository secret: `SITE_TOKEN` = токен из п. 3;
   - вкладка **Variables** → New repository variable: `SITE_REPO` = `<ваш логин>/jarvibet`.
   Свой домен (потом): переменная `SITE_URL` = `https://jarvibet.ru/` и домен в Settings → Pages → Custom domain.
5. Actions → «Сайт прогнозов» → Run workflow. Через пару минут сайт открывается по адресу из п. 2.

## Поиск (после первого запуска)
- **Яндекс Вебмастер** (webmaster.yandex.ru): добавить сайт → подтвердить способом «Мета-тег» (код прислать в чат —
  он не секретный, допишем в страницы) → «Индексирование → Файлы Sitemap» → `<адрес сайта>sitemap.xml`.
- **Google Search Console** (search.google.com/search-console): ресурс «Префикс URL» → подтверждение мета-тегом → Sitemaps.
- Первые 1–3 месяца трафика из поиска почти не будет; смотрим через 2 месяца, по каким запросам приходят
  (Вебмастер → «Поисковые запросы»), и решаем, развивать ли.

## Проверка без сети
    SITE_URL=https://example.github.io/jarvis python team/site/build.py /tmp/site <plan.json> --no-settle

## Состояние (23.10)
- Сайт: **https://sevasonyshahmatov-collab.github.io/** — репозиторий `sevasonyshahmatov-collab/sevasonyshahmatov-collab.github.io`
  (переименован из `jarvibet`, чтобы сайт был в корне адреса: Яндекс Вебмастер подтверждает права только на весь адрес).
  Переменные: `SITE_REPO`, `SITE_URL`, `GOOGLE_VERIFICATION`; секрет `SITE_TOKEN`.
- Права подтверждены: Яндекс Вебмастер (мета-тег, код в `build.verify`) и Google Search Console (мета-тег из
  `GOOGLE_VERIFICATION`). Sitemap отправлен в Google. Не удалять мета-теги — иначе подтверждение слетит.
- Через ~месяц: Вебмастер → «Поисковые запросы», Search Console → «Эффективность» — по каким запросам приходят.
