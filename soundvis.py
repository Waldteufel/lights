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
parser.add_argument('-f', '--force', dest='force', action='store_true',
                    default=False, help='ignore dmxmasks')

args = parser.parse_args()

SAMPLE_RATE = 44100
MINP = 8   # analyze at least 2**MINP samples at once
MAXP = 15  # keep 2**MAXP samples in a ring buffer
MAXOUT = 75  # number of output channels

# precomputed windowing functions for several time-scales
windows = {k: scipy.signal.hann(2**k) for k in range(MINP, MAXP)}

# int(freqs[k] * 2**n) is the index for semitone k
# in the result of a rfft for a buffer of size n
freqs = 440 * 2 ** (np.arange(MAXOUT)/12 - 3) / SAMPLE_RATE

buf = np.zeros(shape=2**MAXP, dtype=np.float32)
bins = np.zeros(shape=MAXOUT, dtype=np.float32)

smooth_bins = np.zeros(shape=MAXOUT, dtype=np.float32)
smooth_maximum = 1e-7


def process_buffer(appsink):
    global bins, smooth_maximum

    # get samples from gstreamer
    gst_ibuf = appsink.emit('pull-sample').get_buffer()
    gst_raw = gst_ibuf.extract_dup(0, gst_ibuf.get_size())
    ibuf = np.frombuffer(gst_raw, dtype=np.float32)

    # drop samples if there are too many
    ibuf = ibuf[-len(buf):]

    # write samples to ring buffer
    buf[:-len(ibuf)] = buf[len(ibuf):]
    buf[-len(ibuf):] = ibuf

    # clear bins
    bins[:] = 0

    # analyze frequencies on multiple time-scales
    for (k, w) in windows.items():
        # decompose buffer into frequency components
        tmp = abs(np.fft.rfft(buf[-2**k:] * w)[1:])
        tmp /= 2**k

        # cut off low frequencies
        tmp[:20] = 0

        # pick frequencies for each semitone and accumulate
        bins += tmp[(freqs * 2**k).astype(int)]

    # the np.where(...) below is equivalent to
    #
    #    if (bins[i] > 1.25 * smooth_bins[i])
    #       // take new (higher) value
    #       smooth_bins[i] = bins[i];
    #    else if (bins[i] < 0.75 * smooth_bins[i])
    #       // slowly fade to lower values
    #       smooth_bins[i] = 0.95 * smooth_bins[i];
    #    else
    #       // keep old value
    #       smooth_bins[i] = smooth_bins[i];

    smooth_bins[:] = np.where(bins > 1.25 * smooth_bins,
                              bins,
                              np.where(bins < 0.75 * smooth_bins,
                                       0.95 * smooth_bins,
                                       smooth_bins))

    # the following normalization shall not affect the
    # smoothing logic when the next samples arrive, so
    # use bins for a temporary copy of smooth_bins
    bins[:] = smooth_bins

    # let smooth_maximum follow max(bins) smoothly ("low-pass filter")
    smooth_maximum = 0.995 * smooth_maximum + 0.005 * max(bins)
    if smooth_maximum != 0:
        bins /= smooth_maximum

    # since we used a time-smoothened maximum, the normalization
    # is not perfect and we have to clip our results
    np.clip(bins, 0, 1, out=bins)

    # send out the color channels
    dmx.channels[:] = 50 + bins * 200
    dmx.push()

    return False


GObject.threads_init()
GLib.set_application_name('Sound Visualization')
Gst.init(None)

dmx = artdmx.Client(MAXOUT, args.server, args.port, universe=args.universe)
pipeline = Gst.parse_launch("""
    pulsesrc !
    appsink name=sink max-buffers=1 emit-signals=True
        caps=audio/x-raw,format=F32LE,channels=1,rate={}
""".format(SAMPLE_RATE))
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
