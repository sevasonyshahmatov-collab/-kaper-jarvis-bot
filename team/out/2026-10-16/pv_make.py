"""Пример послематчевого поста в графике Versus: Адмирал — Спартак 1:5 (16.10), три подачи баннера → out/pv/."""
import postmatch_vs as pv

for v in ('score', 'abbr', 'stamp'):
    print(pv.render('Адмирал', 'Спартак', 1, 5, 'out/pv/admiral_spartak_%s.mp4' % v, date='16 октября',
                    pick='победа Спартака в основное время', kef=1.95, hit=True, variant=v))
