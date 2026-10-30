# Сайт v2 — промпты для макетов в нейросети (30.10)

Владелец 30.10: визуал макета-кода не нравится → сначала макеты главной в красивой нейросети (Syntx: Midjourney v7 /
GPT Image / Nano Banana / Flux), потом верстаем по выбранной картинке. Промпты на английском (модели понимают лучше),
русский текст на картинке модели пишут криво — его потом ставим в вёрстке, на макете важны композиция, свет, стиль.

Как работать: каждый промпт — 2–4 варианта; лучшие картинки — в бот или в чат «Сайт v2»; по ним — вёрстка 1:1.
Для Midjourney добавлять в конец: `--ar 16:9 --style raw --v 7` (компьютер) или `--ar 9:19.5 --style raw --v 7` (телефон).

## 1. Главная, первый экран — компьютер
```
Premium sports analytics website homepage, desktop UI design, dark night stadium theme. Hero section: huge bold
condensed headline on the left, two buttons (bright cyan primary, outlined secondary), a row of small league chips.
On the right a floating glass scoreboard card "match of the day": two club crests, countdown timer, three odds tiles,
one highlighted in gold, a thin probability bar. Background: cinematic view from a players' tunnel opening onto an ice
hockey rink under stadium floodlights, deep navy #071225, cyan #3ee0ff light accents, subtle volumetric fog, depth of
field. Clean top navigation with a sport switch "Hockey | Football". Awwwards site of the day quality, Godly-style,
editorial typography, generous spacing, realistic UI, sharp, 8k, no bookmaker logos, no watermark.
```

## 2. Главная, первый экран — футбол (та же сетка, другой фон)
```
Same premium dark sports analytics website hero as a desktop UI, but the football mode: background is a night
football pitch seen from the tunnel, fresh green turf #2ee59d accents, white pitch lines, floodlights, light haze.
Glass "match of the day" card on the right with two club crests, countdown and odds tiles. Sport switch at the top
set to "Football". Cinematic, Awwwards quality, minimal, high contrast, realistic UI, no logos of leagues or bookmakers.
```

## 3. Переход «лёд | газон» (сцена посередине страницы)
```
Website section design, dark: the screen split diagonally by a glowing line — left half an ice hockey rink from above
with blue and red lines, right half a night football pitch with white lines; two large portal cards "Hockey" and
"Football" with short stats under each. Cinematic lighting, floodlight beams, navy and gold palette with cyan for ice
and green for grass. Premium sports brand, Awwwards style, realistic UI mockup.
```

## 4. Блоки ниже (бенто-сетка) — компьютер
```
Dark premium sports analytics website, bento grid section: tiles of different sizes — today's matches feed with club
crests and win probability bars, a "honest results" tile with monthly win rate and a small line chart "promised vs
actual", a model explainer tile with dots forming three bars (home/draw/away), league tiles (KHL, NHL, Premier League,
La Liga, Serie A, Bundesliga, Ligue 1, Portugal, Champions League) as minimal icons. Navy #071225 background, gold
#ffc93c and cyan accents, glassmorphism kept subtle, crisp typography, Bento Grids / Godly inspiration, realistic UI.
```

## 5. Телефон — первый экран и прокрутка
```
Mobile app-like website design for iPhone, three screens side by side: 1) hero with bold headline, cyan button, and a
compact "match of the day" scoreboard card over a dark floodlit ice rink; 2) horizontal swipe feed of match cards
with crests, odds and probability bars; 3) results screen with monthly win rate cards. Bottom tab bar
"Hockey · Football · Picks · Results". Dark navy, cyan and gold accents, premium, Dribbble shot quality, realistic UI.
```

## 6. Фон-«видео» (кадры для сцен, потом — оживить в Higgsfield/Kling)
```
Cinematic wide shot from inside a dark stadium players' tunnel looking out at an empty ice hockey arena at night,
floodlights switching on, cold blue haze, no people, no logos, 16:9, photorealistic, film still.
```
```
Empty night football stadium, camera low on the pitch, floodlights, light mist over fresh green grass, no people,
no logos, 16:9, photorealistic, cinematic film still.
```
```
Giant LED scoreboard in a dark arena close-up, glowing digits, bokeh crowd lights, navy and gold, no text, no logos,
16:9, cinematic.
```

Запрещено на макетах (правила канала): логотипы букмекеров и лиг, «гарантия», промокоды, белое свечение вокруг курсора.
