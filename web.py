#!/usr/bin/python3

import artdmx
import shlex
import io
import numpy as np
from flask import *

app = Flask(__name__)

MAXCH = 76
UNIVERSES = 16
dmxmasks = np.memmap('/dev/shm/dmxmasks', mode='r',
                     shape=(MAXCH, UNIVERSES), dtype=bool)
dmxchannels = np.memmap('/dev/shm/dmxchannels', mode='r',
                        shape=(MAXCH, UNIVERSES), dtype='u1')


@app.context_processor
def add_checks():
    def check_mask(universe, channel):
        return 'On' if dmxmasks[channel, universe] else 'Off'
    return dict(check_mask=check_mask)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        for k, v in request.form.items():
            c = artdmx.Client(76, 'localhost', universe=int(k, 0))
            c.parse(*shlex.split(v))
            c.push()
        return redirect('/lights', code=303)
    else:
        return render_template('index.html')


@app.route("/masks")
def masks():
    resp = Response(dmxmasks.tostring(),
                    mimetype='application/octet-stream')
    resp.headers['X-MAXCH'] = MAXCH
    resp.headers['X-UNIVERSES'] = UNIVERSES
    return resp


@app.route("/channels")
def channels():
    resp = Response(dmxchannels.tostring(),
                    mimetype='application/octet-stream')
    resp.headers['X-MAXCH'] = MAXCH
    resp.headers['X-UNIVERSES'] = UNIVERSES
    return resp


@app.route("/state")
def state():
    return render_template('state.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8989, debug=True, use_reloader=False)
