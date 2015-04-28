from setuptools import setup

setup(name='wsevents',
      version='1.0',
      packages=['wsevents'],
      scripts=['event_service', 'event_handler'],
      install_requires=['asyncio', 'aiohttp', 'puredaemon', 'setproctitle',
                        'stevedore'],
  )
