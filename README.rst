========================================
wsevents - A websocket event message bus
========================================

Components::
- event_service: The websocket event bus
- event_handler: A service that listens on the bus and dispatches actions

Usage:
------

Just run event_service (probably with --daemon). You can send in events by doing things like:

 curl http://foo/events -d '{"event": {"sender": "foo", "action": "test"}}'

In order to listen to events, you need to connect to the websocket
service. See wsevents/event_handler.py for an aiohttp example of
consuming them from python. Or, use a browser and start a websocket
on /events to start getting them.

The event handler is a thing that runs each event through a
wsevents.Event object. If the precondition, event_NN, and
postcondition match, then it calls the action method to do a
thing. Events are discovered using stevedore in the events.events
namespace.
