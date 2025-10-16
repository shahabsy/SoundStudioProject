import numpy as np
import matplotlib.pyplot as plt
import wave
import os

def generate_waveform_image(file_path, save_path):
    # read sound file
    with wave.open(file_path, 'rb') as wf:
        n_frames = wf.getnframes()
        framerate = wf.getframerate()
        audio = wf.readframes(n_frames)
        signal = np.frombuffer(audio, dtype=np.int16)
    
    # downsample for performance
    step = len(signal) // 1000 or 1
    signal = signal[::step]

    # plot waveform
    plt.figure (figsize=(5, 1))
    plt.plot(signal, color='mediumseagreen')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
    plt.close()