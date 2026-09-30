import os; os.makedirs("out/today", exist_ok=True)
from poster import render_clean, render_cards, team_info, TEAMS
W='ВТ 22.09 · 19:30 МСК'
M=[('Динамо Москва','Барыс',(1.62,4.32,4.52),(7,8,'XXWWL'),(6,8,'WLWLW')),
   ('Торпедо','Авангард',(2.79,3.65,2.28),(6,8,'XLWWL'),(6,6,'WXXLL')),
   ('Шанхайские Драконы','Автомобилист',(3.11,3.76,2.07),(4,4,'XLXL'),(6,6,'OLWOL'))]
for h,a,o,ih,ia in M:
    render_cards(h,a,dict(when=W,odds=o,home=team_info(*ih),away=team_info(*ia)),'out/today/card_%s_%s.png'%(TEAMS[h][0],TEAMS[a][0]))
    print(h,a)
for h,a,o,ih,ia in M:
    render_clean(h,a,dict(when=W,odds=o,home=team_info(*ih),away=team_info(*ia)),'out/today/side_%s_%s.png'%(TEAMS[h][0],TEAMS[a][0]))
