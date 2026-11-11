"""11.11: apt-get на раннере виснет (не резолвится security.ubuntu.com) — ffmpeg из pip (imageio-ffmpeg), потом
express_render.py с теми же аргументами."""
import os, runpy, shutil, subprocess, sys
if not shutil.which('ffmpeg'):
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'imageio-ffmpeg'], check=True)
    import imageio_ffmpeg
    d = os.path.abspath('out/ffbin'); os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, 'ffmpeg')
    if not os.path.exists(dst):
        os.symlink(imageio_ffmpeg.get_ffmpeg_exe(), dst)
    os.environ['PATH'] = d + os.pathsep + os.environ['PATH']
    print('ffmpeg из imageio-ffmpeg:', shutil.which('ffmpeg'))
sys.argv = ['team/picks/express_render.py'] + sys.argv[1:]
runpy.run_path('team/picks/express_render.py', run_name='__main__')
