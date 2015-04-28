import asyncio
import datetime
import json
import logging
import time

import aiohttp
from stevedore import extension


@asyncio.coroutine
def client_loop(url):
    ws = yield from aiohttp.ws_connect(url, autoclose=False, autoping=False)

    log = logging.getLogger('wsclient')
    log.info('Connected')

    dispatcher = EventHandler()

    while True:
        msg = yield from ws.receive()
        if msg is None or msg.data is None:
            return
        try:
            event = json.loads(msg.data)
        except:
            log.exception('Failed to de-JSON event')
            continue

        log.debug('Event: %s' % event)
        if 'sender' not in event:
            log.warning('Unable to dispatch even with no sender')
            continue
        yield from dispatcher.handle_event(event)


class Event(object):
    def __init__(self, timeout=120):
        self._timeout = timeout
        self._log = logging.getLogger(__name__)

        self._max = 0
        for i in range(1, 100):
            if hasattr(self, self._seq_name(i)):
                self._max = i

        self.reset()

    def reset(self):
        self._start = 0
        self._index = 0

    def expired(self):
        return self._max > 0 and (time.time() - self._start) > self._timeout

    def satisfied(self):
        if self.expired():
            self.reset()
            return False
        if self._index == self._max:
            pc = self.postcondition()
            if not pc:
                self.reset()
            return pc
        else:
            return False

    @staticmethod
    def _seq_name(i):
        return 'event_%02i' % i

    def precondition(self):
        return True

    def postcondition(self):
        return True

    def action(self):
        self.reset()

    def process_event(self, event):
        if not self.precondition():
            self.reset()
            return False

        if self.expired():
            self.reset()

        fn = getattr(self, self._seq_name(self._index + 1))
        result = fn(event)
        if result:
            if self._index == 0:
                self._start = time.time()
            self._index += 1
        return result


class EventHandler(object):
    def __init__(self, namespace='events.events'):
        self._namespace = namespace
        self._log = logging.getLogger('EventHandler')
        self.reload_events()

    def reload_events(self):
        self.events = {}
        mgr = extension.ExtensionManager(self._namespace,
                                         invoke_on_load=True)
        for name in mgr.names():
            self.events[name] = mgr[name].obj

    def _handle_one_event(self, event, event_name, handler):
        if handler.process_event(event):
            self._log.debug('Event %s matched' % event_name)
        if handler.satisfied():
            self._log.debug('Triggering event %s' % event_name)
            handler.action()
            handler.reset()

    @asyncio.coroutine
    def handle_event(self, event):
        for event_name, handler in self.events.items():
            try:
                self._handle_one_event(event, event_name, handler)
            except Exception:
                self._log.exception(
                    'Error dispatching event for %s' % event_name)
