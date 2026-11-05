from _parts import *
h=HEAD%dict(title='JARVIS: прогнозы на хоккей и футбол по собственной модели',desc='Прогнозы на хоккей и футбол — по расчёту, а не наугад. Вероятность модели рядом с реальной линией.',a_h='')
h+='''<main id="main">
<section class="stage" data-beam data-beam-scroll>
 <div class="giant" aria-hidden="true">ШАНСЫ</div>
 <div class="wrap">
 <div class="hero-enter">
  <h1>Прогнозы на хоккей и футбол — по расчёту, а не <em class="it">наугад</em></h1>
  <p class="lead">На каждый матч КХЛ, НХЛ и топ-лиг Европы: вероятность нашей модели рядом с реальной линией. Для тех, кто смотрит матч дня и хочет знать шансы заранее.</p>
  <ul class="chips"><li class="chip">Собственная модель, не чужие скриншоты</li><li class="chip">Линия с источником указана</li><li class="chip">Без VIP и промокодов</li></ul>
  <div class="cta"><a class="btn" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a><a class="btn ghost" href="#model">Как считает модель</a></div>
 </div>
 <div class="hs">
  <div class="sphere" aria-hidden="true" data-depth="10"></div>
  <div class="ribs" aria-hidden="true" data-depth="-16"></div>
  <img class="obj e1" data-depth="26" src="../../assets/em/avangard.webp" alt="" width="210" height="210">
  <img class="obj e2" data-depth="34" src="../../assets/em/cska.webp" alt="" width="210" height="210">
  <span class="obj puck pk" aria-hidden="true" data-depth="46"></span>
  <div class="slab tablo-slab" aria-label="Табло матча дня"><div class="tilt-in"><div class="plate" style="padding:10px"><div class="cut tablo" id="tablo" data-vt>
   <div class="tablo-top"><span>КХЛ, матч дня</span><span>16:30 МСК</span></div>
   <div class="tablo-teams"><div class="tm"><img class="vt-h" src="../../assets/em/avangard.webp" alt="" width="88" height="88"><b>Авангард</b></div><span class="vs" aria-hidden="true">—</span><div class="tm"><img class="vt-a" src="../../assets/em/cska.webp" alt="" width="88" height="88"><b>ЦСКА</b></div></div>
   <div class="nums"><div><small>П1</small><output>39</output></div><div><small>Х</small><output>22</output></div><div><small>П2</small><output>40</output></div></div>
  </div></div></div></div>
 </div></div>
</section>
<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec" id="today" data-beam><div class="wrap">
 <div class="sh"><span class="tag">Хоккей, ближайшие матчи</span><h2>Ближайшие матчи</h2><p>Нажми на плиту — откроется расчёт. Наведи курсор: плита наклонится, а иней растает.</p></div>
 <div class="grid3" id="next"><noscript><p class="muted">Матчи подгружаются скриптом. Без него смотрите прогнозы в Telegram.</p></noscript></div>
 <p class="note" style="margin-top:28px">Время московское. Кэфы П1 / Х / П2 — основное время. Вероятность — самый вероятный исход по модели JARVIS. Кэфы — справка, не рекомендация. Это аналитика, не гарантия.</p>
</div></section>

<div class="wrap"><div class="blue" aria-hidden="true"></div></div>

<section class="sec" id="doubts"><div class="wrap">
 <div class="sh"><h2>Частые сомнения</h2><p>Четыре вопроса, которые задают чаще всего. Отвечаем прямо.</p></div>
 <div class="bento">
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Это бесплатно?</h3><p>Да. Канал @jarvibet бесплатный, прогнозы выходят до начала матча. Без VIP, без предоплаты, без «верняков».</p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Почему верить?</h3><p>Верить на слово не нужно: собственная модель, а не чужие скриншоты. У каждого прогноза вероятность модели и линия рынка, время публикации указано. Блок «Итоги» на сайте скоро. <a href="#model">Как считает модель</a></p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>Чем вы отличаетесь?</h3><p>Мы считаем, а не угадываем: объясняем, откуда цифра, а не просто «ставь». На каждый матч вероятность модели и реальная линия. Без промокодов и рекламы букмекеров.</p></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate qa blur"><h3>А если не сработает?</h3><p>Гарантий нет: прогноз — оценка вероятности, и у любой модели бывают плохие серии. Поэтому цифры и линия всегда рядом, а решать вам.</p></div></div></div>
 </div>
</div></section>

<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec" id="model" data-beam><div class="wrap">
 <div class="sh"><h2>Как думает модель</h2><p>До матча модель разыгрывает его тысячи раз. Ставка — только там, где расчёт и линия сходятся.</p></div>
'''+STEPS%dict(s1='Последние игры, сила атаки и обороны, место в таблице.',s3='Самое вероятное событие в коридоре кэфов 1,6–2,3. В футболе — от 60 % по модели.')+'''
</div></section>

<div class="wrap"><div class="blue" aria-hidden="true"></div></div>

<section class="sec" id="results"><div class="wrap">
 <div class="sh"><h2>Честные итоги</h2><p>Каждое утро в канале — итоги вчерашних матчей, и зашедшие, и нет. У каждого прогноза номер поста: любой можно проверить.</p></div>
 <div class="slab" data-r><div class="tilt-in"><div class="plate soon"><span class="puck">?</span><div><h3>Скоро</h3><p>Сводку по месяцам и таблицу всех прогнозов выложим здесь, когда накопится проверяемая история. Пока итоги дня — в Telegram.</p></div></div></div></div>
 <p style="margin-top:22px"><a class="btn ghost" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a></p>
</div></section>
'''+TG+FAQ+'</main>\n'+FOOT
open('index.html','w').write(h)
