import os
import pyinotify
import sys
import time

if __package__ == '':
    # load local package
    sys.path.insert(0, './')

from .config import config
from .engine import Engine


def build(t=0):
    print(f'Building site...')
    time.sleep(t)
    e = Engine(config.src,  config.out)
    e = None
    print(f'Done')

build()

if config.watch:
    # signal handling
    from signal import signal, SIGINT, SIGTERM
    run = True
    def stop():
        global run
        run = False
    signal(SIGINT, lambda a,b: stop())
    signal(SIGTERM, lambda a,b: stop())

    # create watcher
    watcher = pyinotify.WatchManager()
    notifier = pyinotify.ThreadedNotifier(watcher)
    base_dir = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
    events = pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_DELETE
    # watch
    watcher.add_watch(config.src, events, lambda event: build(0.5))
    # add watches for imported modules
    for module in sys.modules.values():
        # builtin modules don't have a __file__ attribute
        if hasattr(module, '__file__') and module.__file__ is not None:
            filename = os.path.abspath(module.__file__)
            # only watch file if it's in the same directory as the main script
            # + module src files
            if filename.startswith(base_dir)  or 'kishta' in module.__name__:
                watcher.add_watch(filename, events, lambda event: build(0.5))
    notifier.start()
    while run:
        time.sleep(0.1)
    notifier.stop()
