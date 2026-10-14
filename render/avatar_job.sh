#!/usr/bin/env bash
# ИИ-ведущий (тест): говорящее видео из фото и голоса владельца — запускается GitHub Actions (.github/workflows/itogi.yml,
# задание avatar), payload {"kind":"avatar","branch":"tmp-avatar-test","size":512}.
# Фото и голос лежат на временной ветке branch (input/face.jpg, input/voice.wav) — в рабочие ветки не попадают;
# workflow выкладывает её в папку $TB без сохранённых учётных данных git. Ветку после теста удаляем.
# SadTalker (Apache-2.0, github.com/OpenTalker/SadTalker, закреплённый коммит) на CPU: губы и голова под голос,
# лицо дорисовывает GFPGAN. Чужой код работает без токенов и прав на запись: готовое видео — только в $W/out/host.mp4,
# оттуда его забирает шаг upload-artifact (хранится 1 день).
# Права: часть весов SadTalker (3DMM / Basel Face Model) — только некоммерческое использование; для теста.
set -euo pipefail

SIZE=$(python -c 'import json,os; print(int(json.loads(os.environ["INPUT_PAYLOAD"]).get("size", 512)))')
# "enhancer": false — без дорисовки лица GFPGAN: в разы быстрее на CPU, лицо мягче
ENH=$(python -c 'import json,os; print("--enhancer gfpgan" if json.loads(os.environ["INPUT_PAYLOAD"]).get("enhancer", True) else "")')
# PART / PARTS (матрица в itogi.yml): голос режется на PARTS кусков по ~равной длине, кратной кадру (0,04 с), это
# задание оживляет кусок PART; куски склеивает задание avatar_join. На CPU 2 ядра ~12 с на кадр 256 — без деления долго.
PARTS=${PARTS:-1}
PART=${PART:-0}
W="$RUNNER_TEMP/avatar"
ST_COMMIT=cd4c0465ae0b54a6f85af57f5c65fec9fe23e7f8
mkdir -p "$W"

command -v ffmpeg >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg; }

git init -q "$W/st"
git -C "$W/st" fetch -q --depth 1 https://github.com/OpenTalker/SadTalker "$ST_COMMIT"
git -C "$W/st" checkout -q FETCH_HEAD
cat > "$W/pins.txt" <<'EOF'
numpy==1.23.4
torch==2.0.1
torchvision==0.15.2
torchaudio==2.0.2
opencv-python==4.8.1.78
numba==0.56.4
llvmlite==0.39.1
scipy==1.10.1
scikit-image==0.19.3
EOF
pip install -q torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu
pip install -q -c "$W/pins.txt" numpy face_alignment==1.3.5 imageio==2.19.3 imageio-ffmpeg==0.4.7 librosa==0.9.2 \
  numba resampy==0.3.1 pydub==0.25.1 scipy kornia==0.6.8 tqdm yacs==0.1.8 pyyaml joblib==1.1.0 scikit-image \
  opencv-python facexlib==0.3.0 safetensors av
pip install -q -c "$W/pins.txt" --no-build-isolation basicsr==1.4.2 gfpgan==1.3.8

cd "$W/st"
mkdir -p checkpoints gfpgan/weights
R=https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc
for f in mapping_00109-model.pth.tar mapping_00229-model.pth.tar SadTalker_V0.0.2_256.safetensors SadTalker_V0.0.2_512.safetensors; do
  curl -sSfL -o "checkpoints/$f" "$R/$f"
done
curl -sSfL -o gfpgan/weights/alignment_WFLW_4HG.pth https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth
curl -sSfL -o gfpgan/weights/detection_Resnet50_Final.pth https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth
curl -sSfL -o gfpgan/weights/GFPGANv1.4.pth https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth
curl -sSfL -o gfpgan/weights/parsing_parsenet.pth https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth

AUD="$TB/input/voice.wav"
if [ "$PARTS" -gt 1 ]; then
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUD")
  read -r SS DD < <(python -c "import math; d=$DUR; n=$PARTS; i=$PART; seg=math.ceil(d/n/0.04)*0.04; print('%.3f %.3f' % (i*seg, seg))")
  ffmpeg -v error -y -ss "$SS" -t "$DD" -i "$AUD" -ac 1 -ar 16000 "$W/part.wav"
  AUD="$W/part.wav"
  echo "часть $PART из $PARTS: с $SS с, $DD с"
fi
python inference.py --driven_audio "$AUD" --source_image "$TB/input/face.jpg" --result_dir "$W/res" \
  --still --preprocess full $ENH --size "$SIZE" --cpu
RES=$(ls -t "$W"/res/*.mp4 | head -1)
mkdir -p "$W/out"
ffmpeg -v error -y -i "$RES" -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow -c:a aac -b:a 192k -movflags +faststart \
  "$W/out/host.mp4"
ffprobe -v error -show_entries format=duration:stream=width,height -of compact "$W/out/host.mp4"
echo "AVATAR_DONE"
