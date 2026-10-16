"""Пример: нынешний «Итог матча», верх — кольца «Versus» вместо шёлка, анимация (гифка) → out/pr/."""
import postmatch_styles as pm

print(pm.render('Адмирал', 'Спартак', 1, 5, 'out/pr/admiral_spartak.mp4', league='KHL', date='четверг, 16 октября',
                pick='победа Спартака в основное время', kef=1.95, hit=True, style='verdict_rings'))
