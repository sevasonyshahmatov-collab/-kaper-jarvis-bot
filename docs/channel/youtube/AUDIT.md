# YouTube: снять лимит ~6 загрузок в сутки и 7-дневный ключ (BACKLOG №15)

Две заявки в Google, обе бесплатные, подаёт владелец (аккаунт Google — владелец проекта «JARVIS YouTube» в Google Cloud).
Ниже — готовые тексты: скопировать и вставить. Все ответы — на английском (формы Google англоязычные).

| Что мешает | Почему | Что снимает |
|---|---|---|
| ключ `YT_REFRESH_TOKEN` живёт 7 дней | приложение в статусе «Testing» | Шаг 2 — перевести приложение в «In production» |
| ~6 загрузок в сутки | квота API 10 000 единиц, загрузка — 1 600 | Шаг 3 — форма Audit and Quota Extension |

---

## Шаг 1. Страница политики конфиденциальности (5 мин)

Google требует публичную ссылку на политику. Проще всего — https://telegra.ph : заголовок «JARVIS — Privacy Policy»,
вставить текст ниже, «Publish», скопировать ссылку.

> **JARVIS — Privacy Policy**
>
> JARVIS is an internal publishing tool used only by the owner of the YouTube channel "JARVIS BET | Прогнозы на хоккей
> НХЛ и КХЛ" (https://t.me/jarvibet). It uploads short videos created by the channel owner to the owner's own YouTube
> channel through the YouTube Data API.
>
> Data we access: only the channel owner's YouTube account, with the scope `youtube.upload` (and, for weekly statistics,
> `yt-analytics.readonly`). We do not access, collect or store data of any other YouTube users or viewers.
>
> Storage: the OAuth refresh token is stored encrypted as a GitHub Actions secret and is used only to upload the
> owner's videos and read the owner's channel statistics. Video files are deleted automatically after 2 days.
>
> Sharing: no data is sold, shared or transferred to third parties.
>
> Revoking access: the owner can revoke access at any time at https://myaccount.google.com/permissions.
>
> JARVIS uses YouTube API Services. YouTube Terms of Service: https://www.youtube.com/t/terms.
> Google Privacy Policy: https://policies.google.com/privacy.
>
> Contact: <почта владельца>

## Шаг 2. Приложение — из «Testing» в «In production» (10 мин, убирает 7-дневный ключ)

**Сделано: 23.10 статус «In production» (скриншот владельца).** Осталось п. 5 — новый ключ, если текущий выдан до перевода.

console.cloud.google.com → проект «JARVIS YouTube» → **Google Auth Platform** (или APIs & Services → OAuth consent screen):
1. **Branding**: App name `JARVIS Uploader`; User support email — ваша почта; App home page — `https://www.youtube.com/@<канал>`;
   Privacy policy — ссылка из шага 1; Authorized domains — `telegra.ph` и `youtube.com` (если просит); Developer contact — почта. Save.
2. **Data access** (Scopes): `.../auth/youtube.upload` (и `.../auth/yt-analytics.readonly` — для еженедельного отчёта).
3. **Audience** → **Publish app** → Confirm. Раньше кнопка не срабатывала — скорее всего, не хватало полей из п. 1.
4. Если Google попросит верификацию (scope `youtube.upload` — «sensitive»): «Prepare for verification», ответы:
   - *How will the scopes be used?* — `The app is an internal tool used only by the channel owner. youtube.upload is
     used to upload short videos (hockey match previews) that the owner creates to the owner's own channel, several
     times a day, from a scheduled GitHub Actions job. No other users sign in.`
   - *Demo video* — запись экрана 1–2 мин: OAuth Playground (свой Client ID) → вход в Google → экран согласия с названием
     приложения и scope → ролик появляется в YouTube Studio. Загрузить на YouTube как «Доступ по ссылке», ссылку вставить.
5. После публикации — **один раз** получить новый refresh token (OAuth Playground, как раньше) и положить в секрет
   `YT_REFRESH_TOKEN`. Дальше он не истекает каждые 7 дней.

Пока Google проверяет (обычно 3–10 дней), приложение работает как раньше; на экране входа может быть предупреждение
«Google hasn't verified this app» — для своего аккаунта это нормально: «Advanced» → «Go to JARVIS Uploader».

## Шаг 3. Форма Audit and Quota Extension (15 мин, убирает лимит загрузок)

Форма: https://support.google.com/youtube/contact/yt_api_form → «YouTube API Services — Audit and Quota Extension Form».
Ответы:
- **API Client / project number** — Google Cloud → проект «JARVIS YouTube» → Dashboard → Project number.
- **Organization** — `Individual / JARVIS (hockey predictions media)`; сайт — `https://t.me/jarvibet`.
- **Use case / How does your API client use YouTube API Services?** —
  `An internal, server-side tool for a single YouTube channel that we own. Every day it renders one vertical short
  video (about 23 seconds) per KHL and NHL hockey match with a match preview and uploads it to our own channel with
  videos.insert, sets a custom thumbnail with thumbnails.set, and once a week reads our own channel statistics with
  YouTube Analytics. There is no public user interface and no other users. All content is original (our own graphics
  and the channel owner's music).`
- **Which API methods** — `videos.insert, thumbnails.set, playlistItems.insert, commentThreads.insert (own videos), YouTube Analytics reports.query`.
- **Requested quota** — `50,000 units per day`.
  **Justification** — `KHL and NHL together have 10–20 matches per day in season. One upload costs 1,600 units plus
  50 for the thumbnail and 50 for adding it to a playlist: 20 × 1,700 = 34,000 units, plus weekly long videos and
  retries. The current 10,000 units allow only about 6 uploads per day.`
- **Screenshots / screencast** — тот же ролик из шага 2 и скриншот YouTube Studio со списком загруженных шортсов.
- **Privacy policy** — ссылка из шага 1. **Terms of service** — `https://www.youtube.com/t/terms`.
- Галочки соответствия политике (Developer Policies) — подтвердить.

Ответ приходит на почту: обычно 1–4 недели, иногда Google задаёт уточняющие вопросы — перешлите их в чат, подготовлю ответ.

## После одобрения
- Квота растёт — конвейер сам грузит все ролики дня (в коде ничего менять не нужно: «загрузите вручную» исчезнет).
- Можно добавить на YouTube серию про таблицу, шортс «Зашло вчера», плейлисты и длинное видео недели.
