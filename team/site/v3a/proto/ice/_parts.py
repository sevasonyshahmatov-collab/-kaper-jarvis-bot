HEAD='''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="theme-color" content="#eaf3f9">
<link rel="icon" href="../../favicon.svg">
<link rel="stylesheet" href="fonts.css">
<link rel="stylesheet" href="ice.css">
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<div class="scratch" aria-hidden="true"></div>
<header class="nav"><div class="wrap">
 <a class="brand" href="index.html" aria-label="JARVIS, главная"><i></i>JARVIS</a>
 <ul>
  <li><a href="hockey.html"%(a_h)s>Хоккей</a></li>
  <li><a href="../../football/index.html">Футбол</a></li>
  <li><a href="index.html#today">Сегодня</a></li>
  <li><a href="index.html#model">Модель</a></li>
  <li><a href="index.html#results">Итоги</a></li>
  <li><a href="index.html#faq">Вопросы</a></li>
 </ul>
 <nav class="navm" aria-label="Разделы"><a href="hockey.html"%(a_h)s>Хоккей</a><a href="../../football/index.html">Футбол</a></nav>
 <a class="btn sm" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a>
</div></header>
'''
FOOT='''<footer class="foot"><div class="wrap">
 <nav aria-label="Ссылки"><a href="index.html">Главная</a><a href="hockey.html">Хоккей</a><a href="../../football/index.html">Футбол</a><a href="../../model.html">Как считает модель</a><a href="../../glossary.html">Словарь терминов</a><a href="https://t.me/jarvibet">Telegram</a></nav>
 <p class="age">18+. Аналитика, а не призыв делать ставки. Выигрыш не гарантирован.</p>
 <p>Материалы носят информационный характер и не гарантируют результат. Реклама букмекеров на сайте не размещается. Эмблемы клубов — собственность клубов, показаны для навигации. Макет «Белый лёд», прототип v3a, © JARVIS, @jarvibet.</p>
</div></footer>
<script src="../../assets/club/themes.js"></script>
<script src="../../data/today.js"></script>
<script src="../../data/model.js"></script>
<script src="../../data/lines.js"></script>
<script src="ice.js"></script>
</body></html>
'''
FAQ='''<section class="sec" id="faq"><div class="wrap"><div class="sh"><h2>Вопросы</h2></div>
 <div class="faq">
  <details><summary>Где посмотреть итоги?</summary><p>Каждое утро в канале и здесь, в разделе «Итоги»: все прогнозы подряд, с номером поста и счётом матча.</p></details>
  <details><summary>Какие лиги?</summary><p>Хоккей: КХЛ и НХЛ. Футбол: АПЛ, Ла Лига, Серия А, Бундеслига, Лига 1, Португалия и Лига чемпионов.</p></details>
  <details><summary>Что такое «ВЫБОР»?</summary><p>Ставка, у которой модель даёт от 60 %% при кэфе от 1,6. Остальные матчи — разбор без выбора.</p></details>
  <details><summary>Почему кэф 1,6–2,3?</summary><p>Ниже — мало смысла рисковать, выше — больше случайности, чем расчёта.</p></details>
 </div></div></section>
'''.replace('%%','%')
TG='''<section class="sec" data-beam><div class="wrap"><div class="plate tg blur" data-r>
 <div><h2>Все прогнозы&nbsp;— в Telegram</h2><p class="lead muted" style="margin:14px 0 22px;max-width:40ch">Подписка бесплатная. Прогнозы выходят до начала матча.</p><a class="btn" href="https://t.me/jarvibet">Получать прогнозы — бесплатно</a></div>
 <ul><li><b>Посты на каждый матч</b><span>С кэфом и вероятностью по модели.</span></li><li><b>Ролики</b><span>Матчи дня и тренды коротко.</span></li><li><b>Итоги дня</b><span>Все прогнозы подряд. Подписка бесплатная.</span></li></ul>
</div></div></section>
'''
STEPS='''<div class="steps" data-r2>
 <svg class="trail" viewBox="0 0 1000 140" preserveAspectRatio="none" aria-hidden="true"><path class="t1 draw" pathLength="1" vector-effect="non-scaling-stroke" d="M-20 118 C10 60 20 47 47 47 C200 47 250 134 392 77 C520 24 600 144 736 107 C850 79 930 24 1030 44"/><path class="t2 draw" pathLength="1" vector-effect="non-scaling-stroke" d="M-20 112 C10 54 20 41 47 41 C200 41 250 128 392 71 C520 18 600 138 736 101 C850 73 930 18 1030 38"/></svg>
 <div class="slab" data-r><div class="tilt-in"><div class="plate step"><span class="puck" style="--rim:var(--blue)">1</span><h3>Форма</h3><p>%(s1)s</p></div></div></div>
 <div class="slab" data-r><div class="tilt-in"><div class="plate step"><span class="puck" style="--rim:var(--ice-4)">2</span><h3>Линия</h3><p>Кэфы рынка сравниваются с вероятностью модели. Большое расхождение — повод перепроверить данные, а не готовый вывод.</p></div></div></div>
 <div class="slab" data-r><div class="tilt-in"><div class="plate step"><span class="puck" style="--rim:var(--red)">3</span><h3>Выбор</h3><p>%(s3)s</p>
  <div class="scale" role="img" aria-label="Коридор кэфов от 1,6 до 2,3"><i class="rail"></i><i class="band"></i><span>1,2</span><span style="left:20%%">1,6</span><span style="left:55%%">2,3</span><span>3,2</span></div></div></div></div>
</div>
'''
