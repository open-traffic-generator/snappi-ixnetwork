import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

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

    def test_parameterized_json_is_decoded(self):
        data = {"state": "SUCCESS"}
        self.session.request.return_value = self.response(
            200, data, "application/json; charset=utf-8"
        )
        self.assertEqual(self.api._request("GET", "/op"), data)

    def test_parameterized_binary_is_returned_as_bytes(self):
        data = b"capture-bytes"
        self.session.request.return_value = self.response(
            200, data, "application/octet-stream; example=value"
        )
        self.assertEqual(self.api._request("GET", "/files"), data)

    def test_media_type_case_and_whitespace_are_normalized(self):
        data = {"state": "ready"}
        self.session.request.return_value = self.response(
            200, data, " Application/JSON ; charset=utf-8"
        )
        self.assertEqual(self.api._request("GET", "/op"), data)

    def test_plain_json_is_preserved(self):
        data = {"state": "ready"}
        self.session.request.return_value = self.response(200, data)
        self.assertEqual(self.api._request("GET", "/op"), data)

    def test_plain_binary_is_preserved(self):
        data = b"capture-bytes"
        self.session.request.return_value = self.response(
            200, data, "application/octet-stream"
        )
        self.assertEqual(self.api._request("GET", "/files"), data)

    def test_unknown_media_type_keeps_response_object(self):
        response = self.response(200, b"text", "text/plain")
        self.session.request.return_value = response
        self.assertIs(self.api._request("GET", "/text"), response)

    def test_missing_media_type_keeps_response_object(self):
        response = self.response(200, b"text")
        response.headers = {}
        self.session.request.return_value = response
        self.assertIs(self.api._request("GET", "/text"), response)
