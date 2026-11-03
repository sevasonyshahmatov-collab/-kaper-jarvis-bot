"""Чистка истории открытого репозитория сайта (безопасность 03.11, решение владельца «да» в чате «Сайт»).

Во всех коммитах в data/<лига>-<день>.json у матчей без поста в канале (или с постом о другой ставке) удаляются поля
модели — те же, что build.py seal_public прячет в новых сборках (pick, odds, p, sim, fact, res, score). Посты канала —
stats/published.json из последнего коммита (в нём все посты с 1 сентября). Заодно личная почта в авторе первого коммита
меняется на адрес noreply. Остальные файлы и коммиты не меняются; последний коммит после #138 уже чистый — дерево
сайта остаётся прежним.

    python team/site/security/scrub_history.py <клон сайта с полной историей>      # переписывает на месте
    python team/site/security/scrub_history.py <клон> --check                       # только проверить: сколько осталось
"""
import json
import re
import subprocess
import sys

SEAL = ('pick', 'odds', 'p', 'sim', 'fact', 'res', 'score')
OLD_MAIL = b'sevasony.shahmatov@gmail.com'
NEW_MAIL = b'sevasonyshahmatov-collab@users.noreply.github.com'


def _norm(t):                                     # как в team/site/build.py
    t = str(t or '').lower().replace('ё', 'е').replace('в осн. время', 'в основное время')
    return re.sub(r'[^0-9a-zа-я+,.]+', ' ', t).strip()


def load_posts(repo):
    raw = subprocess.run(['git', '-C', repo, 'show', 'HEAD:stats/published.json'], capture_output=True, check=True).stdout
    return {(x['lg'], _norm(x['h']), _norm(x['a']), x['d'][:10]): _norm(x['bet']) for x in json.loads(raw)}


def scrub(P, posts):
    """Убрать поля модели у матчей без поста. Возвращает число очищенных матчей."""
    n = 0
    for m in P.get('matches') or []:
        bet = posts.get((P.get('league'), _norm(m.get('h')), _norm(m.get('a')), str(m.get('d'))[:10]))
        if m.get('pick') is None or (bet is not None and bet == _norm(m['pick'])):
            continue
        for k in SEAL:
            m.pop(k, None)
        n += 1
    return n


def day_file(data):
    if not data.lstrip().startswith(b'{') or b'"matches"' not in data or b'"league"' not in data:
        return None
    try:
        P = json.loads(data.decode('utf-8'))
    except ValueError:
        return None
    return P if isinstance(P, dict) and isinstance(P.get('matches'), list) and P.get('league') in ('khl', 'nhl') else None


def check(repo, posts):
    """Сколько матчей без поста с полями модели осталось во всех версиях data/*.json по всей истории."""
    out = subprocess.run(['git', '-C', repo, 'rev-list', '--all', '--objects'], capture_output=True, text=True, check=True).stdout
    bad = 0
    for line in out.splitlines():
        sha, _, path = line.partition(' ')
        if re.fullmatch(r'data/(khl|nhl)-\d{4}-\d{2}-\d{2}\.json', path):
            P = day_file(subprocess.run(['git', '-C', repo, 'cat-file', 'blob', sha], capture_output=True, check=True).stdout)
            if P:
                bad += scrub(P, posts)
    mails = subprocess.run(['git', '-C', repo, 'log', '--all', '--format=%ae%n%ce'], capture_output=True, check=True).stdout
    return bad, mails.count(OLD_MAIL)


def main():
    repo = sys.argv[1]
    posts = load_posts(repo)
    if '--check' in sys.argv:
        bad, mail = check(repo, posts)
        print('SCRUB осталось матчей без поста с полями модели: %d, коммитов с личной почтой: %d' % (bad, mail))
        sys.exit(1 if bad or mail else 0)
    import git_filter_repo as fr
    stat = dict(blobs=0, matches=0)

    def blob_cb(blob, _meta):
        P = day_file(blob.data)
        if P is None:
            return
        n = scrub(P, posts)
        if n:
            blob.data = (json.dumps(P, ensure_ascii=False, indent=1)).encode('utf-8')
            stat['blobs'] += 1
            stat['matches'] += n

    def mail_cb(email):
        return NEW_MAIL if email == OLD_MAIL else email

    args = fr.FilteringOptions.parse_args(['--force', '--quiet', '--source', repo, '--target', repo])
    fr.RepoFilter(args, blob_callback=blob_cb, email_callback=mail_cb).run()
    print('SCRUB переписано версий файлов: %d, матчей без поста очищено: %d' % (stat['blobs'], stat['matches']), flush=True)


if __name__ == '__main__':
    main()
