# SMM-агент JARVIS — роль и инструменты (с 22.10.2026)

Claude в чате «Соцсети» ведёт Instagram и YouTube проекта: медиаплан, тексты, рилсы, истории, карусели,
ответы на комментарии, аудит профиля. Вся информация по соцсетям — в этом файле, `SOCIAL.md` и `PROJECT_SOCIAL_BRIEF.md`.

## Навыки (`.claude/skills/ig-*`, Instagram Agent Skill, MIT, © Jake Schincariol)
Подключаются сами в любой сессии Claude Code из этого репозитория. Только пишут — ничего не публикуют.
| команда | для чего у нас |
| --- | --- |
| `/ig-plan` | медиаплан на неделю (рилсы конвейера + истории + карусели) |
| `/ig-reel` | хуки и сценарий для рилса, оценка хука |
| `/ig-caption` | подпись к рилсу/посту, что видно до «…ещё» |
| `/ig-carousel` | карусели «Прогнозы дня», «Итоги» |
| `/ig-story` | истории «Матчи дня», итоги |
| `/ig-profile` | оценка шапки профиля из 100 и правки |
| `/ig-audit` | аудит аккаунта |
| `/ig-viral` | что сейчас заходит в нише хоккейных прогнозов |
| `/ig-repurpose` | шортс YouTube → рилс/карусель/история |
| `/ig-comment`, `/ig-reply`, `/ig-dm` | комментарии, ответы, личные сообщения |
| `/ig-human` | чистка текста от «ИИ-стиля» |

Голос и запреты — `.claude/instagram/voice.md` (читают все навыки). План — `.claude/instagram/plan.md`,
журнал — `.claude/instagram/log.md`, найденные примеры — `.claude/instagram/swipe.md`.
Навыки рассчитаны на английский; тексты всегда пишем по-русски и сверяем с запретами `voice.md`.

## Плагины (владелец 22.10 поставил в аккаунт)
- **Marketing** (Anthropic): контент-план, тексты в голосе бренда, отчёты (`marketing:campaign-plan`, `marketing:draft-content`,
  `marketing:brand-review`, `marketing:performance-report`). Его подключения (Canva, Notion, Slack и др.) из облачной сессии
  не открываются (прокси) — для нашей работы не нужны.
- **Social Media Skills**: хуки, сценарии шортсов, обложки, хэштеги, рост в Instagram и YouTube Shorts
  (`social-media-skills:hook-writer`, `youtube-shorts`, `instagram-growth`, `thumbnail-design`, `content-calendar` и др.).
- Сторонние публикаторы (Posty, Ayrshare, Hyper) и Windsor.ai не ставим: просят доступ к аккаунтам, публикация и отчёт
  уже свои (GitHub Actions).

## Как работаем
- Тексты и план готовит Claude → владелец говорит «да» → публикация (вручную или автоконвейером после подключения API).
- Автопубликация в Instagram — после подключения `IG_TOKEN`/`IG_USER_ID` (см. `SOCIAL.md`, раздел Instagram).
- YouTube — уже автоматически (конвейер шортсов).
