#!/usr/bin/python3

import numpy as np
import scipy.signal
from gi.repository import GObject, Gst, GstBase

def get_class(t, k):
    element_class = GObject.type_class_peek(t.__gtype__)
    element_class.__class__ = k
    return element_class

XR = 1024
YR = 16

class FrequencyVis(GstBase.BaseTransform):

    def __init__(self):
        GstBase.BaseTransform.__init__(self)
        self.obuf_array = bytearray(3*XR*YR)
        self.obuf = np.ndarray(shape=(YR, XR, 3), buffer=self.obuf_array, dtype='uint8')

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

        return True

    def do_transform_caps(self, direction, caps, flt):
        if direction == Gst.PadDirection.SRC:
            return Gst.caps_from_string('audio/x-raw, format=S16LE, channels=1')
        elif direction == Gst.PadDirection.SINK:
            ok, rate = caps.get_structure(0).get_int('rate')
            if ok:
                return Gst.caps_from_string('video/x-raw, format=RGB, width={}, height={}, framerate=1/{}'.format(XR, YR, 50))
            else:
                return Gst.caps_from_string('video/x-raw')

    def do_transform(self, gst_ibuf, gst_obuf):
        ibuf = np.frombuffer(gst_ibuf.extract_dup(0, gst_ibuf.get_size()), dtype='short') / 65535

        self.buf[:-len(ibuf)] = self.buf[len(ibuf):]
        self.buf[-len(ibuf):] = ibuf

        C = 20
        C2 = 256

        bins = np.zeros(shape=2**14, dtype=np.float64)
        for k in range(0, 8):
            tmp = self.my_stft(self.buf, 2**(15-k))
            tmp[:C] = 0
            for i in range(2**k):
                bins[i::2**k] += tmp

        bins = bins[C2:C2+XR]
        self.upper = 0.99 * self.upper + 0.01 * max(bins)
        if self.upper != 0:
            bins /= self.upper

        for y in range(YR):
            v = (bins - y/(YR-1))
            self.obuf[YR-y-1,:,1] = np.where(v >= 0, np.exp(-v) * 128 + 127, 0)

        for i in range(-48, 48):
            x = 440 * 2 ** (i/12) * 2**16 / self.rate
            x -= C2
            if 0 <= x < XR:
                self.obuf[:,x,2] = 255
                if i%12 == 0: self.obuf[:,x,0] = 255

        x = 440 * 2**16 / self.rate
        x -= C2
        if 0 <= x < XR:
            self.obuf[:,x-1:x+2,:] /= 2
            self.obuf[:,x-1:x+2,:] += 127

        gst_obuf.fill(0, memoryview(self.obuf_array))
        return Gst.FlowReturn.OK


FrequencyVisT = GObject.type_register(FrequencyVis)
FrequencyVisC = get_class(FrequencyVisT, Gst.ElementClass)
FrequencyVisC.set_metadata('Frequency Visualization', 'Converter', 'Display a frequency analysis', 'Benjamin Richter <br@waldteufel.eu>')
FrequencyVisC.add_pad_template(Gst.PadTemplate.new('sink', Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.caps_from_string('audio/x-raw')))
FrequencyVisC.add_pad_template(Gst.PadTemplate.new('src', Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.caps_from_string('video/x-raw')))

Gst.Element.register(None, 'frequencyvis', 0, FrequencyVis)
