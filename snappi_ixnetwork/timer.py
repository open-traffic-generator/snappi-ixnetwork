import time
from collections import OrderedDict

timer_data = OrderedDict()


class Timer:
    def __init__(self, api, msg):
        self._api = api
        self._msg = msg

    def __enter__(self):
        """Start a new timer as a context manager"""
        self._start = time.time()
        return self

    def __exit__(self, *exc_info):
        """Stop the context manager timer"""
        time_lapse = time.time() - self._start
        self._api.info(self._msg + " %.3fs" % (time_lapse))
        timer_data[self._msg] = time_lapse
