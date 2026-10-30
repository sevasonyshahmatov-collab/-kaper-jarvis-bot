# Сайт v2 — Футбол: фон «один полёт камеры» (раскадровка и промпты Higgsfield, 30.10)

Заменяет структуру F0–F6 из `SITE_V2_HIGGS_FOOTBALL.md` (оттуда взяты «ДНК» стадиона, стиль, негатив). Идея и
референсы владельца: `SITE_V2_CAMERA.md` (1а–1е), картинки — `team/site_v2_refs/F2_concourse.webp` (холл),
`team/site_v2_refs/F6_final.webp` (финал, закат), `team/out/2026-10-30/site_v2_bg/s1h_frame.png` (пример тона, который
уже получился: тёмный бетон, циан, мокрый пол с отражениями).

**Новое требование владельца (30.10):** не склейка слайдов, а **один непрерывный полёт**. Вперёд: кружение снаружи →
снижение → вход → главный холл с баннерами → пролёты и переходы → туннель с клубами на стенах → поле → подъём с
разворотом (игра, полный стадион, открытое небо) → облёт чаши изнутри → фиксация сверху под углом внутри чаши, игра идёт.
Назад: **другой маршрут и ракурс** по тем же местам → снова снаружи у ракурса первого экрана → через пару секунд
кружение. Цикл бесконечный.

---

## 1. Владельцу коротко: как добиться цельности
1. **Сначала 5 мастер-кадров** (M1 стадион снаружи, M2 главный холл, M3 туннель, M4 поле с уровня газона, M5 финальная
   точка) — Higgsfield → Image, 16:9, 3–4 варианта каждого, утвердить «облик». Все остальные картинки делать **с ними как
   референсом** (поле Reference): стадион, свет и материалы не должны меняться.
2. **Цепочка:** скачал ролик A(n) → взял стоп-кадр **последнего кадра** → это Start frame ролика A(n+1). End frame —
   готовый ключевой кадр K (или мастер-кадр). Так ролики стыкуются кадр в кадр.
3. **Одно время суток — сумерки сразу после заката**, один свет и одна скорость. Во **все** промпты видео вставлять
   дословно одну и ту же «камерную» фразу (п. «Общее») — тогда скорость и манера полёта совпадают.
4. **Порядок:** M1–M5 → ключевые кадры K → L0 → A1…A11 по очереди → L1 → B1…B8 по очереди. Ролик плохой — переделать
   только его, соседей не трогать (их кадры стыка уже утверждены).
5. **Команда** склеит A1–A11 в ОДИН файл «вперёд», B1–B8 — в ОДИН файл «назад», без наплывов: подгонит цвет, уберёт
   2–4 кадра на стыках, выровняет скорость. Прокрутка двигает этот файл; петли L0 и L1 — отдельные короткие файлы.
6. Присылать в бот или чат «Сайт v2»: ролик mp4 + его Start/End кадры, подпись «A4, вариант 2».

---

## 2. Общее для всех промптов (вставлять дословно)
**[ДНК]** стадион — в каждом промпте картинки и в коротком виде в видео:
`a colossal fictional open-air football stadium with three stacked tiers, white-gold geometric lattice facade inspired
by new Saudi Arabian stadiums, a ring-shaped cantilever roof over the stands with a wide open center, a row of
floodlights and a thin cyan LED band along the roof edge, a palm-lined plaza at the main entrance, desert and city
lights beyond`

**[СВЕТ]** одно время суток:
`dusk just after sunset, deep blue sky #071225 with a warm orange-pink horizon, floodlights on, warm gold #ffc93c light
and cold cyan #3ee0ff accents, bright green pitch #2ee59d`

**[КАМЕРА]** — одна и та же фраза во всех видео (главный «клей» цельности):
`One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out,
no cuts, no shake, no morphing of the architecture.`

**[СТИЛЬ]** `Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.`

**Негатив** (поле Negative, где есть):
```
text, letters, numbers, captions, watermark, signature, logo, club crest, emblem, badge, league logo, brand name,
sponsor, advertising on boards, billboard text, scoreboard graphics, real stadium, Camp Nou, Santiago Bernabeu,
recognizable landmark, real football players, celebrity, close-up faces, distorted faces, extra limbs, deformed bodies,
crowd faces in focus, cartoon, illustration, CGI look, plastic, oversaturated, HDR halos, fisheye distortion, warped
architecture, bent lines, flicker, jitter, camera shake, cuts, scene change, morphing, frame jump, daylight noon, night
black sky, rain, low resolution, blurry, bokeh, shallow depth of field, soft focus, noise, banding
```
**Качество картинок (владелец 30.10):** генерировать **резкими**, в высоком разрешении — минимум 1920×1080, лучше
2K–4K (в настройках Image — максимальное качество / Upscale). **В промптах не просить размытие** (blur, bokeh, soft
focus, depth of field) — размытие под текст сайт делает сам кодом. Поэтому в промптах картинок стоит «ultra sharp,
highly detailed 4K». Видео — 1080p (или максимум, что даёт модель), стоп-кадры для Start frame брать из 1080p-ролика.

**Кубки (владелец 30.10):** в главном холле — подсвеченные витрины и постаменты с большими серебряными и золотыми
трофеями разных форм (в духе «ушастого» кубка, кубков чемпионатов), без гравировок, надписей и логотипов; ещё один —
на мосту-пролёте к атриуму. Есть в M2, K3, KB5 и в роликах A2 (конец), A3, A4, B5 (конец), B6.

**Модели.** Картинки: Nano Banana Pro / Soul / Seedream (с Reference). Видео: где есть **Start frame + End frame** —
Kling 2.5 / 2.1, Veo 3.1 (first/last frame), Hailuo 02; 1080p, 16:9, 24 к/с. Названия пресетов камеры в Higgsfield
меняются — если нужного нет, брать ближайший по смыслу или «без пресета» (движение уже описано в промпте).
**Скорость:** снаружи — «медленно» (дрон, ~8–10 м/с на большой высоте, на экране плавно); внутри — шаг пешехода
(~1,5–2 м/с); финал — почти неподвижно. В таблицах ниже — «медл.», «шаг», «покой».

