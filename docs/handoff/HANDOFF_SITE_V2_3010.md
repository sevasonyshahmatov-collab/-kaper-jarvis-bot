# Передача: «Сайт v2» (аккаунт Б) → новый чат «Сайт v2 — 2» (30.10, вечер)

Прошлый чат `session_01MtLSoeSv8gymmHS6ujNVRc` закрыт по просьбе владельца (дорого перечитывать). Читать: `CLAUDE.md`,
`team/NOW.md`, этот файл. Подробности по мере нужды: `docs/handoff/SITE_V2_ONESHOT.md` (раскадровка, раздел 1а — решения
владельца), `SITE_V2_CAMERA.md` (идея владельца), `SITE_V2_BRIEF.md` (ТЗ сайта v2).

## 1. Что делаем
Фон раздела «Футбол» сайта v2 — ОДИН непрерывный полёт камеры-дрона по вымышленному стадиону («ленты» на фасаде, ночь):
прокрутка вниз — путь вперёд, вверх — другой маршрут назад, наверху петля кружения, внизу петля зависания. Решения
владельца: гербы клубов на баннерах/в туннеле — можно (логотипы лиг/турниров/БК — нет); кубки в холле; ночь как на M1;
золотые линии-«ветер» — кодом на сайте, не в картинке; размытие под текст — кодом, картинки резкие.

## 2. Что готово
- **12 кадров пути вперёд** — `team/out/2026-10-30/frames/01_M1.jpg … 12_M5.jpg` (исходники `team/site_v2_refs/*_final.*`):
  01 стадион сверху · 02 площадь у входа · 03 холл с кубками · 04 лестница+мост+проём · 05 галерея (слева чаша, справа
  аналитика) · 06 комната аналитики · 07 туннель (светящиеся гербы) · 08 выход из туннеля (дымка) · 09 газон · 10 подъём
  над чашей · 11 угол чаши низко · 12 тот же угол выше (финал). 02, 07, 08, 10 — только превью 895×500 (оригиналы просить).
- **Видео** (Syntx → Kling → режим **Keyframes**, 1080, 5–10 с, без аудио, Multi-shot выкл., ползунок ближе к
  «Соответствию»): `team/site_v2_video/V01…V05` готовы и проверены (V01 01→02, V02 02→03, V03 03→04 10 с с поворотом
  влево — идея владельца, V04 04→05, V05 05→06). На стыках срезать статичные хвосты (~0,5 с у V02).
- Владелец присылает ролики **ссылками `https://r2.syntx.ai/...`** — домен разрешён в сети среды; качать `curl -L`,
  проверять листом кадров (`ffmpeg … fps=8/<dur>,scale=480:-1,tile=4x2`), смотреть 1 картинкой, коммитить `git add -f`.
  Google Drive-коннектор — аккаунт shakhmatovvsevolod24@gmail.com (папки владельца из другого аккаунта не видны).
- Макет сайта v2: ветка `claude/team-dev-site-v2-mock` (`team/site/v2/`: главная-развилка, `football/` с движком
  `assets/cam.js` — scrub по прокрутке, back-ролики, вихрь 360° на хоккей). Ссылка для владельца —
  raw.githack.com на коммит ветки (явные `index.html` в ссылках).

## 3. Дальше (по порядку)
1. Видео 6–11 (промпты ниже), петли L0 (01→01) и L1 (12→12).
2. Склейка `forward.mp4` (ffmpeg, срезать 2–4 кадра на стыках, подогнать цвет, all-intra для scrub), вставить в макет
   `football/` вместо постеров, видео «было/стало» владельцу (jarvis-send).
3. Обратный путь — 6 кадров (план в `SITE_V2_ONESHOT.md` 1а): KB1 вид с поля на вход в туннель (промпт был дан, ответа
   нет) → KB2 туннель обратно (камера под потолком) → KB3 галерея обратно (чаша справа) → KB4 с моста вниз на холл → KB5
   холл к стеклянному входу → KB6 подъём над площадью → конец = 01_M1. Потом видео B1–B7.
4. Хоккей — та же схема позже. Внешний вид в main — только после «было/стало» и «да».

## 4. Промпты видео 6–11 (Keyframes: первый кадр → второй)
Хвост всех: `One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, no cuts, no shake, no morphing of the architecture.`
- **6: 06→07, лучше 10 с** — `The camera moves across the dark analytics room toward a door at the back, passes through it into a narrow concrete service corridor lit by warm lamps, descends a short flight of stairs and turns into the players' tunnel with glowing club crests on the dark walls and a bright hazy opening to the pitch at the end.` + хвост.
- **7: 07→08** — `The camera flies straight along the players' tunnel past the glowing club crests toward the bright hazy exit, approaching the steps as mist drifts in from the pitch.` + хвост.
- **8: 08→09** — `The camera rises up the steps, flies out of the tunnel through the haze onto the pitch and glides low over the grass along the touchline, the full stadium with floodlights and phone lights opening around it, a match in progress.` + хвост.
- **9: 09→10** — `The camera smoothly rises from the grass to about 35 m and turns, revealing the whole bowl: the pitch with the match below, three tiers of stands with phone lights, the ring of floodlights and the night sky.` + хвост.
- **10: 10→11** — `The camera slowly orbits inside the stadium bowl along the stands and descends toward a corner of the pitch, fans with scarves coming into view in the foreground, the match continuing below.` + хвост.
- **11: 11→12** — `The camera rises slowly above the same corner of the stadium, keeping the same diagonal view, revealing the whole pitch from above and the dense crowd below, then gently stops and hovers.` + хвост.
- **L0: 01→01** — `The drone slowly orbits around the stadium at the same height, the bowl glowing, the match inside, car lights moving on the avenues, phone lights twinkling in the stands, returning exactly to the first frame. Steady, no cuts.`
- **L1: 12→12** — `The camera hovers almost still with a very slight drift, the match continues on the pitch, phone lights twinkle in the stands, floodlight haze slowly moves. Steady, no cuts.`

## 5. Как работать с владельцем (уроки)
- Промпты картинок: «Real documentary photograph…», без HEX и «cinematic/anamorphic», в конце «Not a 3D render…».
  Правки — «Edit this image. Keep everything exactly the same… Change ONLY…», одна-две правки за раз; прикреплять
  референсы (M1 для ночи/облика). Nano Banana Pro (Higgsfield/Syntx). Владелец не любит много вариантов промптов —
  давать ОДИН итоговый.
- Мои вклейки кодом владелец забраковал (K3) — точечные правки делать моделью; кодом можно цвет/небо (M2) и разметку поля (M1).
- Отвечать коротко, по-русски; каждый принятый кадр/ролик — сохранить и запушить в ветку команды.
