import time


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
        self._api.info(self._msg + " %.3fs" % (time.time() - self._start))