---

## 3. Мастер-кадры M1–M5 (Image, 16:9)

**M1 — стадион снаружи, ракурс первого экрана** (= начало A1, конец B8, начало и конец петли L0; ракурс — п. 1а)
```
Aerial helicopter view of a colossal fictional open-air football stadium at dusk, camera tilted 40-45 degrees down from
about 180 m, the stadium bowl fills 85-90% of the frame with edges almost touching the borders. Three stacked tiers of
full stands, white-gold geometric lattice facade inspired by new Saudi Arabian stadiums, a ring-shaped cantilever roof
over the stands with a wide open center, a row of floodlights and a thin cyan LED band along the roof edge. Inside, the
bowl glows: the crowd as tiny warm dots, bright green striped pitch #2ee59d with white lines, tiny players mid-game. The
tall main entrance and palm-lined plaza at the lower right, city lights, avenues with car light trails and desert only
at the very edges. Dusk just after sunset, deep blue sky #071225 with a warm orange-pink horizon, warm gold floodlight
glow #ffc93c, cyan accents #3ee0ff. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no
logos, no advertising.
```

**M2 — главный холл** (= конец A2 / начало A3; референс `F2_concourse.webp`, п. 1б)
```
Interior of the main concourse of a colossal fictional football stadium at dusk, camera at 3 m height in the center of
the passage just past the main entrance, looking straight ahead into a vast five-storey atrium that recedes deep into
the building. Raw concrete, slanted beams of the stands overhead, a curved wall on the left with colored vertical ribs,
balconies with dark railings on massive columns on the right, stair bridges crossing the space at different levels.
Long plain fabric banners and tall flags hang from beams and balconies at different heights and depths, each in solid
club colors: red, sky blue, white, navy, claret, yellow, black-white, red-black, blue-black, green-white, completely
blank with no symbols. Along the center of the hall stand illuminated glass display cases and dark stone pedestals
with large silver and gold football trophies of different shapes, one with big curved handles like a classic European
cup, tall polished championship cups and a golden trophy, each lit by a warm spotlight from above and a cool cyan glow
from below, completely plain with no engravings, no text, no logos. Warm sunset light falls in stripes between the
columns through the white-gold lattice facade,
cold cyan edge light #3ee0ff along the ceiling, warm matte floor with soft reflections, deep blue shadows #071225, gold
light #ffc93c. Only a few tiny distant silhouettes. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens,
no text, no logos, no crests.
```

**M3 — командный туннель** (= конец A6 / начало A7; п. 1г, тон — `s1h_frame.png`)
```
Inside a straight symmetrical players' tunnel of a colossal fictional football stadium at dusk, camera at 1.5 m height
perfectly centered, looking toward the far end where steps rise to a bright opening onto the floodlit green pitch and
a warm orange-pink dusk sky. The ceiling is a row of white glowing oval panels receding into perspective. Both walls
are lined with tall blank rectangular panels, each panel framed in solid club colors (red, sky blue, white, navy,
claret, yellow, black-white stripes, red-black stripes, blue-black stripes, green-white hoops), the center of every
panel an empty matte surface, softly uplit with warm gold light #ffc93c from below. Glossy dark red-brown floor with
mirror reflections, cold cyan accent #3ee0ff at the floor edges, light haze in the air, deep blue shadows #071225. No
people. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no crests, no faces on
the panels.
```

**M4 — вид с поля, уровень газона** (= конец A8 / начало A9; п. 1д, но сумерки, не чёрное небо)
```
Low camera about 1 m above the grass at the touchline of a colossal fictional open-air football stadium at dusk, wide
angle looking along the pitch and slightly up. The bright green striped pitch #2ee59d with white lines runs toward the
far goal, a match in progress with players in the mid-distance, small and crisp, no recognizable faces. Full three-tier
stands rise on both sides as a sea of tiny people, the ring-shaped roof edge with rows of floodlights and a thin cyan
LED band #3ee0ff frames a huge open sky: deep blue #071225 above, warm orange-pink dusk glow near the rim. Blank dark
pitch-side boards, no screens content. Warm gold floodlight #ffc93c, light haze in the beams. Photorealistic, cinematic
film still, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```

**M5 — финальная точка внутри чаши** (= конец A11, начало B1, начало и конец петли L1; референс `F6_final.webp`, п. 1е)
```
View from high inside the bowl of a colossal fictional open-air football stadium at dusk, camera at the height of the
upper tier just below the roof edge, still inside the stadium, wide angle tilted 25 degrees down. The floodlit green
pitch #2ee59d lies diagonally in the lower-left third with a match in progress, tiny players, full three-tier stands
curve around it as a sea of tiny people with no visible faces, the edge of the near upper tier in the lower right
corner. The ring-shaped roof edge with a row of floodlights and a thin cyan LED band #3ee0ff crosses the upper part
of the frame, and through the wide open center a dramatic dusk sky: glowing pink-orange mammatus clouds, deep blue sky
#071225 above, low hills and twinkling city lights on the horizon. Warm gold floodlight #ffc93c. Photorealistic,
ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no flags, no advertising boards, no scoreboard.
```

---

## 4. Маршрут ВПЕРЁД (прокрутка вниз): A1–A11

