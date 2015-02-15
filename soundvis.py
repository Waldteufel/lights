#!/usr/bin/python3

import artdmx
import numpy as np
import scipy
import scipy.signal
from gi.repository import GObject, GLib, Gst, Gio
import argparse

parser = argparse.ArgumentParser(description='Visualize sound over ArtDMX.')
parser.add_argument('-u', '--universe', metavar='UNIV', default=0,
                    type=lambda x: int(x, 0), help='universe id (default=0)')
parser.add_argument('-s', '--server', metavar='HOST', default='localhost',
                    type=str, help='server (default=localhost)')
parser.add_argument('-p', '--port', metavar='PORT', default=6454, type=int,
                    help='udp port (default=6454)')

args = parser.parse_args()


READ_FRAMES = 1764 // 2
RATE = 44100

buf = np.zeros(dtype=np.float32, shape=2**15)
upper = 1e-7
windows = [scipy.signal.hann(2**i) for i in range(17)]
freqs = 440 * 2 ** (np.arange(-3*12, 4*12)/12) * len(buf) / RATE

bins = np.zeros(shape=7*12, dtype=np.float32)
bin_buf = np.zeros(shape=7*12, dtype=np.float32)


def my_stft(signal, i):
    res = abs(np.fft.rfft(signal[-2**i:] * windows[i])[1:])
    res /= 2**i
    return res


def process_buffer(appsink):
    global bins, upper

    gst_ibuf = appsink.emit('pull-sample').get_buffer()
    gst_raw = gst_ibuf.extract_dup(0, gst_ibuf.get_size())
    ibuf = np.frombuffer(gst_raw, dtype=np.float32)
    ibuf = ibuf[-len(buf):]  # drop samples if there are too many
    buf[:-len(ibuf)] = buf[len(ibuf):]
    buf[-len(ibuf):] = ibuf

    bins[:] = 0
    for k in range(0, 8):
        tmp = my_stft(buf, 15-k)
        tmp[:20] = 0  # cut off low frequencies
        bins += tmp[(freqs / 2**k).astype(int)]
    bins[75:] = 0  # ignore out-of-range channels

    bins = np.where(bins > 1.25*bin_buf, bins,
                    np.where(bins < 0.75*bin_buf, 0.95*bin_buf, bin_buf))
    bin_buf[:] = bins

    upper = 0.995 * upper + 0.005 * max(bins)
    if upper != 0:
        bins /= upper
    np.clip(bins, 0, 1, out=bins)

    dmx.channels[:] = 50 + bins[:75] * 200
    dmx.push()

    return False

GObject.threads_init()
GLib.set_application_name('Sound Visualization')
Gst.init(None)
dmx = artdmx.Client(75, args.server, args.port, universe=args.universe)
pipeline = Gst.parse_launch('pulsesrc ! appsink name=sink ' +
                            'emit-signals=True ' +
                            'caps=audio/x-raw,format=F32LE,channels=1')
appsink = pipeline.get_by_name('sink')
appsink.connect('new-sample', process_buffer)


def check_masks():
    if dmxmasks[args.universe]:
        pipeline.set_state(Gst.State.PLAYING)
    else:
        pipeline.set_state(Gst.State.PAUSED)
    return True

dmxmasks = np.memmap('/dev/shm/dmxmasks', mode='r', dtype=bool)
GLib.timeout_add_seconds(1, check_masks)

GObject.MainLoop().run()
