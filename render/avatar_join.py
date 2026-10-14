"""ИИ-ведущий (тест): склейка кусков говорящего видео (артефакты avatar-part-<i> задания avatar в itogi.yml) в один ролик
с цельной дорожкой голоса и отправка владельцу в личку (владелец — создатель @jarvibet, как в team_job).
Запуск: python render/avatar_join.py <папка с avatar-part-*>; голос — $TB/input/voice.wav; итог — avatar_host.mp4.
Чужого кода здесь нет: только ffmpeg над готовыми файлами."""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_job  # noqa: E402

src = sys.argv[1]
parts = sorted((d for d in os.listdir(src) if re.fullmatch(r'avatar-part-\d+', d)), key=lambda d: int(d.rsplit('-', 1)[1]))
with open('parts.txt', 'w') as f:
    for d in parts:
        f.write("file '%s'\n" % os.path.abspath(os.path.join(src, d, 'host.mp4')))
print('кусков:', len(parts))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'parts.txt', '-an', '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p', '-crf', '17', '-r', '25', 'video.mp4'], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'video.mp4', '-i', os.path.join(os.environ['TB'], 'input', 'voice.wav'),
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', 'avatar_host.mp4'], check=True)
subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height', '-of', 'compact',
                'avatar_host.mp4'], check=True)
token = os.environ.get('TG_BOT_TOKEN')
if token:
    owner = team_job.owner_chat(token, '@jarvibet')
    with open('avatar_host.mp4', 'rb') as f:
        team_job._api(token, 'sendVideo', dict(chat_id=owner, supports_streaming='true',
                                               caption='Тест ИИ-ведущего: ваше фото и голос (запись А). Не для публикации.'),
                      {'video': f})
    print('отправлено владельцу')