| № | Start | End | Что видно | Раздел сайта поверх | Длит. | Скорость |
|---|---|---|---|---|---|---|
| A1 | M1 | K1 | кружение продолжается, дрон снижается 180 → 60 м, вылетает к фасаду и площади | первый экран «Прогноз дня» (уход) | 8 с | медл. |
| A2 | = посл. кадр A1 | M2 | над пальмами к главному входу, влёт внутрь, начало холла | «Сегодня в эфире» (матчи дня) | 8 с | медл. → шаг |
| A3 | = посл. A2 | K3 | полёт по холлу с подъёмом к уровню балконов, баннеры на разной высоте и глубине | «Лиги и клубы» | 8 с | шаг |
| A4 | = посл. A3 | K4 | пролёт над мостом-лестницей, арка, круглый «зал клубов», дуга вдоль кольца | «Сила команд» | 7 с | шаг |
| A5 | = посл. A4 | K5 | дверь → комната аналитики: стена пустых экранов, стол-поле, стекло на поле | «Как думает модель» | 7 с | шаг |
| A6 | = посл. A5 | M3 | спуск по винтовой рампе на уровень поля, служебный коридор, разворот в туннель | «Как думает модель» (конец) → «Честные итоги» | 7 с | шаг |
| A7 | = посл. A6 | K7 | туннель: панели клубов на стенах, ступени, проём | «Честные итоги» | 8 с | шаг |
| A8 | = посл. A7 | M4 | вылет из туннеля на газон, немного вдоль поля на высоте 1 м | «Подписаться» (начало) | 6 с | шаг → медл. |
| A9 | = посл. A8 | K9 | подъём с разворотом: видна игра и весь заполненный стадион под открытым небом | «Подписаться» | 8 с | медл. |
| A10 | = посл. A9 | K10 | облёт чаши внутри, первая половина (на уровне верхнего яруса, под кромкой крыши) | FAQ | 10 с | медл. |
| A11 | = посл. A10 | M5 | облёт чаши, вторая половина, торможение и фиксация в финальной точке | финал + «ПРОГНОЗЫ НА ХОККЕЙ» | 10 с | медл. → покой |

Итого вперёд ≈ 87 с видео (на сайте — прокрутка, а не время).

### Ключевые кадры вперёд (Image, 16:9, Reference — нужный мастер-кадр)
**K1** (конец A1, Reference M1)
```
Low aerial view at about 60 m height of a colossal fictional open-air football stadium at dusk, camera tilted 25
degrees down, facing the main entrance: the white-gold geometric lattice facade inspired by new Saudi Arabian stadiums
fills the upper two thirds of the frame, the ring-shaped roof edge with floodlights and a thin cyan LED band #3ee0ff
on top, the glow of the bowl rising above the roof. Below, a wide palm-lined plaza with warm lamps leads to a tall
glowing main entrance opening, a few tiny distant people walking. Dusk just after sunset, deep blue sky #071225 with a
warm orange-pink horizon, warm gold light #ffc93c. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens,
no text, no logos, no advertising.
```
**K3** (конец A3, Reference M2)
```
Deep inside the main concourse of a colossal fictional football stadium at dusk, camera floating at 10 m height at the
level of the third-floor balconies, near the far end of a five-storey concrete atrium. Ahead, a wide concrete stair
bridge crosses the space, and beyond it a tall arched opening glows with a cyan neon ring of a round hall. Around the
camera: long plain fabric banners in solid club colors (red, sky blue, white, navy, claret, yellow, black-white,
red-black) hang at different heights and depths, slanted stand beams overhead, balconies with dark railings on massive
columns; on the balcony to the right, a lit glass display case with a large silver trophy with big curved handles and
a golden championship cup, plain with no engravings. Warm sunset stripes of light #ffc93c, cold cyan edge light #3ee0ff, deep blue shadows #071225. No people.
Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no crests.
```
**K4** (конец A4; круглый «зал клубов», п. 1в)
```
Upper level of a round multi-level atrium inside a colossal fictional football stadium at dusk, camera at the black
railing, looking across the atrium toward a dark doorway with a soft cyan glow on the far side. Around the circle: a
cyan-green neon ring #3ee0ff #2ee59d along the edge, white curved ribbon sculptures and spotlights under the ceiling,
a row of football shirts on mannequins in plain club colors (red, white, sky blue, claret and blue, red-white stripes,
black-white stripes, red-black stripes, blue-black stripes, yellow, green-white hoops, navy), no badges, no sponsors,
no names. Below the railing runs a continuous curved LED screen around the whole circle, completely blank, glowing dark
navy #071225. Warm gold spotlights #ffc93c. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text,
no logos, no numbers.
```
**K5** (конец A5; комната аналитики)
```
Dark analytics war room under the stands of a colossal fictional football stadium at dusk, camera at 1.6 m height at
the far end of the room, a long glowing tactical table with a miniature green pitch #2ee59d etched in light in the
foreground, a wall of nine large blank screens glowing empty dark navy #071225 with thin cyan edges #3ee0ff on the left,
a tall glass wall on the right overlooking the floodlit pitch and full stands below under a dusk sky. Ahead, an opening
to a spiral concrete ramp going down, with a glowing cyan handrail. Warm gold desk lamps #ffc93c, light haze. No
people. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no numbers, no charts, no logos.
```
**K7** (конец A7, Reference M3)
```
Top of the stairs at the pitch end of a straight players' tunnel in a colossal fictional open-air football stadium at
dusk, camera at 1.5 m height looking out of the opening onto the floodlit pitch: bright green grass #2ee59d, white
lines, full three-tier stands as tiny lights with no visible faces, a match in progress with small distant players,
the roof ring with floodlights and cyan LED band #3ee0ff, warm orange-pink dusk sky above. At the frame edges: the last
club-colored blank wall panels and white oval ceiling lights of the tunnel, warm gold light #ffc93c, light haze in the
beams, blank dark pitch-side boards. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no
logos, no advertising.
```
**K9** (конец A9, Reference M4 и M5)
```
View from about 35 m above the touchline inside a colossal fictional open-air football stadium at dusk, camera tilted
30 degrees down, looking across the whole bowl: the bright green pitch #2ee59d in the lower half with a match in
progress, small players, full three-tier stands all around as a sea of tiny people with no visible faces, the
ring-shaped roof edge with floodlights and a cyan LED band #3ee0ff, and through the wide open center a huge dusk sky
with pink-orange clouds, deep blue #071225 above. The camera is inside the bowl, below the roof edge. Warm gold
floodlight #ffc93c, light haze. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos,
no advertising.
```
**K10** (конец A10 — противоположная сторона чаши, Reference M5)
```
View from the opposite side of the bowl of a colossal fictional open-air football stadium at dusk, camera at the
height of the upper tier just below the roof edge, still inside the stadium, tilted 25 degrees down, the pitch #2ee59d
seen end-on from behind one goal with a match in progress, tiny players, full three-tier stands curving on both sides
as a sea of tiny people with no visible faces, the ring roof edge with floodlights and a cyan LED band #3ee0ff across
the top, pink-orange clouds and deep blue sky #071225 through the open center, city lights on the horizon. Warm gold
light #ffc93c. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no scoreboard.
```

