#!/usr/bin/env python3

import sys

import argparse
import signal
import atexit
import logging

import asyncio
from aiohttp import web
import socketio
from socketio.exceptions import ConnectionError

import functools

import json
import yaml

import lx200.store

from .protocols import LX200Protocol, StellariumProtocol


logger = logging.getLogger('ethernet-encoder-bridge')

store = lx200.store.Store()


def build_protocol_factory(protocol, store, server, ra_id, dec_id, *args, **kwargs):
    def __inner(*args, **kwargs):
        return protocol(store, server, ra_id, dec_id, *args, **kwargs)
    return __inner



class ScopeStoreServer:

    def __init__(self, host, port, store):
        self.host = host
        self.port = port
        self.store = store

        routes = web.RouteTableDef()

        @routes.get('/')
        async def json_store_status(request):
            return web.json_response(request.app['scope_store'])

        app = self.app = web.Application()
        app['scope_store'] = store

        app.add_routes(routes)
        self.runner = web.AppRunner(app)

    async def start(self):

        await self.runner.setup()

        site = self.site = web.TCPSite(self.runner, self.host, self.port)

        await self.site.start()


class WSUpdater:
    def __init__(self, encoder_server_path, store, ra_axis_id, dec_axis_id):
        self.server_path = encoder_server_path
        self.store = store
        self.ra_axis_id = ra_axis_id
        self.dec_axis_id = dec_axis_id

        sio = self.sio = socketio.AsyncClient()

        @sio.on('disconnect')
        async def onerror(payload=None):
            await asyncio.sleep(1)
            await self.start()

        @sio.on('position')
        async def update_position(payload):
            parameter_map = {
                self.ra_axis_id: [
                    ('position_astronomical', 'mount.right_ascencion'),
                    ('target_astronomical', 'mount.target.right_ascencion'),
                ],
                self.dec_axis_id: [
                    ('position_angle', 'mount.declination'),
                    ('target_angle', 'mount.target.declination'),
                ]
            }

            for src, dest in parameter_map[payload['id']]:
                self.store[dest].update(payload[src])

            if payload['id'] == self.ra_axis_id:
                self.store['mount.alignment_status'].update({
                    'is_tracking': payload['tracking']
                })

    async def start(self):
        async def __connect():
            while True:
                try:
                    await self.sio.connect(self.server_path)
                except (ConnectionError, ValueError):
                    pass
                else:
                    break

                await asyncio.sleep(1)

        return asyncio.create_task(__connect())


async def run(args):

    loop = asyncio.get_running_loop()

    lx200_factory = build_protocol_factory(LX200Protocol, store, args.encoder_server, args.ra_axis_id, args.dec_axis_id)
    stellarium_factory = build_protocol_factory(StellariumProtocol, store, args.encoder_server, args.ra_axis_id, args.dec_axis_id)

    lx200_server = await loop.create_server(lx200_factory, args.host, args.port)
    stellarium_server = await loop.create_server(stellarium_factory, args.host, args.stellarium_port)

    store_server = ScopeStoreServer(args.host, args.web_port, store)
    await store_server.start()

    wsupdater = WSUpdater(args.encoder_server, store, args.ra_axis_id, args.dec_axis_id)
    await(wsupdater.start())

    logger.info('LX200 <-> Ethernet Encoder Bridge')
    logger.info('Serving on {}'.format(lx200_server.sockets[0].getsockname()))

    logger.info('Stellarium <-> Ethernet Encoder Bridge')
    logger.info('Serving on {}'.format(stellarium_server.sockets[0].getsockname()))

    logger.info('Serving state on http://{}:{}'.format(args.host, args.web_port))


def save_store(store, store_path, format='json'):
    if format == 'json':
        serialized = store.toJSON()
    else:
        serialized = store.toYAML()

    with open(store_path, 'w', encoding='utf-8') as f:
        f.write(serialized)


def load_store(store, store_path, format='json'):
    contents = ''
    try:
        with open(store_path, 'r') as f:
            contents = f.read()
    except FileNotFoundError:
        return

    try:
        data = json.loads(contents)
        store.update(data)
    except json.decoder.JSONDecodeError:
        data = yaml.load(contents)
        store.update(data)


def main():
    parser = argparse.ArgumentParser(description='Bridge between ethernet-encoder-servo and LX200/Stellarium protocol')

    parser.add_argument('--encoder-server', required=False, default='http://localhost:5000', help='ethernet encoder server url (%(default)s)')
    parser.add_argument('--ra-axis-id', required=False, default='RA', help='Id of axis to map to Right Ascencion (%(default)s)')
    parser.add_argument('--dec-axis-id', required=False, default='DEC', help='Id of axis to map to Declination (%(default)s)')

    parser.add_argument('--port', type=int, required=False, default=7634, help='TCP port for the LX200 server (%(default)s)')
    parser.add_argument('--stellarium-port', type=int, required=False, default=10001, help='TCP port for the Stellarium server (%(default)s)')
    parser.add_argument('--web-port', type=int, required=False, default=8081, help='TCP port for the status server (%(default)s)')
    parser.add_argument('--host', type=str, required=False, default='127.0.0.1', help='Host for all the servers (%(default)s)')

    parser.add_argument('--store-path', type=str, required=False, default='', help='Path to load and save scope status store')
    parser.add_argument('--store-format', required=False, default='json',  choices=['json', 'yaml'], help='Output format for store, default: JSON')
    parser.add_argument('--state-save-interval', required=False, default=1000,  type=int, help='Interval in milliseconds between state saving (%(default)s)')

    parser.add_argument('--verbose', required=False, default=False, action='store_true')

    args = parser.parse_args()

    logging.basicConfig()
    logger.setLevel(logging.INFO)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()

    if args.store_path:

        save_interval = max(args.state_save_interval, 250)
        __save_store = functools.partial(save_store, store=store, store_path=args.store_path, format=args.store_format)

        async def background_save():
            while True:
                __save_store()
                await asyncio.sleep(save_interval / 1000.0)

        atexit.register(__save_store)
        loop.add_signal_handler(signal.SIGHUP, __save_store)

        loop.create_task(background_save())

        loop.add_signal_handler(signal.SIGTERM, functools.partial(sys.exit, 0))
        loop.add_signal_handler(signal.SIGINT, functools.partial(sys.exit, 0))
        loop.add_signal_handler(signal.SIGQUIT, functools.partial(sys.exit, 0))

    load_store(store, args.store_path, args.store_format)

    loop.run_until_complete(run(args))
    loop.run_forever()
