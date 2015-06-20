import asyncio
import json
import logging
import logging.handlers
import os

import aiohttp
import aiohttp.server
import aiohttp.websocket


class BadEvent(Exception):
    pass


# This isn't really much of a thing. I planned it to be something
# I could use for firing alerts, but in reality none of my devices
# specify severities.
SEVERITIES = ['INFO', 'ERROR', 'WARNING', 'DEBUG']
CLIENTS = []


def validate_parse_event(data):
    def _assert(thing, reason):
        if not thing:
            raise BadEvent(reason)

    try:
        envelope = json.loads(data)
    except:
        raise BadEvent('Invalid JSON')

    _assert('event' in envelope, 'Bad envelope')
    event = envelope['event']
    _assert('sender' in event, 'No sender in event')
    if 'severity' in event:
        _assert(event['severity'] in SEVERITIES,
                'Bad severity')
    return event


class Handler(aiohttp.server.ServerHttpProtocol):
    def __init__(self, *args, **kwargs):
        super(Handler, self).__init__(*args, **kwargs)
        self.clients = CLIENTS

    def get_static(self, message):
        data = None
        pieces = message.path.split('/')
        if len(pieces) != 3:
            # Malformed or invalid request
            return aiohttp.Response(self.writer, 404)
        fn = pieces[2]
        if not os.path.isfile(fn):
            return aiohttp.Response(self.writer, 404)

        with open(fn) as f:
            data = f.read()
            resp = aiohttp.Response(self.writer, 200)

        resp.send_headers()
        if data:
            resp.write(data.encode())
        return resp

    def do_events(self, message, data):
        try:
            event = validate_parse_event(data.decode())
        except BadEvent as e:
            resp = aiohttp.Response(self.writer, 400)
            resp.send_headers()
            resp.write(str(e).encode())
            self.log.debug('Bad event: %s' % e)
            return resp

        resp = aiohttp.Response(self.writer, 200)
        resp.send_headers()

        self.log.info('Event: %s' % event)

        event_json = json.dumps(event).encode()
        for client in self.clients:
            client.send(event_json)

        return resp

    @asyncio.coroutine
    def handle_request(self, message, payload):

        peer, port = self.transport.get_extra_info('peername')
        self.log = logging.getLogger('[%s]' % peer)

        upgrade = 'websocket' in message.headers.get('UPGRADE', '').lower()

        if upgrade:
            status, headers, parser, writer, protocol = \
                aiohttp.websocket.do_handshake(message.method,
                                               message.headers,
                                               self.transport)
            resp = aiohttp.Response(self.writer, status,
                                    http_version=message.version)
            resp.add_headers(*headers)
            resp.send_headers()

            dataqueue = self.reader.set_parser(parser)
            self.clients.append(writer)

            self.log.debug('New websocket connection')

            while True:
                try:
                    msg = yield from dataqueue.read()
                except:
                    break

                if msg.tp == aiohttp.websocket.MSG_PING:
                    writer.pong()
                elif msg.tp == aiohttp.websocket.MSG_TEXT:
                    # Ignore
                    pass
                elif msg.tp == aiohttp.websocket.MSG_CLOSE:
                    break

            self.log.debug('Disconnected')
            self.clients.remove(writer)

        elif message.path.startswith('/static/'):
            resp = self.get_static(message)
            self.log.debug('GET %s: %s' % (message.path, resp.status))
            yield from resp.write_eof()
        elif message.path.startswith('/events'):
            data = yield from payload.read()
            resp = self.do_events(message, data)
            yield from resp.write_eof()
        else:
            resp = aiohttp.Response(self.writer, 400)
            resp.send_headers()
            yield from resp.write_eof()
            self.log.debug('Unknown request for %s' % message.path)