### Видео вперёд
**A1** · M1 → K1 · 8 с · пресет: Arc Right + Crane Down (или «Aerial descent»)
```
The drone continues its slow orbit around a colossal fictional open-air three-tier football stadium at dusk and
gradually descends from 180 m to about 60 m while arcing a quarter turn to the right. The white-gold lattice facade
grows larger, the glowing bowl with a match in progress slips behind the roof ring, and the palm-lined plaza with the
tall glowing main entrance comes into view ahead. Car light trails flow on the avenues, the cyan LED band on the roof
edge softly pulses. Dusk just after sunset, deep blue sky, warm orange horizon, gold floodlights. One continuous
unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no
shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```
**A2** · последний кадр A1 → M2 · 8 с · FPV Drone (плавный) / Fly Through
```
From 60 m above the palm-lined plaza the drone glides down and forward toward the white-gold lattice facade of a
colossal fictional football stadium at dusk, pitching up from a downward view to eye level, skimming over palm tops
and warm plaza lamps, then flies straight through the tall open main entrance into a vast concrete concourse and
slows down in its center, at 3 m height, facing a five-storey atrium with long plain banners in club colors hanging
at different heights. A few tiny distant silhouettes. Dusk just after sunset, warm gold light, cyan accents. One
continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no
cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no
logos, no crests.
```
**A3** · последний кадр A2 → K3 · 8 с · Dolly In + Crane Up
```
Slow forward flight through the center of a vast five-storey concrete stadium concourse at dusk, the camera rising
gently from 3 m to the level of the third-floor balconies. Long plain fabric banners and tall flags in solid club
colors hang from beams and balconies at different heights and depths and pass on both sides with strong parallax,
some above, some below the camera, swaying slightly. Below, the camera passes lit glass display cases with large silver
and gold trophies, light sliding across their polished surfaces. Warm sunset stripes between massive columns, cyan
light along the ceiling edge, dust particles in the beams. Ahead, a stair bridge and an arched opening
with a cyan neon ring. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed,
gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI
Alexa, anamorphic lens, no text, no logos, no crests.
```
**A4** · последний кадр A3 → K4 · 7 с · Fly Through + Arc Left
```
The camera glides just over a wide concrete stair bridge inside a stadium concourse at dusk, past a lit pedestal with a
tall golden trophy, passes through a tall
arched opening and enters a round multi-level atrium, then makes a slow arc to the left along the upper black railing,
keeping the center of the atrium in view. A row of football shirts on mannequins in plain club colors passes in the
foreground with gentle parallax, the cyan-green neon ring softly breathes, white ribbon sculptures glow under the
ceiling, the continuous curved LED screen below the railing stays blank dark navy. It ends facing a dark doorway with
soft cyan light. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle
ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no logos, no badges.
```
**A5** · последний кадр A4 → K5 · 7 с · Dolly In + Pan Right
```
The camera flies through a dark doorway with soft cyan light into an analytics war room under the stands of a
fictional football stadium at dusk. It moves along a long glowing tactical table with a miniature green pitch etched
in light, small points of light drift across it like simulated passes. On the left, a wall of nine large blank
screens glows empty dark navy with thin cyan edges, nothing displayed. On the right, a tall glass wall overlooks the
floodlit pitch and full stands below. Ahead, the opening of a spiral concrete ramp with a cyan handrail. Warm desk
lamps, faint haze. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle
ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no numbers, no logos.
```
**A6** · последний кадр A5 → M3 · 7 с · Spiral / Corkscrew down (или Crane Down + Pan)
```
The camera leaves the analytics room and descends a wide spiral concrete ramp with a glowing cyan handrail, circling
down two levels inside the stadium at dusk, warm gold wall lights sliding past. At the bottom it glides along a short
service corridor with raw concrete walls, turns smoothly to the right and settles at the entrance of a straight
symmetrical players' tunnel, perfectly centered at 1.5 m, facing rows of white oval ceiling lights, blank club-colored
wall panels and a bright opening to the pitch far ahead. Glossy reflective floor, light haze. One continuous unbroken
shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no
morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```
**A7** · последний кадр A6 (= M3) → K7 · 8 с · Dolly In (по центру)
```
Slow steady push through a straight symmetrical players' tunnel of a fictional football stadium at dusk, camera at
1.5 m, perfectly centered. Rows of white glowing oval ceiling panels pass overhead; both walls are lined with tall
blank panels framed in solid club colors, softly uplit with warm gold light from below; the glossy dark red-brown
floor reflects every light, cold cyan accents at the floor edges. At the end, steps rise toward a bright opening; the
camera climbs the steps and stops at the top, revealing the floodlit green pitch, full stands and a match in progress
under a dusk sky. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle
ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no logos, no faces on the panels.
```
**A8** · последний кадр A7 → M4 · 6 с · Dolly In + легкий Pan Left
```
The camera emerges from the players' tunnel onto the edge of the floodlit pitch of a colossal fictional open-air
stadium at dusk, drops to about 1 m above the grass and glides a short distance along the touchline, turning gently
to look along the pitch. A match is in progress in the mid-distance, small sharp players with no recognizable faces,
full three-tier stands rise on both sides, the roof ring with floodlights and a cyan LED band frames a huge open dusk
sky, blank dark pitch-side boards. Grass blades catch the gold light, light haze in the beams. One continuous unbroken
shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no
morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**A9** · последний кадр A8 (= M4) → K9 · 8 с · Crane Up + Arc Right
```
From 1 m above the touchline the camera rises smoothly to about 35 m while turning to the right, tilting down to
reveal the whole match on the bright green pitch and the entire full three-tier stadium around it, a sea of tiny
people with no visible faces, all under a huge open dusk sky with pink-orange clouds seen through the wide open center
of the ring roof. Floodlights glow gold, the cyan LED band runs along the roof edge, the crowd ripples as tiny lights.
The camera stays inside the bowl, below the roof edge. One continuous unbroken shot from a stabilized cinema drone,
slow constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture.
Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**A10** · последний кадр A9 → K10 · 10 с · Orbit / 360 Orbit (половина круга), медленно
```
The camera makes a slow wide orbit inside the bowl of a colossal fictional open-air football stadium at dusk, rising
to the height of the upper tier just below the roof edge and circling half way around the pitch while always looking
at its center. A match is in progress below with tiny players, full three-tier stands sweep past in the foreground
with gentle parallax, the floodlight ring and cyan LED band slide overhead, pink-orange clouds drift in the open sky
above the pitch, city lights appear and disappear beyond the rim. The camera never leaves the bowl. One continuous
unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no
shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```
**A11** · последний кадр A10 → M5 · 10 с · Orbit (вторая половина) → Static
```
The camera continues its slow orbit inside the bowl of the fictional open-air stadium at dusk, at upper-tier height
below the roof edge, completing the circle around the pitch, then gradually slows down and settles into a still,
high angled view: the floodlit pitch diagonal in the lower-left third with a match in progress, full stands curving
around it, the edge of the near upper tier in the lower right, dramatic pink-orange mammatus clouds and deep blue sky
through the open roof. The final second is almost motionless while the game goes on. One continuous unbroken shot from
a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of
the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no scoreboard.
```
Если облёт A10+A11 «съедает» стадион (модель меняет трибуны), разбить на 3 ролика по 120° через промежуточный кадр
«вид сбоку на поле с верхнего яруса, противоположная сторона».

