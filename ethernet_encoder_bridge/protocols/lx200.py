import asyncio
import requests
import functools

import logging

import lx200.parser
import lx200.commands
import lx200.responses

logger = logging.getLogger('ethernet-encoder-bridge.lx200')


class LX200Protocol(asyncio.Protocol):

    def __init__(self, store, server_path, ra_id='RA', dec_id='DEC', *args, **kwargs):
        self.transport = None
        self.store = store
        self.server_path = server_path
        self.ra_id = ra_id
        self.dec_id = dec_id

        self.parser = lx200.parser.Parser()

        self.dispatch = {
            lx200.commands.SlewToTarget: self.do_goto,
            lx200.commands.SlewToTargetObject: self.do_goto,
            lx200.commands.SyncDatabase: self.do_sync,
            lx200.commands.HaltAll: self.halt,
            lx200.commands.HaltEastward: functools.partial(self.halt_axis_slew, axis_id=self.ra_id),
            lx200.commands.HaltWestward: functools.partial(self.halt_axis_slew, axis_id=self.ra_id),
            lx200.commands.HaltNorthwawrd: functools.partial(self.halt_axis_slew, axis_id=self.dec_id),
            lx200.commands.HaltSouthward: functools.partial(self.halt_axis_slew, axis_id=self.dec_id),

            lx200.commands.MoveEast: functools.partial(self.slew_axis_relative, axis_id=self.ra_id, direction=1),
            lx200.commands.MoveWest: functools.partial(self.slew_axis_relative, axis_id=self.ra_id, direction=-1),
            lx200.commands.MoveNorth: functools.partial(self.slew_axis_relative, axis_id=self.dec_id, direction=1),
            lx200.commands.MoveSouth: functools.partial(self.slew_axis_relative, axis_id=self.dec_id, direction=-1),
        }

    def connection_made(self, transport):
        self.transport = transport
        transport.set_write_buffer_limits(high=0, low=0)
        logger.info('Connected: {}'.format(transport.get_extra_info('socket', 'peername')))

    def data_received(self, data):
        decoded_data = data.decode('ascii')
        self.parser.feed(decoded_data)

        logger.debug('<< {}'.format(decoded_data))

        while self.parser.output:
            command = self.parser.output.pop()
            self.store.commit_command(command)

            response = lx200.responses.for_command(command)

            action = self.dispatch.get(command.__class__, None)
            if action:
                action(command=command, response=response)

            self.store.fill_response(response)

            logger.debug('>> {}'.format(repr(response)))
            logger.debug('>> {}'.format(str(response)))

            self.transport.write(bytes(str(response), 'ascii'))

    def do_goto(self, *args, **kwargs):
        return self.__call_axis_action('goto')

    def do_sync(self, *args, **kwargs):
        return self.__call_axis_action('sync')

    def __call_axis_action(self, action='goto'):
        if 'mount.target.right_ascencion' in self.store:
            payload = self.store['mount.target.right_ascencion']
            requests.put('{}/api/devices/{}/{}/astronomical'.format(self.server_path, self.ra_id, action), json=payload)

        if 'mount.target.declination' in self.store:
            payload = self.store['mount.target.declination']
            requests.put('{}/api/devices/{}/{}/angle'.format(self.server_path, self.dec_id, action), json=payload)

    def halt_axis_slew(self, axis_id, *args, **kwargs):
        payload = {
            'degrees': 0,
            'minutes': 0,
            'seconds': 0,
        }
        return requests.put('{}/api/devices/{}/run_speed'.format(self.server_path, axis_id), json=payload)

    def halt_axis(self, axis_id, *args, **kwargs):
        return requests.put('{}/api/devices/{}/halt'.format(self.server_path, axis_id))

    def halt(self, *args, **kwargs):
        return (self.halt_axis(self.ra_id), self.halt_axis(self.dec_id))

    def slew_axis_relative(self, axis_id, direction=1, *args, **kwargs):
        # mount.slew_rate['value'] -> offset in degrees
        offset_map = {
            'max': {
                'degrees': 2
            },
            'finding': {
                'minutes': 30
            },
            'centering': {
                'seconds': 30
            },
            'guiding': {
                'seconds': 1
            }
        }
        payload = {
            'degrees': 0,
            'minutes': 0,
            'seconds': 0,
        }
        payload.update(offset_map[self.store['mount.slew.rate']['value']])
        for (k,v) in payload.items():
            payload[k] = v*direction

        return requests.put('{}/api/devices/{}/run_speed'.format(self.server_path, axis_id), json=payload)
