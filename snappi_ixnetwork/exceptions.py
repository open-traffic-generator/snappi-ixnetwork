from ixnetwork_restpy import errors as err
import sys
import traceback


class SnappiIxnException(Exception):
    def __init__(self, *args):
        super(SnappiIxnException, self).__init__(*args)
        self._args = args
        self._message = None
        self._status_code = None
        self.process_exception()
        self._add_traceback()

    @property
    def args(self):
        return (
            self._status_code,
            (
                [self._message]
                if not isinstance(self._message, list)
                else self._message
            ),
        )

    @property
    def message(self):
        return (
            [self._message]
            if not isinstance(self._message, list)
            else self._message
        )

    @property
    def status_code(self):
        return self._status_code

    def process_exception(self):
        if isinstance(self._args, tuple) and len(self._args) == 1:
            if isinstance(self._args[0], (str, list)):
                self._status_code = (
                    500 if self._status_code is None else self._status_code
                )
                self._message = self._args[0]
                return
            if isinstance(self._args[0], err.IxNetworkError):
                self._status_code = self._args[0].status_code
                self._status_code = (
                    500 if self._status_code is None else self._status_code
                )
                self._message = self._args[0].message
                return
            if isinstance(self._args[0], (NameError, TypeError, ValueError)):
                self._status_code = 400
                self._args = self._args[0].args
                return self.process_exception()
            if isinstance(
                self._args[0], (ImportError, Exception, RuntimeError)
            ):
                self._args = self._args[0].args
                return self.process_exception()
        elif isinstance(self._args, tuple) and len(self._args) > 1:
            self._status_code = self._args[0]
            self._message = self._args[1]
            return
        else:
            self._message = self._args
        return

    def _add_traceback(self):
        tb = sys.exc_info()
        if len(tb) >= 2:
            tb = traceback.format_tb(tb[2])
            if isinstance(tb, str):
                tb = [tb]
            if isinstance(self._message, list):
                tb.extend(self._message)
                self._message = tb
            if isinstance(self._message, str):
                self._message = "{} {}".format("".join(tb), self._message)

    def __str__(self):
        if isinstance(self._message, list):
            return "".join(self._message)
        return self._message

    def __repr__(self):
        if isinstance(self._message, list):
            return "".join(self._message)
        return self._message