---

## 5. Маршрут НАЗАД (прокрутка вверх): B1–B8 — другой путь и ракурс

Те же места, но камера летит **иначе**: туннель — под потолком и чуть вбок; аналитика — вдоль стеклянной стены с видом
на поле; атриум — снизу вверх (вертикальный подъём по центру); холл — под балками, над баннерами; выход — через верхний
проём фасада, а не через двери; затем разворот в небе и возврат к ракурсу M1.

| № | Start | End | Что видно | Раздел сайта поверх | Длит. | Скорость |
|---|---|---|---|---|---|---|
| B1 | M5 | KB1 | из финальной точки пике вниз через трибуны, над газоном к выходу из туннеля, лицом к проёму | финал → «Подписаться» | 8 с | медл. |
| B2 | = посл. B1 | KB2 | туннель вглубь, камера под самым потолком, левее оси; панели клубов под углом | «Честные итоги» | 8 с | шаг |
| B3 | = посл. B2 | KB3 | подъём по винтовой рампе, вдоль стеклянной стены аналитики (видно поле), к выходу в атриум | «Как думает модель» | 8 с | шаг |
| B4 | = посл. B3 | KB4 | нижний этаж круглого атриума, камера смотрит вверх на кольца, футболки, LED-экран | «Сила команд» | 6 с | шаг |
| B5 | = посл. B4 | KB5 | вертикальный подъём по центру атриума, выход под балки главного холла | «Лиги и клубы» | 7 с | шаг |
| B6 | = посл. B5 | KB6 | полёт под балками над баннерами к фасаду, вылет сквозь верхний проём решётки над площадью | «Лиги и клубы» → «Сегодня в эфире» | 8 с | шаг → медл. |
| B7 | = посл. B6 | KB7 | над площадью к городу, подъём и разворот на 180° к стадиону | «Сегодня в эфире» | 8 с | медл. |
| B8 | = посл. B7 | M1 | подъём на 180 м и дуга к ракурсу первого экрана | первый экран «Прогноз дня» | 8 с | медл. → покой |

Итого назад ≈ 61 с видео. Через ~2 с покоя на M1 включается петля L0 (кадр тот же).

