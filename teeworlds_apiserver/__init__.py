import asyncio
import os
import json
import copy
import re
import typing

import websockets
from aiohttp import web

from teeworlds_apiserver.econ import TeeworldsECON

RECONNECT_DELAY = 5


class TeeworldsAPIServer:

    PATTERNS = {
        'chat': r'^\[\S+\]\[chat\]: (-?\d+):(-?\d+):(.+?): (.*)$',
        'join': r'^\[\S+\]\[game\]: team_join player=\'(-?\d+):(.+?)\' team=(-?\d+|(-?\d+)->(-?\d+))$',
        'leave': r'^\[\S+\]\[game\]: leave player=\'(-?\d+):(.+?)\'',
        'kill': r'^\[\S+\]\[game\]: kill killer=\'(-?\d+):(-?\d+):(.+?)\' victim=\'(-?\d+):(-?\d+):(.+?)\' weapon=(-?\d+) special=(-?\d+)$',
        'pickup': r'^\[\S+\]\[game\]: pickup player=\'(-?\d+):(.+?)\' item=(-?\d+)$',
        'start_match': r'^\[\S+\]\[game\]: start match type=\'(.+?)\' teamplay=\'(-?\d+)\'$',
        'connect': r'^\[\S+\]\[server\]: player has entered the game. ClientID=(-?\d+) addr=(.+?)$',
    }

    def __init__(self, econ):
        self.econ = econ
        self.web_app = web.Application()
        self.web_app.add_routes([
            web.post('/command/{command}', self.route_command),
        ])
        self.subscribers = set()
        self.patterns = copy.deepcopy(self.PATTERNS)
        for k, v in self.patterns.items():
            self.patterns[k] = re.compile(v)

    async def read_econ(self):
        event = None
        while event is None:
            try:
                event = self.parse_log((await self.econ.readline()))
            except ConnectionError:
                print('Connection to ECON failed')
                await asyncio.sleep(5)
                try:
                    await self.econ.connect()
                except ConnectionError:
                    pass
        if event is not None:
            msg = json.dumps(event)
            for subscriber in self.subscribers:
                subscriber.put_nowait(msg)
        asyncio.create_task(self.read_econ())

    async def start(self):
        try:
            self.web_runner = web.AppRunner(self.web_app)
            await self.web_runner.setup()
            self.web_site = web.TCPSite(
                self.web_runner,
                os.environ['APISERVER_WEB_HOST'],
                int(os.environ['APISERVER_WEB_PORT']),
            )
            await self.web_site.start()
            await self.econ.connect()
            await websockets.serve(
                self.websocket_feed,
                os.environ['APISERVER_WS_HOST'],
                int(os.environ['APISERVER_WS_PORT']),
            )
            await self.read_econ()
        except Exception:
            asyncio.get_running_loop().stop()
            raise

    async def route_command(self, request):
        try:
            payload = await request.json()
            args = payload['args']
            if not isinstance(args, typing.Sequence):
                raise ValueError()
        except (ValueError, KeyError):
            return web.Response(status=400)
        try:
            await self.econ.command(request.match_info['command'], *args)
        except ValueError:
            return web.Response(status=400, reason='Invalid command')
        return web.Response(status=200)

    def parse_log(self, line):
        for event, pattern in self.patterns.items():
            match = re.match(pattern, line)
            if not match:
                continue
            r = {}
            if event == 'chat':
                r.update({
                    'client_id': int(match.group(1)),
                    'team': int(match.group(2)),
                    'player': match.group(3),
                    'message': match.group(4),
                })
            elif event == 'join':
                if match.groups()[-1] is not None:
                    r.update({
                        'previous_team': int(match.group(4)),
                        'team': int(match.group(5)),
                    })
                else:
                    r.update({
                        'team': int(match.group(3)),
                    })
                r.update({
                    'client_id': int(match.group(1)),
                    'player': match.group(2),
                })
            elif event == 'leave':
                r.update({
                    'client_id': int(match.group(1)),
                    'player': match.group(2),
                })
            elif event == 'kill':
                r.update({
                    'killer': {
                        'client_id': int(match.group(1)),
                        'team': int(match.group(2)),
                        'player': match.group(3),
                    },
                    'victim': {
                        'client_id': int(match.group(4)),
                        'team': int(match.group(5)),
                        'player': match.group(6),
                    },
                    'weapon': int(match.group(7)),
                    'special': int(match.group(8)),
                })
            elif event == 'pickup':
                r.update({
                    'client_id': int(match.group(1)),
                    'player': match.group(2),
                    'item': int(match.group(3)),
                })
            elif event == 'start_match':
                r.update({
                    'game_type': match.group(1),
                    'teamplay': int(match.group(2)),
                })
            elif event == 'connect':
                r.update({
                    'client_id': match.group(1),
                    'address': match.group(2),
                })
            r.update({'type': event})
            break
        else:
            return None
        return r

    async def websocket_feed(self, ws, path):
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                await ws.send(event)
                queue.task_done()
        except websockets.ConnectionClosedError:
            pass
        finally:
            self.subscribers.remove(queue)


def main():
    loop = asyncio.get_event_loop()
    econ = TeeworldsECON(
        os.environ['APISERVER_ECON_HOST'],
        os.environ['APISERVER_ECON_PORT'],
        os.environ['APISERVER_ECON_PASSWORD'],
    )
    server = TeeworldsAPIServer(econ)
    loop.call_soon(asyncio.create_task, server.start())
    try:
        loop.run_forever()
    finally:
        loop.close()
