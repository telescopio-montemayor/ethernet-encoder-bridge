import asyncio
import requests
import struct
import time

import math

import attr

import logging

import lx200.commands

logger = logging.getLogger('lx200-bridge.stellarium')


def decimal_to_dms(angle):
    sign = 1.0
    if angle < 0:
        sign = -1.0
    angle = math.fabs(angle)

    degrees = math.floor(angle)

    minutes_float = (angle - degrees) * 60
    minutes = math.floor(minutes_float)

    seconds = (minutes_float - minutes) * 60

    degrees = degrees*sign
    minutes = minutes*sign
    seconds = seconds*sign
    return (degrees, minutes, seconds)


@attr.s
class AnglePosition:
    degrees = attr.ib(default=0)
    minutes = attr.ib(default=0)
    seconds = attr.ib(default=0)

    def to_decimal(self):
        return self.degrees + self.minutes / 60.0 + self.seconds / 3600.0

    def to_dict(self):
        return {
            'degrees': self.degrees,
            'minutes': self.minutes,
            'seconds': self.seconds
        }

    @classmethod
    def from_decimal(cls, angle):
        degrees, minutes, seconds = decimal_to_dms(angle)
        return cls(degrees, minutes, seconds)


@attr.s
class AstronomicalPosition:
    hours = attr.ib(default=0)
    minutes = attr.ib(default=0)
    seconds = attr.ib(default=0)
    longitude = attr.ib(default=None)

    def to_decimal(self):
        return self.hours + self.minutes / 60.0 + self.seconds / 3600.0

    @classmethod
    def from_decimal(cls, angle):
        hours, minutes, seconds = decimal_to_dms(angle)
        return cls(hours, minutes, seconds)

    def to_dict(self):
        return {
            'hours':   self.hours,
            'minutes': self.minutes,
            'seconds': self.seconds,
        }


# Many parts shamleslly copied from https://github.com/juanmb/SkyPointer/

def decode_goto_packet(data):
    """Decode Stellarium client->server "goto" packet"""
    fields = struct.unpack('<HHQIi', data)
    ra = AstronomicalPosition.from_decimal(fields[3]*12.0/0x80000000)
    dec = AnglePosition.from_decimal(fields[4]*180.0/0x80000000)
    return (ra, dec)


def encode_position_packet(ra, dec):
    """Encode Stellarium server->client "current postion" packet"""
    ra = int((ra.to_decimal() % 24)/12.0*0x80000000)
    dec = int(dec.to_decimal()/180.0*0x80000000)
    return struct.pack('<HHQIii', 24, 0, int(time.time()*1e6), ra, dec, 0)


class StellariumProtocol(asyncio.Protocol):

    def __init__(self, store, server_path, ra_id='RA', dec_id='DEC', *args, **kwargs):
        self.transport = None
        self.store = store
        self.server_path = server_path
        self.ra_id = ra_id
        self.dec_id = dec_id

    def connection_made(self, transport):
        self.transport = transport
        transport.set_write_buffer_limits(high=0, low=0)
        logger.info('Client connected: {}'.format(transport.get_extra_info('socket', 'peername')))

    def data_received(self, data):
        ra, dec = decode_goto_packet(data)

        set_ra = lx200.commands.SetTargetRightAscencion(**ra.to_dict())
        set_dec = lx200.commands.SetTargetDeclination(**dec.to_dict())

        logger.debug('Goto: RA {}  DEC {}'.format(ra, dec))

        self.store.commit_command(set_ra)
        self.store.commit_command(set_dec)

        if 'mount.target.right_ascencion' in self.store:
            payload = self.store['mount.target.right_ascencion']
            requests.put('{}/api/devices/{}/{}/astronomical'.format(self.server_path, self.ra_id, 'goto'), json=payload)

        if 'mount.target.declination' in self.store:
            payload = self.store['mount.target.declination']
            requests.put('{}/api/devices/{}/{}/angle'.format(self.server_path, self.dec_id, 'goto'), json=payload)

        current_ra = AstronomicalPosition(**self.store['mount.right_ascencion'])
        current_dec = AnglePosition(**self.store['mount.declination'])

        logger.debug('Sent current position: RA {}  DEC {}'.format(current_ra, current_dec))

        self.transport.write(encode_position_packet(current_ra, current_dec))
