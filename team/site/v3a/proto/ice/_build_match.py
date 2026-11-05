from _parts import *
import math
def frows(rows):
    o=''
    for i,(r,d,w,t,s) in enumerate(rows):
        cl='w' if r=='В' else 'l'
        o+=f'<div class="frow {cl}" style="--i:{i}"><span class="res" aria-label="{"победа" if r=="В" else "поражение"}">{r}</span><time>{d}</time><span class="who"><small>{w}</small><b>{t}</b></span><span class="sc2">{s}</span></div>'
    return o
av=[('П','22.10','дома','Нефтехимик','2:3'),('В','26.10','в гостях','Динамо Москва','3:2 <small>ОТ</small>'),('В','28.10','в гостях','Ак Барс','4:0'),('П','30.10','в гостях','Лада','2:3 <small>ОТ</small>'),('П','01.11','в гостях','Сочи','1:2 <small>ОТ</small>')]
cs=[('П','23.10','в гостях','Автомобилист','1:5'),('В','25.10','в гостях','СКА','3:1'),('В','28.10','дома','Трактор','5:1'),('В','01.11','в гостях','Трактор','3:2 <small>ОТ</small>'),('В','03.11','в гостях','Металлург','7:3')]
def track(l1,l2):
    E1,E2=l1*115,l2*115
    p=lambda E,sx,dirn:f'M{sx} 215 C{sx+dirn*E*.35:.0f} 215 {sx+dirn*E*.65:.0f} 70 {sx+dirn*E:.0f} 70'
    a=p(E1,30,1);b=p(E2,610,-1)
    return a,b,30+E1,610-E2
