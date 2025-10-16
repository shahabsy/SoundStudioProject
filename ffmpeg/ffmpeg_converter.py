import subprocess
import os
from core.utils import resource_path
import sys
#BASE = os.path.dirname(__file__)
#BASE = resource_path("ffmpeg/ffmpeg_converter.py")
#FFMPEG_BIN = os.path.join(BASE, "ffmpeg.exe")
FFMPEG_BIN = resource_path("ffmpeg/ffmpeg.exe")

# ffmpeg -i "$f" -vn -ar 44100 -ac 2 -b:a 96k "$output_dir/${f%.*}.mp3"
# ffmpeg -i "$f" -dash 1 -b:a 96k "$output_dir/${f%.*}.webm"
def get_ffmpeg_bin(ffmpeg_path = None):
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        return ffmpeg_path
    if sys.platform == "darwin":
        bin_path = resource_path("ffmpeg/ffmpeg")
        if not os.access(bin_path, os.X_OK):
            try:
                os.chmod(bin_path, 0o755)
            except Exception as e:
                raise RuntimeError(f"Failed to set executable permission for ffmpeg: {e}")
        return bin_path
    return FFMPEG_BIN

def convert_wave_to_mp3(src_path, dst_path, ffmpeg_path=None):
    ffmpeg_bin = get_ffmpeg_bin(ffmpeg_path)
    cmd = [
        ffmpeg_bin,
        "-y",               # Overwrite output
        "-i", src_path,
        "-vn",              # No video
        "-ar", "44100",     # Audio sampling rate
        "-ac", "2",         # Stereo
        "-b:a", "96k",     # Bitrate
        dst_path
    ]
    if not os.path.exists(ffmpeg_bin):
        raise FileNotFoundError(f"ffmpeg binary not found at {ffmpeg_bin}")
    subprocess.run(cmd, check=True)

def convert_wav_to_webm(src_path, dst_path, ffmpeg_path=None):
    ffmpeg_bin = get_ffmpeg_bin(ffmpeg_path)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", src_path,
        "-dash", "1",
        "-b:a", "96k",
        dst_path
    ]
    if not os.path.exists(ffmpeg_bin):
        raise FileNotFoundError(f"ffmpeg binary not found at {ffmpeg_bin}")
    subprocess.run(cmd, check=True)


####################################################################################
# example use
# convert_wav_to_mp3("assets/sounds/intro.wav", "exports/intro.mp3")
# convert_wav_to_webm("assets/sounds/intro.wav", "exports/intro.webm")
####################################################################################