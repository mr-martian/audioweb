#!/usr/bin/env python3

import http.server
import threading
import parselmouth
import urllib
import pathlib
import numpy
import PIL.Image
import socketserver
import os
import functools

THE_SPECTROGRAM_LOCK = threading.Lock()

class ImageRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path.strip('/').startswith('spectrogram'):
            THE_SPECTROGRAM_LOCK.acquire()
            self.ensure_spectrogram_exists(parts.path)
            THE_SPECTROGRAM_LOCK.release()
        return super().do_GET()
    def ensure_spectrogram_exists(self, path):
        pth = pathlib.Path(self.directory) / path.strip('/')
        if pth.exists():
            return
        args = path.split('.')[0].split('_')
        try:
            wl = int(args[1]) / 1000.0
            mf = int(args[2])
            dr = int(args[3])
        except:
            return
        audio = pathlib.Path(self.directory) / 'audio'
        snd = parselmouth.Sound(str(audio))
        duration = snd.get_total_duration()
        ts = duration / 10000.0
        spec_raw = snd.to_spectrogram(
            window_length=wl, time_step=ts, maximum_frequency=mf)
        spec = 10 * numpy.log10(numpy.flip(spec_raw.values, 0))
        mx = spec.max()
        spec = (spec.clip(mx-dr, mx) - mx) * (-255.0 / dr)
        img = PIL.Image.fromarray(spec)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        print('saving to', str(pth))
        img.save(pth)

class BigQueueServer(socketserver.ThreadingTCPServer):
    request_queue_size = 100

def run_server(port, directory):
    handle = functools.partial(ImageRequestHandler, directory=directory)
    with BigQueueServer(('', port), handle) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('')
            os._exit(0)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, default=80)
    parser.add_argument('directory', action='store')
    args = parser.parse_args()
    run_server(args.port, args.directory)
