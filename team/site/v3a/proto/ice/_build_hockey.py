from _parts import *
h=HEAD%dict(title='Хоккей: матчи КХЛ и НХЛ и прогнозы модели | JARVIS',desc='Хоккей: КХЛ и НХЛ. Прогноз на каждый матч от собственной модели. Бесплатно, без VIP.',a_h=' aria-current="page"')
h+='''<div class="ticker" id="ticker" aria-label="Матчи дня"><noscript><span><b>Матчи дня</b> подгружаются скриптом</span></noscript></div>
<main id="main">
<section class="stage" data-beam data-beam-scroll>
 <div class="giant" aria-hidden="true">ЛЁД</div>
 <div class="wrap">
 <div class="hero-enter">
  <h1>Хоккей: КХЛ и <em class="it">НХЛ</em></h1>
  <p class="lead">Прогноз на каждый матч от собственной модели. КХЛ днём, НХЛ ночью по Москве. Бесплатно, без VIP.</p>
  <div class="cta"><a class="btn" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a></div>
  <div class="stats" id="stats">
   <div class="stat cut"><output data-count="0">0</output><small>матчей в ближайшие дни</small></div>
   <div class="stat cut"><output data-count="0">0</output><small>с линией и расчётом модели</small></div>
   <div class="stat cut"><output data-count="2">2</output><small>лиги</small></div>
  </div>
  <div class="lgrow"><img src="../../assets/lg/khl.webp" alt="КХЛ" width="34" height="34"><img src="../../assets/lg/nhl.webp" alt="НХЛ" width="34" height="34"></div>
 </div>
 <div class="hs">
  <div class="sphere" aria-hidden="true" data-depth="10"></div>
  <div class="ribs" aria-hidden="true" data-depth="-16"></div>
  <img class="obj e1" data-depth="26" src="../../assets/em/avangard.webp" alt="" width="210" height="210">
  <img class="obj e2" data-depth="34" src="../../assets/em/cska.webp" alt="" width="210" height="210">
  <span class="obj puck hp" aria-hidden="true" data-depth="46"></span>
  <div class="slab tablo-slab" aria-label="Матч дня"><div class="tilt-in"><div class="plate" style="padding:10px"><div class="cut tablo" id="tablo" data-vt>
   <div class="tablo-top"><span>КХЛ, матч дня</span><span>16:30 МСК</span></div>
   <div class="tablo-teams"><div class="tm"><img class="vt-h" src="../../assets/em/avangard.webp" alt="" width="88" height="88"><b>Авангард</b></div><span class="vs" aria-hidden="true">—</span><div class="tm"><img class="vt-a" src="../../assets/em/cska.webp" alt="" width="88" height="88"><b>ЦСКА</b></div></div>
   <div class="nums"><div><small>П1</small><output>39</output></div><div><small>Х</small><output>22</output></div><div><small>П2</small><output>40</output></div></div>
  </div></div></div></div>
 </div></div>
</section>
<div class="wrap"><p class="note" style="margin-top:6px">Прогноз дня: посты с прогнозами выходят в канале — КХЛ до 08:00 МСК, НХЛ до 14:00. <a href="https://t.me/jarvibet" style="color:var(--blue);font-weight:700">Получать прогнозы — бесплатно</a></p></div>
<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec" id="today" data-beam><div class="wrap">
 <div class="period"><b>1-й период</b><time>20:00</time></div>
 <div class="sh"><h2>Сегодня на льду</h2><p>Матчи дня КХЛ и НХЛ. Нажми на карточку: она перевернётся и покажет, почему модель так думает, и кэфы.</p></div>
 <div class="tabs cut" id="daytabs" role="tablist" aria-label="День и лига"></div>
 <div class="deck" id="deck"><noscript><p class="muted">Матчи подгружаются скриптом. Без него смотрите прогнозы в Telegram.</p></noscript></div>
 <p class="note" style="margin-top:26px">Кэфы — справка, не рекомендация. Время московское. Это вероятности модели, а не гарантия исхода.</p>
</div></section>

<div class="wrap"><div class="blue" aria-hidden="true"></div></div>

<section class="sec" id="leagues"><div class="wrap">
 <div class="period"><b>2-й период</b><time>20:00</time></div>
 <div class="sh"><h2>Лиги и клубы</h2><p>Две лиги, одна модель. КХЛ — днём и вечером, НХЛ — ночью: ночные матчи собраны в один игровой день.</p></div>
 <div class="two">
  <div class="slab" data-r><div class="tilt-in"><div class="plate lg blur"><div class="lg-h"><img src="../../assets/lg/khl.webp" alt="" width="60" height="60"><h3>КХЛ</h3></div><p>Матчи днём и вечером по Москве. Расчёт модели и кэфы — на каждую игру.</p><div class="emrow" aria-label="Клубы КХЛ в матчах дня">
   <a href="match.html" aria-label="Авангард"><img src="../../assets/em/avangard.webp" alt="" loading="lazy"></a><a href="hockey.html#khl_2026-11-05_metallurg_neftekhimik" aria-label="Металлург"><img src="../../assets/em/metallurg.webp" alt="" loading="lazy"></a><a href="match.html" aria-label="ЦСКА"><img src="../../assets/em/cska.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Нефтехимик"><img src="../../assets/em/neftekhimik.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Динамо Москва"><img src="../../assets/em/dinamo_msk.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Сочи"><img src="../../assets/em/sochi.webp" alt="" loading="lazy"></a></div></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate lg blur"><div class="lg-h"><img src="../../assets/lg/nhl.webp" alt="" width="60" height="60"><h3>НХЛ</h3></div><p>Ночные матчи по Москве собраны в один игровой день.</p><div class="emrow" aria-label="Клубы НХЛ в матчах дня">
   <a href="hockey.html" aria-label="Лос-Анджелес"><img src="../../assets/em/nhl_lak.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Сан-Хосе"><img src="../../assets/em/nhl_sjs.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Сиэтл"><img src="../../assets/em/nhl_sea.webp" alt="" loading="lazy"></a><a href="hockey.html" aria-label="Калгари"><img src="../../assets/em/nhl_cgy.webp" alt="" loading="lazy"></a></div></div></div></div>
 </div>
 <p class="note" style="margin-top:18px">Эмблемы — собственность клубов, показаны для навигации.</p>
</div></section>

<section class="sec" id="sheet"><div class="wrap">
 <div class="slab" data-r><div class="tilt-in"><div class="plate sheet" id="sheets">
  <div><span class="tag b">Для тех, кто считает сам</span><h2 style="margin-top:12px">Аналитическая таблица</h2>
   <ul class="ticks"><li>Все матчи КХЛ и НХЛ в одном месте</li><li>Форма команд, вероятности модели и кэфы</li><li>Обновляется каждый игровой день</li></ul>
   <a class="btn" href="https://t.me/jarvibet">Хочу таблицу</a><p class="note" style="margin-top:12px">Оплата появится скоро. Сейчас доступ — через Telegram.</p></div>
  <div>
   <div class="tabs cut" role="tablist" aria-label="Листы таблицы"><button type="button" role="tab">Эло</button><button type="button" role="tab">Прогнозы</button><button type="button" role="tab">Что заходит</button><button type="button" role="tab">Расписание</button><button type="button" role="tab">История</button><button type="button" role="tab">И ещё</button></div>
   <div class="panel cut" hidden><h4>Рейтинг Эло</h4><p>Сила каждой команды одним числом. Рейтинг пересчитывается после каждого матча: победа над сильным соперником стоит больше, чем над слабым.</p><ul><li>Все команды лиги в одном списке</li><li>Как менялась сила команды за сезон</li><li>Поправка на игру: броски в створ и шайбы сверх ожидания</li></ul><span class="soonb">Скоро: рейтинг появится на сайте, когда подключим его расчёт. В таблице лист уже есть.</span></div>
   <div class="panel cut" hidden><h4>Прогнозы на все матчи</h4><p>Все матчи ближайших дней на одном листе: время по Москве, прогноз модели, коэффициенты и вероятность. После игры рядом появляется счёт.</p><ul><li>КХЛ и НХЛ</li><li>Расчёт модели рядом с линией</li><li>Обновляется каждое утро</li></ul></div>
   <div class="panel cut" hidden><h4>Что заходит у команд</h4><p>Как часто у каждой команды случается то или иное событие за сезон: победа, тотал больше или меньше, игра в овертайм.</p><ul><li>Видно сильные и слабые стороны каждой команды</li><li>Конструктор матча: выбираешь две команды и видишь, что вероятнее в их игре</li></ul><span class="soonb">Скоро: цифры по сезону появятся здесь после подключения данных.</span></div>
   <div class="panel cut" hidden><h4>Расписание и результаты</h4><p>Все матчи сезона с датой и временем по Москве. У сыгранных стоит счёт, отмечены овертаймы и буллиты.</p><ul><li>Сегодня, завтра и вся неделя</li><li>Ночные матчи НХЛ собраны в один игровой день</li></ul></div>
   <div class="panel cut" hidden><h4>История ставок</h4><p>Каждый прогноз остаётся в таблице: зашёл или нет и по какому кэфу. Видно, как часто модель угадывает на дистанции.</p><ul><li>Точность модели по фаворитам и аутсайдерам</li><li>Ничего не удаляется</li></ul><span class="soonb">Скоро: история и итоги по месяцам появятся на сайте после подключения базы итогов. Пока — в канале каждое утро.</span></div>
   <div class="panel cut" hidden><h4>И это только часть</h4><p>Мы показали 5 листов. Всего в таблице их больше 20.</p><ul><li>Коэффициенты: линия на ближайшие матчи и итоги прошлых</li><li>Модель против рынка: чья оценка точнее</li><li>Купон дня и мой купон</li><li>Точность и симуляция на дистанции</li><li>Карточка команды, статистика, ключевые игроки, досье</li></ul><p style="margin-top:8px"><a href="https://t.me/jarvibet" style="color:var(--blue);font-weight:700">Узнать про доступ</a></p></div>
   <div class="pager"><button type="button" id="prev" aria-label="Назад">‹</button><span id="pg">1 / 6</span><button type="button" id="next2" aria-label="Дальше">›</button></div>
  </div>
 </div></div></div>
</div></section>

<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec" id="model" data-beam><div class="wrap">
 <div class="period"><b>3-й период</b><time>20:00</time></div>
 <div class="sh"><h2>Прогноз модели</h2><p>Все матчи КХЛ и НХЛ ближайших дней: вероятности модели рядом с линией. Отметка на шкале — доля линии без маржи.</p></div>
 <div class="legend"><span><i class="mk"></i>граница П1 по линии</span><span><i class="mk" style="background:var(--red)"></i>граница П1 плюс Х по линии</span></div>
 <div class="ptab" id="ptab"><noscript><p class="muted">Таблица подгружается скриптом.</p></noscript></div>
 <p style="margin-top:22px"><a class="btn ghost" href="match.html">Расчёт модели: Авангард — ЦСКА</a></p>
</div></section>

<section class="sec" id="how"><div class="wrap">
 <div class="sh"><h2>Как думает модель</h2><p>Три шага от данных к выбору. Выбор для канала делает человек по правилам ниже, а не сама модель.</p></div>
'''+STEPS%dict(s1='Результаты, сила атаки и обороны, броски в створ и шайбы сверх ожидания, вратарь и два матча за два дня.',s3='Самое вероятное событие в коридоре кэфов 1,6–2,3. Остальные матчи — разбор без выбора.')+'''
 <div class="slab" style="margin-top:46px;max-width:620px" data-r><div class="tilt-in"><div class="plate"><h3 style="font-size:22px;margin-bottom:6px">Почему 1,6–2,3</h3><p class="muted">Ниже — мало смысла рисковать, выше — больше случайности, чем расчёта.</p>
  <div class="scale" style="margin-top:14px"><i class="rail"></i><i class="band"></i><span>1,2</span><span style="left:20%">1,6</span><span style="left:55%">2,3</span><span>3,2</span></div></div></div></div>
</div></section>

<div class="wrap"><div class="blue" aria-hidden="true"></div></div>

<section class="sec" id="results"><div class="wrap">
 <div class="sh"><h2>Честные итоги</h2><p>Каждое утро в канале — итоги вчерашних матчей, и зашедшие, и нет. У каждого прогноза номер поста: любой можно проверить.</p></div>
 <div class="slab" data-r><div class="tilt-in"><div class="plate soon"><span class="puck">?</span><div><h3>Скоро</h3><p>Итоги по месяцам появятся на сайте, когда мы подключим его к базе итогов. Пока цифр здесь нет, чтобы не показывать примерные.</p></div></div></div></div>
 <p style="margin-top:22px"><a class="btn ghost" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a></p>
</div></section>

<section class="sec" id="doubts"><div class="wrap">
 <div class="sh"><h2>Частые сомнения</h2><p>Коротко о главном.</p></div>
 <div class="bento">
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Это бесплатно?</h3><p>Да. Канал @jarvibet бесплатный, прогнозы выходят до начала матча. Без VIP, без предоплаты, без «верняков».</p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Почему верить?</h3><p>Верить на слово не нужно: собственная модель, а не чужие скриншоты. У каждого прогноза вероятность модели и линия рынка, время публикации указано. Блок «Итоги» на сайте скоро. <a href="#how">Как считает модель</a></p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Чем вы отличаетесь?</h3><p>Мы считаем, а не угадываем: объясняем, откуда цифра, а не просто «ставь». На каждый матч вероятность модели и реальная линия. Без промокодов и рекламы букмекеров.</p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>А если не сработает?</h3><p>Гарантий нет: прогноз — оценка вероятности, и у любой модели бывают плохие серии. Поэтому цифры и линия всегда рядом, а решать вам.</p></div></div></div>
 </div>
</div></section>
'''+TG.replace('<section class="sec" data-beam>','<section class="sec">')+'''
<section class="sec" id="faq"><div class="wrap"><div class="sh"><h2>Вопросы</h2><p>Футбол — топ-лиги Европы и Лига чемпионов, та же модель и те же честные итоги. <a href="../../football/index.html" style="color:var(--blue);font-weight:700">Прогнозы на футбол</a></p></div>
 <div class="faq">
  <details><summary>Где посмотреть итоги?</summary><p>Каждое утро в канале и на сайте в разделе «Итоги»: все прогнозы подряд, с номером поста и счётом.</p></details>
  <details><summary>Что такое «ВЫБОР»?</summary><p>Ставка, у которой модель даёт от 60 % при кэфе от 1,6. Остальные матчи — разбор без выбора.</p></details>
  <details><summary>Почему кэф 1,6–2,3?</summary><p>Ниже — мало смысла рисковать, выше — больше случайности, чем расчёта.</p></details>
  <details><summary>Когда выходят прогнозы?</summary><p>КХЛ — до 08:00 по Москве, НХЛ — до 14:00. Ночные матчи НХЛ собраны в один игровой день.</p></details>
 </div></div></section>
</main>
'''+FOOT
open('hockey.html','w').write(h)
