#!/usr/bin/env python3

import argparse
import subprocess
import tempfile
import os
import pathlib

static_files = [
    'index.html',
    'audioweb.js',
    'jquery.js',
]

parser = argparse.ArgumentParser()
parser.add_argument('-p', help='HTTP port', type=int, default=80)
parser.add_argument('-w', help='Websocket port', type=int, default=5000)
parser.add_argument('audio', action='store')
parser.add_argument('annotations', help='annotation file', action='store')
parser.add_argument('-n', help="host name (default 'localhost')",
                    action='store', default='localhost')
args = parser.parse_args()

cwd = os.path.dirname(os.path.realpath(__file__))
hpath = os.path.join(cwd, 'http_server.py')
wpath = os.path.join(cwd, 'websocket_server.py')

if not pathlib.Path(args.annotations).exists():
    with open(args.annotations, 'w') as fout:
        fout.write('\n')

with tempfile.TemporaryDirectory() as tempd:
    print(tempd)
    os.symlink(os.path.abspath(args.audio), os.path.join(tempd, 'audio'))
    os.symlink(os.path.abspath(args.annotations), os.path.join(tempd, 'annotations'))
    static = os.path.join(cwd, 'static')
    for st in static_files:
        os.symlink(os.path.join(static, st), os.path.join(tempd, st))
    with open(os.path.join(tempd, 'constants.js'), 'w') as fout:
        fout.write('var WS_ADDR = "ws://%s:%s/";\n' % (args.n, args.w))
    hproc = subprocess.Popen(['python3', hpath, str(args.p), tempd])
    wproc = subprocess.Popen(['python3', wpath, args.n, str(args.w), tempd])
    try:
        hproc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        hproc.kill()
        wproc.kill()
