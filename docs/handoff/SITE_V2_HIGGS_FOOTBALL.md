# Сайт v2 — Футбол: промпты Higgsfield (картинка → видео), отрезки F0–F6 (30.10)

Основа: `SITE_V2_CAMERA.md` (идея владельца, референсы 1а–1е, маршрут F0–F6). Пример стиля, который уже получился в
Higgsfield: `team/out/2026-10-30/site_v2_bg/s1h_frame.png`. Референсы: `team/site_v2_refs/F2_concourse.webp`, `F6_final.webp`.

## Владельцу: как работать (коротко)
1. **Начать с F0.** Higgsfield → **Image** (Soul или Nano Banana), 16:9, промпт «Кадр начала F0» → 3–4 варианта → выбрать один.
2. Остальные кадры делать **с выбранным F0 как референсом** (поле Reference / «по картинке»), чтобы стадион везде был один и тот же.
3. **Video** (Kling / Veo / Hailuo — там, где есть поля **Start frame** и **End frame**): старт = кадр начала, конец = кадр конца, промпт видео + пресет камеры, 1080p, 5–10 с.
4. Склейка без шва: **старт следующего отрезка = последний кадр предыдущего ролика.** Надёжнее всего: скачать готовый ролик, взять из него последний кадр (стоп-кадр/скриншот) и поставить его в Start frame следующего.
5. Порядок: F0 → F1 → F2 → F2b → F3 → F4 → F5 → F6. Присылать в чат «Сайт v2» или в бот: ролик (mp4) + оба кадра, подпись «F1, вариант 2». Сжатие, scrub по прокрутке и наши слои (гербы, данные, текст) делает команда.

## Общее для всех отрезков
**Стиль (добавлен в каждый промпт):** фотореализм, кино (ARRI Alexa, anamorphic), палитра — глубокий синий #071225,
тёплое золото прожекторов #ffc93c, зелень газона #2ee59d, холодный циан #3ee0ff в подсветке; сумерки → ночь.

**«ДНК» вымышленного стадиона** (в каждом промпте, чтобы модель не меняла здание): огромная открытая чаша, фасад —
белая-золотистая решётка с геометрическим узором (в духе новых стадионов Саудовской Аравии), кольцевой козырёк крыши
с открытым центром и рядом прожекторов по кромке, тонкая циановая LED-лента вдоль козырька, пальмы и широкая площадь
у главного входа, пустыня и огни города по краям.

**Общий негативный промпт** (в поле Negative, если есть; если нет — фразу «no text, no logos…» уже содержат промпты):
```
text, letters, numbers, captions, watermark, signature, logo, club crest, emblem, badge, league logo, brand name,
sponsor, advertising on boards, billboard text, scoreboard graphics, real stadium, Camp Nou, recognizable landmark,
real football players, celebrity, close-up faces, distorted faces, extra limbs, deformed bodies, crowd faces in focus,
cartoon, illustration, CGI look, plastic, oversaturated, HDR halos, fisheye distortion, warped architecture, bent
lines, flicker, jitter, camera shake, cuts, scene change, morphing, frame jump, low resolution, blurry, noise, banding
```

**Спокойные зоны под текст** — у каждого отрезка ниже; смысл: там нет ярких деталей, контраст низкий, ничего не
мелькает. Гербы, данные на экранах и плашки команда кладёт кодом — в генерации их нет специально.

---

## F0 — петля: дрон кружит над стадионом (8–10 с) · раздел «Первый экран», «Прогноз дня», кнопка Telegram
Петля: **кадр начала = кадр конца** (одна и та же картинка в Start и End).

