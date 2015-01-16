#!/usr/bin/python3

import pyaudio
import artdmx
import numpy as np
import scipy
import scipy.signal

READ_FRAMES = 1764
RATE = 44100

pa = pyaudio.PyAudio()
stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, input_device_index=None, frames_per_buffer=READ_FRAMES)
dmx = artdmx.Client(75, 'localhost', universe=0x100)

buf = np.zeros(dtype='float64', shape=2**15)
upper = 1e-7
windows = [scipy.signal.hann(2**i) for i in range(17)]
bin_buf = np.zeros(dtype='float64', shape=75)

def my_stft(signal, i):
    res = abs(np.fft.rfft(signal[-2**i:] * windows[i])[1:])
    res /= 2**i
    return res

while True:
    ibuf = np.frombuffer(stream.read(READ_FRAMES), dtype='short') / 65535
    buf[:-len(ibuf)] = buf[len(ibuf):]
    buf[-len(ibuf):] = ibuf

    C = 20

    bins = np.zeros(shape=7*12, dtype=np.float64)
    f = 440 * 2 ** (np.arange(-3*12, 4*12)/12) * len(buf) / RATE
    for k in range(0, 8):
        tmp = my_stft(buf, 15-k)
        tmp[:C] = 0
        bins += tmp[(f / 2**k).astype(int)]

    bins = bins[:75]

    bins = np.where(bins > 1.25*bin_buf, bins, np.where(bins < 0.75*bin_buf, 0.95*bin_buf, bin_buf))
    bin_buf[:] = bins

    upper = 0.995 * upper + 0.005 * max(bins)
    if upper != 0:
        bins /= upper

    dmx.values[:] = 50 + np.clip(bins, 0, 1) * 200
    dmx.push()