### Ключевые кадры назад (Image, 16:9, Reference — мастер-кадр той же локации)
**KB1** (конец B1, Reference M4 и K7)
```
Low camera at 2.5 m height on the pitch side of a colossal fictional open-air football stadium at dusk, slightly off
axis to the right, facing the players' tunnel mouth in the lower stand: a wide dark opening with steps going down and
a row of white oval ceiling lights receding inside, warm gold uplight on club-colored blank wall panels just visible
within. Around the opening: the first rows of the full stands with tiny people and no visible faces, blank dark
pitch-side boards, bright green grass #2ee59d in the foreground, floodlight glow #ffc93c and light haze, cyan accent
#3ee0ff. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**KB2** (конец B2, Reference M3)
```
Inner end of a straight players' tunnel in a colossal fictional football stadium at dusk, camera high just under the
ceiling and left of the center line, looking slightly down and ahead at the bottom of a wide spiral concrete ramp going
up with a glowing cyan handrail #3ee0ff. Behind the camera's view the tunnel continues with white oval ceiling panels
and tall blank wall panels framed in club colors uplit with warm gold #ffc93c, glossy dark red-brown floor with
reflections, deep blue shadows #071225, light haze. No people. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa,
anamorphic lens, no text, no logos.
```
**KB3** (конец B3, Reference K5)
```
Inside a dark analytics war room under the stands of a colossal fictional football stadium at dusk, camera at 2 m
height right next to a tall glass wall, looking along the glass toward the far doorway glowing with a cyan-green neon
light of a round atrium. Through the glass on the left: the floodlit green pitch #2ee59d with a match in progress and
full stands below a dusk sky. On the right: a long glowing tactical table with a miniature pitch etched in light and a
wall of blank screens glowing dark navy #071225 with thin cyan edges #3ee0ff. Warm gold desk lamps #ffc93c, light haze.
No people. Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no numbers, no charts, no logos.
```
**KB4** (конец B4, Reference K4)
```
Ground floor of a round multi-level atrium inside a colossal fictional football stadium at dusk, camera at 2 m height
in the center, tilted 50 degrees up, looking up through the stacked circular levels: a continuous curved blank LED
screen glowing dark navy #071225 around the railing above, a ring of football shirts on mannequins in plain club
colors with no badges or sponsors, a cyan-green neon ring #3ee0ff #2ee59d, white curved ribbon sculptures and
spotlights under the ceiling, warm gold light #ffc93c. Dark polished floor at the bottom edge. No people. Photorealistic,
ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no numbers.
```
**KB5** (конец B5, Reference M2)
```
High inside the main concourse of a colossal fictional football stadium at dusk, camera at 18 m height just under the
slanted concrete beams of the stands, looking down the length of the five-storey atrium toward the glowing white-gold
lattice facade at the far end. Below the camera: long plain fabric banners in solid club colors (red, sky blue, white,
navy, claret, yellow, black-white, red-black) hanging at different heights, balconies with dark railings on massive
columns, stair bridges, a row of illuminated glass display cases with silver and gold trophies glowing on the warm
matte floor far below, tiny distant silhouettes. Warm sunset stripes of light
#ffc93c through the lattice, cold cyan edge light #3ee0ff, deep blue shadows #071225. Photorealistic, cinematic film
still, ARRI Alexa, anamorphic lens, no text, no logos, no crests.
```
**KB6** (конец B6, Reference K1)
```
Camera floating at 25 m height just outside the white-gold geometric lattice facade of a colossal fictional football
stadium at dusk, having just flown out through a high opening in the lattice, looking forward and down over a wide
palm-lined plaza with warm lamps and tiny people toward avenues with car light trails, city lights and desert beyond.
The edge of the glowing lattice frames the top and sides of the frame. Dusk just after sunset, deep blue sky #071225
with a warm orange-pink horizon, warm gold light #ffc93c, cyan accents #3ee0ff. Photorealistic, cinematic film still,
ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**KB7** (конец B7, Reference M1)
```
Aerial view from about 110 m of a colossal fictional open-air football stadium at dusk, seen from the plaza side at a
low three-quarter angle, camera tilted 30 degrees down: the white-gold lattice facade and tall glowing main entrance
in the foreground, palm-lined plaza below, the ring-shaped roof with floodlights and a thin cyan LED band #3ee0ff, the
glowing bowl with a bright green pitch #2ee59d and a match in progress partly visible through the open roof. City lights
and car light trails at the edges. Deep blue sky #071225 with a warm orange-pink horizon, gold light #ffc93c.
Photorealistic, ultra sharp, highly detailed 4K cinematic film still, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```

### Видео назад
**B1** · M5 → KB1 · 8 с · Crane Down + FPV dive (плавно)
```
From the high still view inside the bowl of a colossal fictional open-air stadium at dusk, the camera tips forward and
glides down across the full stands in a long smooth descent, the pink-orange clouds and roof ring sliding up out of
view, the crowd as tiny lights rushing past below. It levels out 2.5 m above the bright green pitch while the match
continues in the distance, curves toward the lower stand and slows down facing the dark mouth of the players' tunnel
with white oval lights receding inside. One continuous unbroken shot from a stabilized cinema drone, slow constant
gliding speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic,
cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no advertising.
```
**B2** · последний кадр B1 → KB2 · 8 с · Fly Through + Crane Up
```
The camera flies from the pitch into the players' tunnel and down the steps, then rises to fly just under the ceiling
and slightly left of the center line, so the white glowing oval ceiling panels pass very close above and the tall
club-colored blank wall panels are seen at a steep angle, uplit with warm gold light; the glossy red-brown floor far
below reflects every light. At the inner end the camera tilts down toward the foot of a spiral concrete ramp with a
glowing cyan handrail. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle
ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no logos, no faces on the panels.
```
**B3** · последний кадр B2 → KB3 · 8 с · Spiral Up + Dolly In
```
The camera climbs a wide spiral concrete ramp with a glowing cyan handrail, circling up two levels inside a stadium at
dusk, then enters a dark analytics war room and glides right along a tall glass wall: through the glass the floodlit
green pitch with a match in progress and full stands under a dusk sky slide past on the left, on the right a long
glowing tactical table and a wall of blank dark navy screens with thin cyan edges. Ahead, a doorway glows cyan-green.
Warm desk lamps, faint haze. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed,
gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no numbers, no logos.
```
**B4** · последний кадр B3 → KB4 · 6 с · Dolly In + Tilt Up
```
The camera passes through a cyan-glowing doorway and drops gently to the ground floor of a round multi-level atrium
inside a stadium at dusk, gliding to its center and tilting up: the stacked circular levels open above, a continuous
curved blank LED screen glowing dark navy around the railing, a ring of football shirts on mannequins in plain club
colors, the cyan-green neon ring softly breathing, white ribbon sculptures and spotlights under the ceiling. Warm gold
light, dark polished floor. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed,
gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa,
anamorphic lens, no text, no logos, no badges.
```
**B5** · последний кадр B4 → KB5 · 7 с · Crane Up (вертикально) + Tilt Down
```
From the center of the round atrium the camera rises straight up through the stacked circular levels, the ring of
football shirts, the blank curved LED screen and the cyan-green neon ring sliding down past it, then at the top drifts
sideways through a high opening into the main concourse and tilts down, floating just under the slanted concrete beams
and looking down the length of a five-storey atrium over long plain banners in club colors toward the glowing lattice
facade. Warm sunset stripes, cyan edge light. One continuous unbroken shot from a stabilized cinema drone, slow
constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture.
Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos, no crests.
```
**B6** · последний кадр B5 → KB6 · 8 с · Fly Through (Through Object Out)
```
The camera glides high under the slanted concrete beams of a vast stadium concourse at dusk, passing over the tops of
long plain banners in solid club colors that sway gently below with strong parallax, balconies, stair bridges
and lit trophy display cases far below sliding past. Warm sunset light streams in through the white-gold geometric lattice facade ahead; the
camera flies out through a high opening in the lattice into the open air and floats 25 m above the palm-lined plaza,
looking toward the city lights. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding
speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic,
ARRI Alexa, anamorphic lens, no text, no logos, no crests.
```
**B7** · последний кадр B6 → KB7 · 8 с · Crane Up + Arc 180° (Aerial pullback)
```
Floating above the palm-lined plaza at dusk, the drone drifts forward toward the city lights, then rises and makes a
smooth wide 180 degree turn back toward the stadium, climbing to about 110 m. The colossal fictional open-air stadium
comes into view at a low three-quarter angle: white-gold lattice facade, tall glowing main entrance, the ring roof with
floodlights and a cyan LED band, the glowing bowl with a match in progress. Car light trails flow, deep blue dusk sky
with a warm orange horizon. One continuous unbroken shot from a stabilized cinema drone, slow constant gliding speed,
gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture. Photorealistic, cinematic, ARRI
Alexa, anamorphic lens, no text, no logos, no advertising.
```
**B8** · последний кадр B7 → M1 · 8 с · Crane Up + Arc Left, в конце почти стоп
```
The drone climbs from 110 m to about 180 m while arcing slowly to the left around a colossal fictional open-air
three-tier football stadium at dusk and tilting further down, until the whole glowing bowl fills 85-90 percent of the
frame at a 40-45 degree downward angle: full stands as tiny warm dots, the bright green pitch with a match in progress,
the ring roof with floodlights and a cyan LED band, the main entrance and palm plaza at the lower right, city lights
at the edges. The last second slows to an almost still hover. One continuous unbroken shot from a stabilized cinema
drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no shake, no morphing of the architecture.
Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```