**(а) Кадр начала (Image, 16:9)**
```
Aerial helicopter view of a colossal fictional open-air football stadium at dusk, camera tilted 40-45 degrees down from
about 180 m, the stadium bowl fills 85-90% of the frame, edges almost touching the borders. White-gold geometric lattice
facade inspired by new Saudi Arabian stadiums, ring-shaped cantilever roof with an open center, a row of floodlights
and a thin cyan LED band along the roof edge. Inside, the bowl glows: full stands as tiny warm dots, bright green
striped pitch #2ee59d with white lines, tiny players mid-game. City lights, palm-lined plaza, avenues with car light
trails only at the very edges. Deep blue dusk sky #071225, warm gold floodlight glow #ffc93c, cyan accents #3ee0ff.
Photorealistic, cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**(б) Кадр конца** = тот же кадр (петля).

**(в) Видео**
```
Slow, steady drone orbit around the fictional open-air football stadium at dusk, camera keeps a 40-45 degree downward
tilt and constant 180 m altitude, the bowl stays centered and fills the frame for the whole shot. The camera arcs
gently about 20 degrees to the right and smoothly returns, ending on exactly the first frame for a seamless loop.
Inside the bowl a football match is in progress: tiny players run, the ball moves, crowd lights twinkle. Floodlights
glow warm gold, cyan LED band on the roof edge softly pulses, car light trails flow in the city streets at the edges,
faint haze drifts. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no shake,
no morphing of the architecture. 10 seconds.
```
**(г) Пресет:** Orbit / Arc (медленно); если петля не замыкается — Arc Right без возврата, петлю делаем кодом «туда-обратно».
**(д) Текст:** верхняя треть кадра (небо) и левый край над городом; стадион — центр-низ. Внутренняя тёмная часть
небосвода над чашей не должна иметь прожекторных бликов.

---

## F1 — снижение к главному входу и влёт внутрь (8–10 с) · «Сегодня в эфире» (матчи дня)
**(а) Кадр начала** = кадр F0 (тот же, что Start/End петли).

**(б) Кадр конца** (= кадр начала F2)
```
Interior view just past the main entrance of a fictional giant football stadium at dusk, camera at 3 m height in the
center of a wide concourse, looking straight ahead into a tall multi-level atrium: raw concrete, slanted beams of the
stand overhead, balconies with dark railings on massive columns on the right, a curved wall with colored ribs on the
left, warm sunset light in stripes between columns, cold cyan edge light #3ee0ff along the ceiling, warm matte floor.
Empty fabric flags and long banners in club colors (red, sky blue, white, navy, yellow) hang at different heights from
beams and balconies, plain without any symbols. Very few distant silhouettes. Deep blue #071225 shadows, gold #ffc93c
light. Photorealistic, cinematic film still, ARRI Alexa anamorphic, no text, no logos, no crests.
```

**(в) Видео**
```
Continuous drone flight from high above the fictional stadium at dusk down to its main entrance: the camera smoothly
descends and pitches up from a 45 degree downward view to eye level, gliding over the palm-lined plaza toward the
glowing white-gold lattice facade, then flies straight through the tall open main entrance into the concourse and
stops in the center of the atrium with hanging plain club-colored flags. Speed: slow at start, steady glide in the
middle, gentle ease-out at the end. Floodlight glow and the match sound of the bowl implied by moving light, faint
haze, a few tiny distant silhouettes walking. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot,
no cuts, steady, no shake, no text, no logos. 10 seconds.
```
**(г) Пресет:** FPV Drone (плавный) или Crane Down → Dolly In; если модель путается — разбить: F1a (сверху к фасаду), F1b (влёт).
**(д) Текст:** первые 2/3 ролика — небо сверху; в конце — верх кадра (бетонный потолок). Карточки матчей ставим вдоль
нижней трети слева, где площадь/пол спокойные.

---

## F2 — лобби: пролёт по центру подтрибунного атриума (8–10 с) · «Лиги и клубы» (гербы-3D кодом)
Референс: `team/site_v2_refs/F2_concourse.webp` (можно дать модели как Reference — но реальный цвет рёбер заменить на разные клубные).

**(а) Кадр начала** = кадр конца F1.

**(б) Кадр конца** (= кадр начала F2b)
```
Deep inside the concourse of a fictional giant football stadium, end of a long concrete atrium: camera at 3 m height,
center of the passage, looking through a wide arched opening into a round multi-level hall with a glowing cyan neon
ring at its upper level. Behind the camera's view the four-storey concrete atrium continues: balconies with dark
railings, slanted stand beams, plain fabric banners in club colors (red, sky blue, white, claret, yellow, navy) hanging
at different heights and depths. Warm golden light #ffc93c, cold cyan edge light #3ee0ff, deep blue #071225 shadows,
warm matte floor with soft reflections, no people or a couple of tiny far silhouettes. Photorealistic, cinematic film
still, ARRI Alexa anamorphic, no text, no logos, no crests.
```

**(в) Видео**
```
Slow forward dolly flight through the center of a tall four-storey concrete stadium concourse at dusk, camera at a
constant 3 m height, perfectly centered in the passage. Plain fabric flags and long banners in club colors hang from
beams and balconies at different heights and gently sway, passing by on both sides with strong parallax. Warm sunset
light falls in stripes between massive columns, cold cyan light runs along the ceiling edge, light dust particles float
in the beams. The camera moves toward a wide arched opening and ends facing a round hall with a glowing cyan neon ring.
Few tiny distant silhouettes. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady,
constant speed, no text, no logos, no crests. 8 seconds.
```
**(г) Пресет:** Dolly In (медленно).
**(д) Текст:** нижняя треть по центру (пол) и тёмная зона под балконами справа. Гербы-3D кодом — на высоте флагов,
слева и справа от оси, с параллаксом.

---

## F2b — круглый атриум «зал клубов» (8 с) · продолжение «Лиги и клубы» / матчи дня на LED-экране
**(а) Кадр начала** = кадр конца F2.

**(б) Кадр конца** (= кадр начала F3)
```
Upper level of a round multi-level atrium in a fictional football stadium at night, camera at the black railing,
looking across the atrium toward a dark doorway with a soft cyan glow on the far side. Around the circle: a cyan-green
neon ring #3ee0ff #2ee59d along the edge, white curved ribbon sculptures and spotlights under the ceiling, a row of
football shirts on mannequins in plain club colors (red, white, sky blue, claret and blue, red-white stripes,
black-white stripes, red-black stripes, blue-black stripes, yellow-black, green-white hoops, navy), no badges, no
sponsors, no names. Below the railing runs a continuous curved LED screen around the whole circle, completely blank,
dark navy #071225 glow. Warm gold spotlights #ffc93c. Photorealistic, cinematic film still, ARRI Alexa anamorphic,
no text, no logos, no crests, no numbers.
```

**(в) Видео**
```
The camera glides from an arched entrance into a round multi-level atrium and makes a slow 90 degree arc along the
upper railing, keeping the center of the atrium in view. A row of football shirts on mannequins in plain club colors
passes by in the foreground with gentle parallax; the cyan-green neon ring softly breathes, white ribbon sculptures
and spotlights glow under the ceiling. The continuous curved LED screen below the railing stays blank dark navy with a
faint even glow, nothing displayed on it. The move ends facing a dark doorway with soft cyan light on the far side.
Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no text, no logos, no badges,
no sponsors. 8 seconds.
```
**(г) Пресет:** Arc / Orbit (влево, медленно); запасной — Dolly In + Pan Right.
**(д) Текст и данные:** **LED-экран** — сюда кодом матчи дня / «обещали–зашло» с перспективой; заголовок — над
кольцом в тёмной зоне потолка.
**Цвета 19 клубов на манекенах** (без гербов): Рома — бордо-оранж; ПСЖ — тёмно-синий с красной полосой; Ман Сити —
небесно-голубой; Челси — синий; Бавария — красный; Барселона — гранатово-синие полосы; Реал — белый; Арсенал — красный с
белыми рукавами; МЮ — красный; Атлетико — красно-белые полосы; Милан — красно-чёрные полосы; Интер — сине-чёрные полосы;
Боруссия Д — жёлтый с чёрным; Спортинг — зелёно-белые горизонтальные полосы; Бенфика — красный; Порту — сине-белые полосы;
Наполи — голубой; Ювентус — чёрно-белые полосы; Ливерпуль — красный. В промпт все 19 модель не уложит — даём набор
цветов; если просит точнее — генерировать 2 варианта и выбрать, где цвета разнообразнее.

---

## F3 — комната аналитики (8 с) · «Как думает модель» (10 000 розыгрышей, «обещали/зашло»)
Придумано: тёмный «штаб» под трибуной — длинный стол-тактическая доска с подсвеченным макетом поля, стена из 9 пустых
экранов, стеклянная стена в конце с видом на освещённое поле сверху. Экраны пустые — графики кладём кодом.

**(а) Кадр начала** = кадр конца F2b.

**(б) Кадр конца** (= кадр начала F4)
```
Dark analytics war room under the stands of a fictional football stadium at night, camera at 1.6 m height at the far
end of the room, looking toward a heavy open door that leads into a players' tunnel lit by a row of white oval ceiling
panels. In the room: a long glowing tactical table with a miniature green pitch #2ee59d etched in light, a wall of nine
large blank screens glowing empty dark navy #071225 with thin cyan edges #3ee0ff, warm gold desk lamps #ffc93c, glass
wall on the side overlooking the floodlit pitch below. No people. Moody, high contrast, light haze. Photorealistic,
cinematic film still, ARRI Alexa anamorphic, no text, no numbers, no charts, no logos.
```

**(в) Видео**
```
Slow cinematic dolly through a dark analytics war room under a stadium at night. The camera enters from a doorway,
moves along a long glowing tactical table with a miniature green pitch etched in light, small points of light drift
across the table surface like simulated passes. On the wall nine large blank screens glow empty dark navy with thin
cyan edges, nothing displayed. Through the side glass wall the floodlit pitch is visible below with a tiny match in
progress. Warm gold desk lamps, faint haze. The camera turns gently and ends facing a heavy open door to a tunnel with
white oval ceiling lights. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady,
no text, no numbers, no logos. 8 seconds.
```
**(г) Пресет:** Dolly In + лёгкий Pan Right (или Push In).
**(д) Текст и данные:** **экраны на стене** — графики «10 000 розыгрышей» кодом; заголовок — тёмный верх кадра над
экранами; стол — под точечную анимацию розыгрышей.

---

## F4 — тоннель к полю (8 с) · «Честные итоги» (проверка ставок по месяцам)
**(а) Кадр начала** = кадр конца F3 (вид через дверь в тоннель).

**(б) Кадр конца** (= кадр начала F5)
```
Top of the stairs at the end of a players' tunnel in a fictional football stadium at night, camera at 1.5 m height
looking out of the opening onto the floodlit pitch: bright green grass #2ee59d, white lines, a ring of floodlights on
the roof edge, full two-tier stands as tiny lights with no visible faces, a match in progress with tiny distant
players. Behind and around the camera: tunnel walls with blank panels in club colors, warm gold light #ffc93c, cold
cyan edge light #3ee0ff, deep blue #071225 shadows, light haze in the floodlight beams. Pitch-side boards blank dark.
Photorealistic, cinematic film still, ARRI Alexa anamorphic, no text, no logos, no advertising.
```

**(в) Видео**
```
Slow steady push through a straight symmetrical players' tunnel at night, camera at 1.5 m, perfectly centered. Rows
of white glowing oval ceiling panels recede into perspective and pass overhead; both walls are lined with blank tall
panels in club colors, softly uplit with warm gold light from below; the glossy dark red-brown floor reflects every
light. At the end, steps rise toward a bright opening; the camera climbs the steps and stops at the top, revealing the
floodlit green pitch, the roof ring of floodlights and full stands with a tiny match in progress. Light haze in the
beams. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, constant speed, no
text, no logos, no people on the wall panels. 8 seconds.
```
**(г) Пресет:** Dolly In (медленно, по центру).
**(д) Текст и данные:** **пустые панно на стенах** — карточки месяцев «Честных итогов» кодом с перспективой; заголовок —
по центру сверху, между рядами потолочных ламп (держать текст между лампами, не на них).

---

## F5 — выход на поле, подъём вправо-вверх (8–10 с) · «Подписаться» (Telegram, приложение)
По `SITE_V2_CAMERA.md` п. 1е: F5 — в той же сумеречной гамме, без чёрного неба.

**(а) Кадр начала** = кадр конца F4.

**(б) Кадр конца** (= кадр F6, т.е. та же картинка, что Start/End петли F6 — см. ниже)

**(в) Видео**
```
The camera emerges from the players' tunnel onto the edge of a floodlit football pitch at low height, about 1 m above
the grass, wide angle looking up: the roof ring with rows of floodlights, deep blue dusk sky in the open center, full
two-tier stands with tiny people and no visible faces, a match in progress with tiny players, blank dark pitch-side
boards. Then the camera rises smoothly and drifts to the right, climbing over the lower tier toward the upper rim of
the stands, the horizon opens with a dramatic sunset of pink-orange clouds, and it settles high on the upper tier
looking down at the pitch diagonally. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts,
steady, smooth ease-in ease-out, no text, no logos. 10 seconds.
```
**(г) Пресет:** Crane Up + Arc Right (если есть комбинированный — «Crane Up» + «Orbit Right»; иначе Crane Up).
**(д) Текст:** начало — небо в проёме крыши по центру (блок «Подписаться» + кнопка Telegram); конец — небо над
горизонтом (см. F6).

---

## F6 — петля: финал с верхнего края трибуны, закат (8–10 с) · подвал + «ПРОГНОЗЫ НА ХОККЕЙ»
Референс ракурса: `team/site_v2_refs/F6_final.webp` (только ракурс и небо; стадион — наш, вымышленный). Петля: **кадр
начала = кадр конца**.

**(а) Кадр начала** (= кадр конца F5)
```
View from the upper rim of the stands of a colossal fictional open-air football stadium at sunset, camera at upper
tier height, wide angle, tilted 20-25 degrees down. The floodlit green pitch #2ee59d lies diagonally in the lower-left
third, full stands curve around it as a sea of tiny people with no visible faces, the edge of the near tier in the
lower right corner, ring-shaped roof edge with a row of floodlights and a thin cyan LED band #3ee0ff. The upper half
of the frame is a dramatic sunset sky: mammatus clouds glowing pink and orange, deep blue sky #071225 above, warm gold
light #ffc93c, silhouette of low hills and twinkling city lights on the horizon, tiny players mid-match. Photorealistic,
cinematic film still, ARRI Alexa anamorphic, no text, no logos, no flags, no advertising boards, no scoreboard.
```
**(б) Кадр конца** = тот же кадр (петля).

**(в) Видео**
```
Locked-off, almost static wide shot from the upper rim of a fictional open-air football stadium at sunset, with a very
subtle slow push forward and return so the last frame matches the first for a seamless loop. Dramatic pink-orange
mammatus clouds drift slowly across the deep blue sky, the light on them shifts gently. Below, the floodlit green pitch
lies diagonally in the lower-left third, a match in progress with tiny players running, the crowd ripples as tiny
lights. City lights twinkle on the horizon, the cyan LED band on the roof edge softly pulses. Photorealistic,
cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no shake, no text, no logos. 10 seconds.
```
**(г) Пресет:** Static / Push In (минимальный); если петля не замыкается — делаем «туда-обратно» кодом.
**(д) Текст:** **верхняя половина (небо)** — финальный блок «Подписаться» и кнопка «ПРОГНОЗЫ НА ХОККЕЙ», лучше в
левой-верхней части, где облака темнее; подвал — по нижнему краю поверх тёмной трибуны.

---

## Обратный путь (F*_back) — ВТОРОЙ ЭТАП (владелец 30.10)
**Сначала делаем все прямые отрезки F0–F6.** Без back-роликов сайт при прокрутке вверх просто проигрывает прямой ролик
назад — это работает. Back-ролики — улучшение: камера развёрнута на 180° и смотрит по ходу обратного движения.

Как стыкуется: у каждого стыка прямых отрезков есть кадр «вид назад» (R1–R5) — та же точка, камера развёрнута.
F*_back идёт от R(конец прямого) к R(начало прямого), поэтому back-ролики тоже склеиваются между собой без шва.
Крайние back-отрезки заканчиваются/начинаются на кадрах петель (F0 и F6), поэтому в них камера в пути **сама
разворачивается** обратно к петле. На сайте при смене направления прокрутки — наплыв 0,3 с между прямым и back-роликом
(команда, кодом).

| Back | Start frame | End frame | Пресет |
|---|---|---|---|
| F5_back | кадр F6 | R5 | Crane Down + Arc Left |
| F4_back | R5 | R4 | Dolly In |
| F3_back | R4 | R3 | Dolly In + Pan Left |
| F2b_back | R3 | R2 | Arc / Orbit (вправо) |
| F2_back | R2 | R1 | Dolly In |
| F1_back | R1 | кадр F0 | FPV Drone / Crane Up |

Делать в порядке сверху вниз (от F6 к F0), так же: последний кадр готового back-ролика → Start frame следующего.

### Кадры «вид назад» (Image, 16:9; с референсом выбранных кадров прямого пути)
**R1** (стык F1/F2, у главного входа изнутри, смотрим наружу)
```
Inside the main entrance of a fictional giant football stadium at dusk, camera at 3 m height in the center of the
concourse, looking back out through the tall open entrance toward the palm-lined plaza and the city lights beyond.
Raw concrete, slanted stand beams overhead, the white-gold geometric lattice facade framing the opening from inside,
plain fabric flags in club colors (red, sky blue, white, navy, yellow) hanging at different heights in the foreground,
warm sunset light flowing in, cold cyan edge light #3ee0ff along the ceiling, deep blue dusk sky #071225 outside, gold
#ffc93c light. Photorealistic, cinematic film still, ARRI Alexa anamorphic, no text, no logos, no crests.
```
**R2** (стык F2/F2b, у арки в круглый зал, смотрим назад вдоль лобби)
```
Inside a tall four-storey concrete stadium concourse at dusk, camera at 3 m height standing at a wide arched opening,
looking back down the long atrium toward the bright distant main entrance. Balconies with dark railings on massive
columns on the left, curved wall with colored ribs on the right, slanted stand beams overhead, plain fabric banners in
club colors hanging at different heights and depths, warm sunset light in stripes between columns, cold cyan edge
light #3ee0ff, deep blue #071225 shadows, warm matte floor. No people or tiny far silhouettes. Photorealistic,
cinematic film still, ARRI Alexa anamorphic, no text, no logos, no crests.
```
**R3** (стык F2b/F3, у двери в аналитику, смотрим назад через круглый зал)
```
Upper level of a round multi-level atrium in a fictional football stadium at night, camera with its back to a dark
doorway, looking across the atrium toward the wide arched opening to the long concrete concourse with warm light
beyond. Cyan-green neon ring #3ee0ff #2ee59d along the edge, white curved ribbon sculptures and spotlights under the
ceiling, a row of football shirts on mannequins in plain club colors with no badges or sponsors, a continuous curved
blank LED screen below the railing glowing dark navy #071225, warm gold spotlights #ffc93c. Photorealistic, cinematic
film still, ARRI Alexa anamorphic, no text, no logos, no numbers.
```
**R4** (стык F3/F4, у двери в тоннель, смотрим назад через комнату аналитики)
```
Dark analytics war room under the stands of a fictional football stadium at night, camera at 1.6 m height with its
back to the tunnel door, looking back across the room toward a doorway glowing with soft cyan neon light from a round
atrium. A long glowing tactical table with a miniature green pitch #2ee59d etched in light leads the eye, a wall of
blank screens glowing empty dark navy #071225 with thin cyan edges #3ee0ff on the side, warm gold desk lamps #ffc93c,
light haze. No people. Photorealistic, cinematic film still, ARRI Alexa anamorphic, no text, no numbers, no charts,
no logos.
```
**R5** (стык F4/F5, верх ступеней у выхода на поле, смотрим назад в тоннель)
```
Top of the stairs at the pitch end of a players' tunnel in a fictional football stadium at night, camera at 1.5 m
height with its back to the floodlit pitch, looking down the steps and into the long straight symmetrical tunnel:
rows of white glowing oval ceiling panels receding into perspective, walls lined with blank tall panels in club
colors uplit with warm gold light #ffc93c, glossy dark red-brown floor with reflections, a heavy open door at the far
end with faint cyan light #3ee0ff. Floodlight spill and light haze from behind the camera. No people. Photorealistic,
cinematic film still, ARRI Alexa anamorphic, no text, no logos.
```

### Видео обратного пути
**F5_back** (кадр F6 → R5), 10 с
```
From the upper rim of a fictional football stadium at sunset, the camera smoothly descends and drifts to the left down
across the stands toward the pitch-side tunnel mouth, gradually turning around as it goes. Pink-orange clouds and the
floodlight ring slide out of view above, the match continues with tiny players on the green pitch, crowd lights
twinkle. The camera settles low at the top of the tunnel steps, now facing into the tunnel with rows of white oval
ceiling lights receding ahead. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady,
smooth ease-in ease-out, no text, no logos. 10 seconds.
```
**F4_back** (R5 → R4), 8 с
```
Slow steady push from the top of the stairs down into a straight symmetrical players' tunnel at night, camera at 1.5 m,
perfectly centered, the floodlit pitch left behind. Rows of white glowing oval ceiling panels pass overhead, blank tall
wall panels in club colors uplit with warm gold glide by on both sides, the glossy red-brown floor reflects the lights.
The camera travels the whole tunnel and passes through a heavy open door into a dark analytics room, ending facing a
long glowing tactical table and a distant doorway with soft cyan light. Photorealistic, cinematic, ARRI Alexa
anamorphic. One continuous shot, no cuts, steady, constant speed, no text, no logos. 8 seconds.
```
**F3_back** (R4 → R3), 8 с
```
Slow cinematic dolly back through a dark analytics war room under a stadium at night, moving forward along a long
glowing tactical table with a miniature green pitch etched in light, small points of light drifting across it. On the
side, a wall of blank screens glows empty dark navy with thin cyan edges, nothing displayed; warm gold desk lamps, faint
haze. The camera passes through the doorway with soft cyan light and emerges on the upper level of a round atrium with
a cyan-green neon ring, ending facing across the atrium toward an arched opening to a long concourse. Photorealistic,
cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no text, no numbers, no logos. 8 seconds.
```
**F2b_back** (R3 → R2), 8 с
```
The camera makes a slow 90 degree arc to the right along the upper railing of a round multi-level atrium, keeping the
center of the atrium in view. A row of football shirts on mannequins in plain club colors passes in the foreground with
gentle parallax, the cyan-green neon ring softly breathes, white ribbon sculptures glow under the ceiling, the curved
LED screen below the railing stays blank dark navy. The camera exits through the wide arched opening and stops at its
threshold, looking down a long four-storey concrete concourse with hanging club-colored banners toward a bright
distant entrance. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no text, no
logos, no badges. 8 seconds.
```
**F2_back** (R2 → R1), 8 с
```
Slow forward dolly flight back through the center of a tall four-storey concrete stadium concourse at dusk, camera at
a constant 3 m height, heading toward the bright main entrance. Plain fabric flags and long banners in club colors hang
from beams and balconies at different heights, gently sway and pass on both sides with strong parallax. Warm sunset
light in stripes between massive columns, cold cyan light along the ceiling edge, dust particles float in the beams.
The camera ends just inside the tall entrance, looking out at the palm-lined plaza and city lights at dusk.
Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, constant speed, no text, no
logos, no crests. 8 seconds.
```
**F1_back** (R1 → кадр F0), 10 с
```
Continuous drone flight out of a fictional giant football stadium at dusk: the camera flies forward through the tall
open main entrance, over the palm-lined plaza, then rises steeply and arcs around while tilting down, until it hovers
at about 180 m looking 40-45 degrees down at the whole stadium bowl filling the frame, white-gold lattice facade, roof
ring with floodlights and cyan LED band, a match in progress on the bright green pitch, city lights at the edges.
Smooth ease-in ease-out. Photorealistic, cinematic, ARRI Alexa anamorphic. One continuous shot, no cuts, steady, no
shake, no morphing of the architecture, no text, no logos. 10 seconds.
```
**Текст на back-роликах** — те же разделы и те же зоны, что у прямых (небо, пол, панно, экраны), только зеркально по
положению: проверяем глазами на готовых кадрах.

---

## Если что-то пошло не так
- **Стадион «плывёт» между кадрами** — генерировать кадры с референсом выбранного F0 и повторять «ДНК» дословно.
- **Модель рисует буквы/гербы на флагах и футболках** — добавить в начало промпта «plain solid fabric, blank» и
  убрать слово «club» (оставить только цвета); мелкие следы надписей команда замажет.
- **Нет поля End frame** — делать только Start frame + промпт; стык команда сгладит наплывом 0,3 с.
- **F1 и F5 — самые трудные** (большой путь камеры). Если 10 с не хватает — делить на два ролика (F1a/F1b, F5a/F5b) через
  промежуточный кадр: для F1 — «камера на уровне глаз перед главным входом», для F5 — «камера над нижним ярусом».