a,b,ea,eb=track(2.33,2.36)
h=HEAD%dict(title='Авангард — ЦСКА: прогноз на матч 5 ноября 2026, КХЛ | JARVIS',desc='Расчёт модели на матч Авангард — ЦСКА 5 ноября: вероятности, тотал, кэфы, форма и личные встречи.',a_h=' aria-current="page"')
h+=f'''<main id="main">
<div class="wrap"><nav class="crumbs" aria-label="Навигация"><a href="index.html">Главная</a><span aria-hidden="true">›</span><a href="hockey.html">Хоккей</a><span aria-hidden="true">›</span><a href="hockey.html#today">Прогноз на сегодня: КХЛ</a><span aria-hidden="true">›</span><span>Авангард — ЦСКА</span></nav></div>
<section class="stage mstage" data-beam data-beam-scroll>
 <div class="giant" aria-hidden="true">КХЛ</div>
 <div class="wrap">
  <div class="mscene" aria-hidden="true">
   <div class="sphere" data-depth="8"></div><div class="ribs" data-depth="-14"></div>
   <img class="obj e1 vt-h" data-depth="28" src="../../assets/em/avangard.webp" alt="" width="300" height="300">
   <img class="obj e2 vt-a" data-depth="36" src="../../assets/em/cska.webp" alt="" width="300" height="300">
   <span class="obj puck hp" data-depth="50"></span>
  </div>
  <div class="mtext hero-enter">
   <h1>Авангард — ЦСКА <small>прогноз на матч <em class="it">5 ноября</em></small></h1>
   <div class="facts">
    <div class="cut"><small>Когда</small><b>5 ноября, четверг</b><em>16:30 МСК</em></div>
    <div class="cut"><small>Арена</small><b>«G-Drive Арена», Омск</b><em>вместимость 12 011</em></div>
    <div class="cut"><small>Турнир</small><b>КХЛ</b><em>Данные обновлены 05.11 в 04:23 МСК</em></div>
   </div>
  </div>
 </div>
</section>
<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec" data-beam><div class="wrap">
 <div class="sh"><span class="tag">Расчёт модели</span><h2>Вероятности и тотал</h2></div>
 <div class="plate blur">
  <div class="pucks" style="--c1:#d0344d;--c2:#1b3a8c">
   <div class="pk" style="--sq:.621"><span class="puck"><b><span data-count="39">39</span><sup>%</sup></b></span><small>П1, победа хозяев</small></div>
   <div class="pk" style="--sq:.468"><span class="puck"><b><span data-count="22">22</span><sup>%</sup></b></span><small>Х, ничья в основное время</small></div>
   <div class="pk" style="--sq:.629"><span class="puck"><b><span data-count="40">40</span><sup>%</sup></b></span><small>П2, победа гостей</small></div>
  </div>
  <p class="caption" style="text-align:center">Площадь шайбы пропорциональна вероятности.</p>
  <div class="total cut" style="margin-top:18px"><b>Тотал 4,5: больше</b><span class="big"><span data-count="49.8" data-dec="1">49,8</span> %</span><span class="muted">Ожидаемые голы 2,3 : 2,4</span></div>
 </div>
 <div class="tracks" style="margin-top:34px">
  <svg viewBox="0 0 640 250" role="img" aria-label="Ожидаемые голы: Авангард 2,3, ЦСКА 2,4">
   <g stroke="#d0344d" stroke-width="3"><path class="draw" pathLength="1" d="{a}"/><path class="draw" pathLength="1" transform="translate(0 8)" d="{a}" stroke-width="1.6" opacity=".6"/></g>
   <g stroke="#1b3a8c" stroke-width="3"><path class="draw" pathLength="1" d="{b}"/><path class="draw" pathLength="1" transform="translate(0 8)" d="{b}" stroke-width="1.6" opacity=".6"/></g>
   <circle class="goal" cx="{ea:.0f}" cy="70" r="9" fill="#0b2240"/><circle class="goal" cx="{eb:.0f}" cy="70" r="9" fill="#0b2240"/>
   <text x="320" y="38" text-anchor="middle" class="big">2,3 : 2,4</text>
   <text x="30" y="242">Авангард</text><text x="610" y="242" text-anchor="end">ЦСКА</text>
  </svg>
  <p class="caption" style="text-align:center">Ожидаемые голы: два следа конька, длина пропорциональна среднему числу голов за матч.</p>
 </div>
</div></section>

<div class="wrap"><div class="blue" aria-hidden="true"></div></div>

<section class="sec"><div class="wrap">
 <div class="sh"><span class="tag b">Справка, не рекомендация</span><h2>Кэфы на матч</h2></div>
 <div class="kefs">
  <div class="kef"><small>П1</small><b>2,95</b></div><div class="kef"><small>Х</small><b>4,20</b></div><div class="kef"><small>П2</small><b>2,10</b></div>
  <div class="kef tt"><span><small>Тотал 4,5: больше</small><b>1,77</b></span><span><small>меньше</small><b>2,05</b></span></div>
 </div>
 <p class="note" style="margin-top:16px">Основное время; кэфы на момент последнего обновления данных, до матча они меняются. Это справка, не рекомендация. Цифры считает модель по данным сайта, а не эксперт. Это вероятности, а не гарантия исхода. <a href="../../model.html" style="color:var(--blue);font-weight:700">Как считает модель</a>, <a href="../../glossary.html" style="color:var(--blue);font-weight:700">словарь терминов</a>.</p>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sh"><h2>Коротко о матче</h2></div>
 <div class="slab" data-r><div class="tilt-in"><div class="plate"><p class="facts-text">По таблице: Авангард — 7-е место, 22 очка за 20 матчей; ЦСКА — 1-е место, 34 очка за 22 матча. В последних 5 матчах: Авангард — 2 победы, 3 поражения, ЦСКА — 4 победы, 1 поражение. Шансы по модели близки: Авангард — 39 %, ЦСКА — 40 %. Модель ждёт около 4,7 гола в матче: 2,3 у хозяев и 2,4 у гостей. Очные встречи из данных (4): Авангард — 3 победы, ЦСКА — 1 победа. Это оценка вероятностей по данным, а не обещание исхода.</p></div></div></div>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sh"><h2>Форма команд: последние 5 матчей</h2></div>
 <div class="forms">
  <div><h3><img src="../../assets/em/avangard.webp" alt="" width="34" height="34">Авангард</h3>{frows(av)}</div>
  <div><h3><img src="../../assets/em/cska.webp" alt="" width="34" height="34">ЦСКА</h3>{frows(cs)}</div>
 </div>
</div></section>

<div class="wrap"><div class="rink" aria-hidden="true"><span class="face"></span></div></div>

<section class="sec"><div class="wrap">
 <div class="sh"><h2>Личные встречи</h2></div>
 <div class="tblwrap"><table class="tbl"><thead><tr><th>Дата</th><th>Хозяева</th><th>Счёт</th><th>Гости</th></tr></thead><tbody>
  <tr><td>04.03.2026</td><td>ЦСКА</td><td>0:2</td><td>Авангард</td></tr><tr><td>15.01.2026</td><td>Авангард</td><td>2:1</td><td>ЦСКА</td></tr>
  <tr><td>04.02.2025</td><td>ЦСКА</td><td>2:1 Б</td><td>Авангард</td></tr><tr><td>17.01.2025</td><td>Авангард</td><td>4:0</td><td>ЦСКА</td></tr></tbody></table></div>
 <p class="note">Последние встречи из данных сайта; ОТ и Б — овертайм и буллиты.</p>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sh"><h2>Положение в таблице</h2></div>
 <div class="tblwrap"><table class="tbl"><thead><tr><th>Команда</th><th class="r">Место</th><th class="r">И</th><th class="r">В</th><th class="r">П</th><th class="r">Голы</th><th class="r">Очки</th></tr></thead><tbody>
  <tr><td>Авангард</td><td class="r">7</td><td class="r">20</td><td class="r">10</td><td class="r">10</td><td class="r">40:47</td><td class="r">22</td></tr>
  <tr><td>ЦСКА</td><td class="r">1</td><td class="r">22</td><td class="r">17</td><td class="r">5</td><td class="r">73:42</td><td class="r">34</td></tr></tbody></table></div>
 <p class="note">И — игры, В — победы, П — поражения (в основное и дополнительное время).</p>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sh"><h2>Другие матчи КХЛ в этот день</h2></div>
 <div class="oth">
  <div class="slab" data-r><div class="tilt-in"><div class="plate"><a href="hockey.html#khl_2026-11-05_metallurg_neftekhimik"><b>Металлург — Нефтехимик</b><time>17:00 МСК</time></a></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate"><a href="hockey.html#khl_2026-11-05_shanghai_dinamo_msk"><b>Шанхайские Драконы — Динамо Москва</b><time>19:30 МСК</time></a></div></div></div>
  <div class="slab" data-r><div class="tilt-in"><div class="plate"><a href="hockey.html#khl_2026-11-05_sochi_severstal"><b>Сочи — Северсталь</b><time>19:30 МСК</time></a></div></div></div>
 </div>
 <p class="links" style="margin-top:28px"><a href="../../khl/avangard/index.html">Страница клуба: Авангард</a><a href="../../khl/cska/index.html">Страница клуба: ЦСКА</a><a href="../../hockey/league.html?lg=khl">Лига: КХЛ</a><a href="hockey.html">Все матчи дня колодой</a></p>
 <p style="margin:26px 0 18px"><a class="btn" href="https://t.me/jarvibet">Все прогнозы дня — в Telegram</a></p>
 <p class="disc">Материалы носят информационный характер и не гарантируют результат. Реклама букмекеров на сайте не размещается. Сайт только для совершеннолетних (18+).</p>
</div></section>
</main>
'''+FOOT
open('match.html','w').write(h)
c=open('ice.css').read()
if '.mscene' not in c:
    c+='''
/* шапка матча: слои глубины */
.mstage{padding-top:0}
.mstage .wrap{display:block;padding-top:0}
.mscene{position:relative;height:clamp(300px,40vw,520px);margin-top:clamp(30px,6vw,90px)}
.mscene .sphere{left:50%;right:auto;top:6%;width:clamp(200px,26vw,360px);transform:translateX(-50%)}
.mscene .ribs{left:50%;right:auto;top:2%;width:clamp(150px,20vw,280px);height:92%;margin-left:clamp(-140px,-10vw,-60px)}
.mscene .obj.e1{left:6%;top:8%;width:clamp(130px,23vw,330px)}
.mscene .obj.e2{right:6%;left:auto;top:8%;width:clamp(130px,23vw,330px)}
.mscene .obj.pk{left:50%;top:auto;bottom:0;margin-left:calc(var(--d) * -.5);--d:clamp(90px,11vw,150px)}
.mtext{position:relative;z-index:4;margin-top:clamp(-70px,-5vw,-20px)}
.mtext .facts{margin-top:22px}
.mstage .giant{font-size:clamp(120px,32vw,460px);top:clamp(30px,5vw,70px)}
@media (max-width:900px){.mscene{height:300px}.mscene .obj.e1{left:0}.mscene .obj.e2{right:0}.mscene .obj.pk{--d:72px}.mscene .sphere{width:52vw}.mstage .giant{font-size:clamp(100px,36vw,260px)}}
'''
    open('ice.css','w').write(c)