---

## 6. Петли

**L0 — кружение снаружи** · Start = End = **M1** · 10 с · Orbit (медленно)
Тот же кадр M1 — начало A1 и конец B8, поэтому вход и выход из петли без шва.
```
Slow, steady drone orbit around a colossal fictional open-air three-tier football stadium at dusk, the camera keeps a
40-45 degree downward tilt and a constant 180 m altitude, the glowing bowl stays centered and fills the frame for the
whole shot. The camera arcs gently about 20 degrees to the right and smoothly drifts back, ending on exactly the first
frame for a seamless loop. Inside the bowl a match is in progress, tiny players run, crowd lights twinkle, the cyan
LED band on the roof edge softly pulses, car light trails flow in the city streets, faint haze drifts. One continuous
unbroken shot from a stabilized cinema drone, slow constant gliding speed, gentle ease-in and ease-out, no cuts, no
shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```
На сайте играет на скорости ×0,5 — дуга «туда-обратно» читается как парение и кружение.
**Улучшение (по желанию, +3 ролика):** настоящий круг 360° из 4 роликов по 90° (L0a: M1 → M1+90°, L0b, L0c, L0d → M1;
кадры +90/+180/+270° — с Reference M1, «тот же стадион с другой стороны»). При начале прокрутки код доигрывает круг
ускоренно до M1 (до 1 с, с размытием движения) и переходит в A1.

**L1 — финальная точка** · Start = End = **M5** · 10 с · Static (минимальный дрейф)
Тот же кадр M5 — конец A11 и начало B1.
```
Locked-off, almost static wide shot from high inside the bowl of a colossal fictional open-air football stadium at
dusk, at upper-tier height just below the roof edge, with a barely noticeable slow drift forward and back so the last
frame matches the first for a seamless loop. Dramatic pink-orange mammatus clouds drift slowly through the open roof
center, light on them shifts gently. Below, the floodlit green pitch lies diagonally in the lower-left third, a match
in progress with tiny players running, the crowd ripples as tiny lights, city lights twinkle on the horizon, the cyan
LED band on the roof edge softly pulses. One continuous unbroken shot from a stabilized cinema drone, no cuts, no
shake, no morphing of the architecture. Photorealistic, cinematic, ARRI Alexa, anamorphic lens, no text, no logos.
```
Игроки в начале и конце петли могут стоять по-разному — команда сглаживает последние 0,5 с наплывом в первый кадр
(игроки мелкие, шва не видно).

---

## 7. Гербы клубов: два пути
Нейросети гербы искажают, в движении «плывут», иногда отказывают (товарные знаки).

**Путь 1 (основной, надёжный):** в мастер-кадрах холла (M2, K3, KB5) и туннеля (M3, K7, KB2) — **пустые панели и
баннеры в цветах клубов** (так уже написано в промптах). Гербы кладёт команда кодом 3D-слоями поверх видео (эмблемы —
`render/emblems/`): они точные, двигаются с параллаксом по треку камеры и нажимаются (герб → страница клуба/лиги).

**Путь 2 (гербы «в кадре»):** владелец кладёт настоящие гербы на пустые панели **в ключевых кадрах** через
редактирование картинки (Nano Banana edit), и уже из отредактированных кадров делает видео. Промпт правки (герб —
приложить картинкой):
```
Place the attached club crest onto the blank [red] panel on the [left] wall, [third] panel from the camera, centered,
matching the panel's perspective, the warm gold uplight and the matte surface texture, slightly embossed like a metal
plaque. Keep everything else in the image exactly unchanged.
```
По одному гербу за правку; 4–6 гербов на кадр максимум (остальные панели — пустые, туда гербы добавит код).
Риск: в видео между Start и End гербы на ближних панелях могут поплыть — тогда эти места команда закроет слоем кодом.

