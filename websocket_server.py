#!/usr/bin/env python3

import asyncio
import websockets
import json
import os
from collections import defaultdict

ANNOTATIONS = []

USERS = set()

USER_NAMES = {}

TIERS = {}

ANNOTATION_FILE = ''

async def send(message):
    websockets.broadcast(USERS, json.dumps(message))

async def connect(websocket):
    global ANNOTATIONS, USERS, USER_NAMES, TIERS
    wid = websocket.id.hex
    try:
        USER_NAMES[wid] = 'user' + str(len(USER_NAMES)+1)
        USERS.add(websocket)
        await websocket.send(json.dumps({
            'type': 'load',
            'annotations': ANNOTATIONS,
            'tiers': TIERS,
            'user_names': USER_NAMES,
            'active_users': [u.id.hex for u in USERS],
            'user': wid,
        }))
        await send({
            'type': 'new_user',
            'user': wid,
            'name': USER_NAMES[wid]
        })
        async for message in websocket:
            event = json.loads(message)
            action = event.get('type')
            if action == 'rename_user':
                name = event['name']
                USER_NAMES[wid] = name
                await send({
                    'type': 'rename_user',
                    'user': wid,
                    'name': name
                })
            elif action == 'add_tier':
                tid = max(TIERS.keys()) + 1
                TIERS[tid] = event.get('name', 'Tier %s' % tid)
                await send({
                    'type': 'add_tier',
                    'user': wid,
                    'id': tid,
                    'name': TIERS[tid],
                })
            elif action == 'rename_tier':
                tid = event.get('id')
                if tid not in TIERS:
                    continue
                TIERS[tid] = event['name']
                await send({
                    'type': 'rename_tier',
                    'user': wid,
                    'id': tid,
                    'name': event['name'],
                })
            elif action == 'delete_tier':
                tid = event.get('id')
                if tid not in TIERS:
                    continue
                ANNOTATIONS = [a for a in ANNOTATIONS if a['tier'] != tid]
                del TIERS[tid]
                await send({
                    'type': 'delete_tier',
                    'user': wid,
                    'id': tid,
                })
            elif action == 'add':
                ann = event['annotation']
                ANNOTATIONS.append(ann)
                await send({
                    'type': 'add',
                    'user': wid,
                    'annotation': ann,
                })
            elif action == 'remove':
                ann = event['annotation']
                ANNOTATIONS = [a for a in ANNOTATIONS if a != ann]
                await send({
                    'type': 'remove',
                    'user': wid,
                    'annotation': ann,
                })
            elif action == 'edit':
                old = event['old']
                new = event['new']
                ANNOTATIONS = [a for a in ANNOTATIONS if a != old]
                ANNOTATIONS.append(new)
                await send({
                    'type': 'edit',
                    'user': wid,
                    'old': old,
                    'new': new,
                })
            with open(ANNOTATION_FILE, 'w') as fout:
                fout.write(json.dumps({
                    'annotations': ANNOTATIONS,
                    'users': USER_NAMES,
                    'tiers': TIERS,
                }))
    finally:
        USERS.remove(websocket)
        await send({
            'type': 'user_left',
            'user': wid,
        })

async def run_server(host, port, directory):
    global ANNOTATIONS, USER_NAMES, ANNOTATION_FILE, TIERS
    ANNOTATION_FILE = os.path.join(directory, 'annotations')
    with open(ANNOTATION_FILE) as fin:
        s = fin.read() or '[]'
        try:
            blob = json.loads(s)
            ANNOTATIONS = blob['annotations']
            USER_NAMES = blob['users']
            TIERS = {int(k):v for k,v in blob['tiers'].items()}
        except Exception as e:
            print(e)
            ANNOTATIONS = []
            USER_NAMES = {}
            TIERS = {1: 'Tier 1'}
    async with websockets.serve(connect, host, port):
        await asyncio.Future()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('host', action='store')
    parser.add_argument('port', type=int, default=5000)
    parser.add_argument('directory', action='store')
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port, args.directory))
