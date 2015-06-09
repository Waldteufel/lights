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
parser.add_argument('-f', '--force', dest='force', action='store_true', default=False)

args = parser.parse_args()

SAMPLE_RATE = 44100
MAXP = 15  # keep 2**MAXP samples in a ring buffer
MAXOUT = 75  # number of output channels

windows = {k: scipy.signal.hann(2**k) for k in range(8, MAXP)}

# int(freqs[k] * 2**n) is the index for semitone k
# in the result of a rfft for a buffer of size n
freqs = 440 * 2 ** (np.arange(MAXOUT)/12 - 3) / SAMPLE_RATE

buf = np.zeros(shape=2**MAXP, dtype=np.float32)
bins = np.zeros(shape=MAXOUT, dtype=np.float32)
bin_buf = np.zeros(shape=MAXOUT, dtype=np.float32)
upper = 1e-7

def process_buffer(appsink):
    global bins, upper

    gst_ibuf = appsink.emit('pull-sample').get_buffer()
    gst_raw = gst_ibuf.extract_dup(0, gst_ibuf.get_size())
    ibuf = np.frombuffer(gst_raw, dtype=np.float32)
    ibuf = ibuf[-len(buf):]  # drop samples if there are too many
    buf[:-len(ibuf)] = buf[len(ibuf):]
    buf[-len(ibuf):] = ibuf

    bins[:] = 0
    for (k, w) in windows.items():
        tmp = abs(np.fft.rfft(buf[-2**k:] * w)[1:])
        tmp /= 2**k
        tmp[:20] = 0  # cut off low frequencies
        bins += tmp[(freqs * 2**k).astype(int)]

    bins = np.where(bins > 1.25*bin_buf, bins,
                    np.where(bins < 0.75*bin_buf, 0.95*bin_buf, bin_buf))
    bin_buf[:] = bins

    upper = 0.995 * upper + 0.005 * max(bins)
    if upper != 0:
        bins /= upper
    np.clip(bins, 0, 1, out=bins)

    dmx.channels[:] = 50 + bins * 200
    dmx.push()

    return False

GObject.threads_init()
GLib.set_application_name('Sound Visualization')
Gst.init(None)
dmx = artdmx.Client(MAXOUT, args.server, args.port, universe=args.universe)
pipeline = Gst.parse_launch('pulsesrc ! appsink name=sink max-buffers=1 ' +
                            'emit-signals=True ' +
                            'caps=audio/x-raw,format=F32LE,channels=1,rate={}'.format(SAMPLE_RATE))
appsink = pipeline.get_by_name('sink')
appsink.connect('new-sample', process_buffer)


def check_masks():
    if dmxmasks[args.universe]:
        pipeline.set_state(Gst.State.PLAYING)
    else:
        pipeline.set_state(Gst.State.PAUSED)
    return True

if args.force:
    pipeline.set_state(Gst.State.PLAYING)
else:
    dmxmasks = np.memmap('/dev/shm/dmxmasks', mode='r', dtype=bool)
    GLib.timeout_add_seconds(1, check_masks)

GObject.MainLoop().run()
