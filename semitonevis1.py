#!/usr/bin/python3

import numpy as np
import scipy.signal
from gi.repository import GObject, Gst, GstBase

def get_class(t, k):
    element_class = GObject.type_class_peek(t.__gtype__)
    element_class.__class__ = k
    return element_class

XR = 25

class SemitoneVis(GstBase.BaseTransform):

    def __init__(self):
        GstBase.BaseTransform.__init__(self)
        self.obuf_array = bytearray(3*XR)
        self.obuf = np.ndarray(shape=3*XR, buffer=self.obuf_array, dtype='uint8')

    def my_stft(self, signal, n):
        res = abs(np.fft.rfft(signal[-n:] * self.windows[n])[1:])
        res /= n
        return res

    def do_set_caps(self, incaps, outcaps):
        _, self.rate = incaps.get_structure(0).get_int('rate')
        self.buf = np.zeros(dtype='float64', shape=2**15)
        self.upper = 1e-7

        self.windows = dict()
        self.freqs = dict()
        for i in range(1, 17):
            self.windows[2**i] = scipy.signal.hann(2**i)
            self.freqs[2**i] = np.fft.rfftfreq(2**i, 1/self.rate)

        self.bin_buf = np.zeros(dtype='float64', shape=75)

        return True

    def do_transform_caps(self, direction, caps, flt):
        if direction == Gst.PadDirection.SRC:
            return Gst.caps_from_string('audio/x-raw, format=S16LE, channels=1')
        elif direction == Gst.PadDirection.SINK:
            ok, rate = caps.get_structure(0).get_int('rate')
            if ok:
                return Gst.caps_from_string('video/x-raw, format=RGB, width={}, height={}, framerate=1/{}'.format(25, 1, 25))
            else:
                return Gst.caps_from_string('video/x-raw')

    def do_transform(self, gst_ibuf, gst_obuf):
        ibuf = np.frombuffer(gst_ibuf.extract_dup(0, gst_ibuf.get_size()), dtype='short') / 65535

        self.buf[:-len(ibuf)] = self.buf[len(ibuf):]
        self.buf[-len(ibuf):] = ibuf

        C = 20

        bins = np.zeros(shape=7*12, dtype=np.float64)
        f = 440 * 2 ** (np.arange(-3*12, 4*12)/12) * len(self.buf) / self.rate
        for k in range(0, 8):
            tmp = self.my_stft(self.buf, 2**(15-k))
            tmp[:C] = 0
            bins += tmp[(f / 2**k).astype(int)]

        bins = bins[:75]

        bins = np.where(bins > 1.25*self.bin_buf, bins, np.where(bins < 0.75*self.bin_buf, 0.95*self.bin_buf, self.bin_buf))
        self.bin_buf[:] = bins

        self.upper = 0.995 * self.upper + 0.005 * max(bins)
        if self.upper != 0:
            bins /= self.upper

        self.obuf[:75] = 50 + np.clip(bins, 0, 1) * 200
        #print('OUT', self.obuf)

        gst_obuf.fill(0, memoryview(self.obuf_array))
        return Gst.FlowReturn.OK


SemitoneVisT = GObject.type_register(SemitoneVis)
SemitoneVisC = get_class(SemitoneVisT, Gst.ElementClass)
SemitoneVisC.set_metadata('Semitone Visualization', 'Converter/Visualisation', 'Display a frequency analysis with semitone precision', 'Benjamin Richter <br@waldteufel.eu>')
SemitoneVisC.add_pad_template(Gst.PadTemplate.new('sink', Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.caps_from_string('audio/x-raw')))
SemitoneVisC.add_pad_template(Gst.PadTemplate.new('src', Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.caps_from_string('video/x-raw')))

Gst.Element.register(None, 'semitonevis', 0, SemitoneVis)