**19 клубов и цвета панелей / баннеров / футболок**
| Клуб | Цвета |
|---|---|
| Ливерпуль | красный |
| Манчестер Сити | небесно-голубой, белый |
| Манчестер Юнайтед | красный, чёрный кант |
| Арсенал | красный с белым |
| Челси | синий |
| Реал Мадрид | белый, золото |
| Барселона | гранатовый и синий полосами |
| Атлетико Мадрид | красно-белые полосы, синий |
| Бавария | красный, белый |
| Боруссия Дортмунд | жёлтый, чёрный |
| ПСЖ | тёмно-синий с красной полосой |
| Ювентус | чёрно-белые полосы |
| Интер | сине-чёрные полосы |
| Милан | красно-чёрные полосы |
| Наполи | голубой |
| Рома | бордо, оранжевый |
| Бенфика | красный |
| Порту | сине-белые полосы |
| Спортинг | зелёно-белые горизонтальные полосы |

В промпт все 19 модель не уложит — даём набор цветов; если цвета однообразные, генерировать 2–3 варианта и выбирать.

---

## 8. Что сделает команда
| Шаг | Что делаем | Как |
|---|---|---|
| Склейка | A1…A11 → `forward.mp4`, B1…B8 → `back.mp4`, L0, L1 — отдельно; без наплывов | ffmpeg concat; на каждом стыке убрать 2–4 повторных/«дёрнутых» кадра (последние кадры ролика N или первые N+1) |
| Скорость | Ровная скорость камеры через стыки | ретайм с интерполяцией кадров (RIFE / minterpolate) на 0,3–0,5 с вокруг стыка; ease, если модель ускорилась |
| Цвет | Один «облик» по всему файлу | эталон — M1 и M5; подгонка баланса и контраста каждого ролика к соседям (DaVinci / LUT), deflicker |
| Чистка | Следы букв, лишние лица, логотипы | ретушь масками; при необходимости — замена кусков на соседние кадры |
| Кодирование для прокрутки | Каждый кадр — ключевой (all-intra), иначе прокрутка тормозит | H.264 `-g 1`, 1080p 24 к/с для ПК; 720p 15–20 к/с для телефона; запасной путь — последовательность кадров WebP на canvas |
| Прокрутка ↔ время видео | Каждому разделу сайта — свой участок прокрутки и свой участок времени в `forward` и в `back` | раздел s, прогресс p (0…1): вниз — `t = A_нач[s] + p·A_длит[s]`; вверх — `t = B_нач[s] + (1 − p)·B_длит[s]`; сглаживание (lerp) ~0,1 с |
| Смена направления | Пользователь крутил вниз и пошёл вверх (или наоборот) | **у каждой точки A есть точка B той же локации** (таблица ниже): по (s, p) берём время в другом файле, 0,3 с — «разворот камеры» кодом: размытие движения по горизонтали + лёгкий сдвиг и наплыв A→B. Читается как быстрый поворот дрона на месте |
| Простой | Прокрутки нет 2 с | вверху (кадр M1) — включается L0, кадр совпадает, без наплыва; внизу (M5) — L1 играет всегда; в середине — кадр стоит, лёгкий дрейф кодом (масштаб 1,00→1,02) |
| Цикл | Конец `back` = M1 = начало L0 = начало `forward` | бесконечно, без шва |
| Телефон / «меньше движения» | Экономия и доступность | постеры + короткие петли по разделам, переходы наплывом, без прокрутки видео |

**Карта «A ↔ B» (одна локация — два ракурса):**
| Локация | Разделы | Участок в `forward` | Участок в `back` |
|---|---|---|---|
| Снаружи, воздух | «Прогноз дня» | A1 | B8 |
| Площадь и вход | «Сегодня в эфире» | A2 | B7 + конец B6 |
| Главный холл | «Лиги и клубы» | A3 | начало B6 + конец B5 |
| Зал клубов (атриум) | «Сила команд» | A4 | начало B5 + B4 |
| Аналитика и рампа | «Как думает модель» | A5 + A6 | B3 |
| Туннель | «Честные итоги» | A7 | B2 |
| Поле | «Подписаться» | A8 + A9 | конец B1 |
| Чаша, финал | FAQ, финал, «ПРОГНОЗЫ НА ХОККЕЙ» | A10 + A11 | начало B1 |
Длина участков разная — сайт приводит их к одной высоте раздела (p от 0 до 1 в каждом).

**Наши слои поверх (не в генерации):** гербы, данные на LED-экране и экранах аналитики, карточки итогов на панелях
туннеля, текст, объёмные плашки, кнопка «ПРОГНОЗЫ НА ХОККЕЙ» — кодом, в спокойных зонах кадра (небо, пол, тёмный верх).

---

## 9. Запреты (во всех промптах и при приёмке)
- Реальные игроки и лица крупным планом; узнаваемые люди, знаменитости. Игроки и болельщики — мелко, без лиц.
- Бренды, спонсоры, реклама на бортах, табло с картинкой, логотипы лиг и клубов в генерации (гербы — только путь 2 / кодом).
- Узнаваемые реальные стадионы (Камп Ноу, Бернабеу и др.) — референсы только по ракурсу и настроению.
- Любые надписи, буквы, цифры, номера на футболках.
- Смена времени суток (день, чёрная ночь), смена стадиона между роликами, склейки и резкие рывки внутри ролика.
- Правила канала остаются: без БК, промокодов, гарантий, выдуманных цифр (`team/RULES.md`).

**Счёт работы:** картинок — 5 мастер + 7 ключевых вперёд + 7 назад = 19; роликов — A 11 + B 8 + L0 + L1 = **21**
(с полным кругом L0 — 24).
