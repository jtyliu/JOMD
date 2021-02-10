import unittest
from utils.api import API, ObjectNotFound
import asyncio
# Shrug
# https://stackoverflow.com/questions/23033939/how-to-test-python-3-4-asyncio-code


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class APITest(unittest.TestCase):
    # Test the intended functionality of API.url_encode()
    def setUp(self):
        self.api = API()

    def test_url_encode_str(self):
        params = {
            "aaa": "bbb",
            "bbb": "ccc",
            1: "ddd"
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?aaa=bbb&bbb=ccc&1=ddd"
        )

    def test_url_encode_list(self):
        params = {
            'aaa': ["bbb", "ccc", "ddd"],
            "eee": [1, 2, 3],
            1: ["fff", 5, 7]
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?aaa=bbb&aaa=ccc&aaa=ddd&eee=1&eee=2&eee=3&1=fff&1=5&1=7"
        )

    def test_url_encode_list_str(self):
        params = {
            "aaa": "bbb",
            "bbb": "ccc",
            1: ["eee", 123, "fff"]
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?aaa=bbb&bbb=ccc&1=eee&1=123&1=fff"
        )

    def test_url_encode_escape_chr(self):
        params = {
            "user": "JoshuaL&page=1",
            "page": 1
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?user=JoshuaL%26page%3D1&page=1"
        )
        params = {
            "user": "JoshuaL#",
            "page": 1
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?user=JoshuaL%23&page=1"
        )

    def test_url_encode_none(self):
        params = {
            "user": "JoshuaL",
            "page": None
        }
        self.assertEqual(
            self.api.url_encode(params),
            "?user=JoshuaL"
        )

    class DataMock:
        async def parse(self, data, _type):
            return data

    @async_test
    async def test_parse_data(self):
        api_data = self.api.Data
        self.api.Data = self.DataMock
        data = {
            "api_version": "v2",
            "method": "GET",
            "fetched": "ISO_DATE",
            "data": {
                "a": "aa",
                "b": "bb"
            }
        }
        await self.api.parse(data, object)
        self.assertEqual(self.api.api_version, data["api_version"])
        self.assertEqual(self.api.method, data["method"])
        self.assertEqual(self.api.fetched, data["fetched"])
        self.assertEqual(self.api.data, data["data"])
        self.api.Data = api_data

    @async_test
    async def test_parse_error(self):
        api_data = self.api.Data
        self.api.Data = self.DataMock
        data = {
            "api_version": "v2",
            "method": "GET",
            "fetched": "ISO_DATE",
            "error": {
                "code": "404",
                "message": "User not found"
            }
        }
        with self.assertRaises(ObjectNotFound):
            await self.api.parse(data, object)



if __name__ == '__main__':
    unittest.main()