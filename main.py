#!/usr/bin/python3

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--dry-run", help="show output locally instead of sending over ArtDMX", action="store_true")
args = parser.parse_args()

from gi.repository import GObject, Gst

GObject.threads_init()
Gst.init(None)

import semitonevis1, frequencyvis, artdmxsink

pipeline = Gst.Pipeline()

src = Gst.ElementFactory.make('autoaudiosrc', None)
vis = Gst.ElementFactory.make('semitonevis', None)
conv = Gst.ElementFactory.make('autovideoconvert', None)
if args.dry_run:
    sink = Gst.ElementFactory.make('autovideosink', None)
else:
    dmxsink = Gst.ElementFactory.make('artdmxsink', None)

pipeline.add(src)
pipeline.add(vis)
pipeline.add(conv)
if args.dry_run:
    pipeline.add(sink)
else:
    pipeline.add(dmxsink)

src.link(vis)
vis.link(conv)
if args.dry_run:
    conv.link(sink)
else:
    conv.link(dmxsink)

pipeline.set_state(Gst.State.PLAYING)
GObject.MainLoop().run()
