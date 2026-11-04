import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.snappi_api import Api


class TestHttpRequests(unittest.TestCase):
    def setUp(self):
        self.session = SimpleNamespace(request=Mock())
        connection = SimpleNamespace(
            _normalize_url=lambda url: ("http://controller.example.test", url),
            x_api_key="example",
            _session=self.session,
        )
        self.api = SimpleNamespace(
            debug=Mock(),
            _assistant=SimpleNamespace(
                Session=SimpleNamespace(_connection=connection)
            ),
        )
        self.api._request = MethodType(Api._request, self.api)
        sleep = patch("snappi_ixnetwork.snappi_api.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    @staticmethod
    def response(status, body, content_type="application/json"):
        return SimpleNamespace(
            status_code=status,
            json=lambda: body,
            content=body,
            headers={"Content-Type": content_type},
            raise_for_status=Mock(),
        )

    def test_completion_stops_polling(self):
        done = {"state": "SUCCESS", "result": "kVoid"}
        self.session.request.side_effect = [
            self.response(202, {"state": "IN_PROGRESS", "url": "/op/1"}),
            self.response(200, done),
            AssertionError("polled after SUCCESS"),
        ]
        self.assertEqual(self.api._request("POST", "/op"), done)
        self.assertEqual(self.session.request.call_count, 2)

    def test_each_poll_consumes_the_latest_state(self):
        done = {"state": "SUCCESS", "result": "kVoid"}
        progress = {"state": "IN_PROGRESS", "url": "/op/1"}
        self.session.request.side_effect = [
            self.response(202, progress),
            self.response(200, {"state": "IN_PROGRESS", "url": "/op/2"}),
            self.response(200, done),
            AssertionError("polled after SUCCESS"),
        ]
        self.assertEqual(self.api._request("POST", "/op"), done)
        self.assertEqual(self.session.request.call_count, 3)
        self.assertEqual(
            [call.args[:2] for call in self.session.request.call_args_list],
            [("POST", "/op"), ("GET", "/op/1"), ("GET", "/op/2")],
        )

    def test_terminal_error_raises(self):
        self.session.request.side_effect = [
            self.response(202, {"state": "IN_PROGRESS", "url": "/op/1"}),
            self.response(200, {"state": "ERROR", "message": "rejected"}),
            AssertionError("polled after ERROR"),
        ]
        with self.assertRaisesRegex(SnappiIxnException, "rejected"):
            self.api._request("POST", "/op")

    def test_immediate_error_raises(self):
        self.session.request.return_value = self.response(
            202, {"state": "ERROR", "message": "rejected"}
        )
        with self.assertRaisesRegex(SnappiIxnException, "rejected"):
            self.api._request("POST", "/op")

    def test_already_successful_operation_is_not_polled(self):
        done = {"state": "SUCCESS", "result": "kVoid"}
        self.session.request.return_value = self.response(202, done)
        self.assertEqual(self.api._request("POST", "/op"), done)
        self.assertEqual(self.session.request.call_count, 1)

    def test_synchronous_json_is_preserved(self):
        data = {"state": "ready"}
        self.session.request.return_value = self.response(200, data)
        self.assertEqual(self.api._request("GET", "/capture"), data)
