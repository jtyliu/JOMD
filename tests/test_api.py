from sqlalchemy.util.langhelpers import NoneType
from utils.api import *
import asyncio
import json
import pytest
import datetime
# Shrug
# https://stackoverflow.com/questions/23033939/how-to-test-python-3-4-asyncio-code


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)

    return wrapper


class TestAPI:
    # Test the intended functionality of API.url_encode()
    def setup_class(self):
        self.api = API()

    def test_url_encode_str(self):
        params = {
            "aaa": "bbb",
            "bbb": "ccc",
            1: "ddd"
        }
        assert self.api.url_encode(params) == "?aaa=bbb&bbb=ccc&1=ddd"

    def test_url_encode_list(self):
        params = {
            'aaa': ["bbb", "ccc", "ddd"],
            "eee": [1, 2, 3],
            1: ["fff", 5, 7]
        }
        assert self.api.url_encode(params) == "?aaa=bbb&aaa=ccc&aaa=ddd&eee=1&eee=2&eee=3&1=fff&1=5&1=7"

    def test_url_encode_list_str(self):
        params = {
            "aaa": "bbb",
            "bbb": "ccc",
            1: ["eee", 123, "fff"]
        }
        assert self.api.url_encode(params) == "?aaa=bbb&bbb=ccc&1=eee&1=123&1=fff"

    def test_url_encode_escape_chr(self):
        params = {
            "user": "JoshuaL&page=1",
            "page": 1
        }
        assert self.api.url_encode(params) == "?user=JoshuaL%26page%3D1&page=1"

        params = {
            "user": "JoshuaL#",
            "page": 1
        }
        assert self.api.url_encode(params) == "?user=JoshuaL%23&page=1"

    def test_url_encode_none(self):
        params = {
            "user": "JoshuaL",
            "page": None
        }
        assert self.api.url_encode(params) == "?user=JoshuaL"

    @pytest.mark.asyncio
    async def test_parse_data(self):
        data = {"api_version": "v2", "method": "GET", "fetched": "ISO_DATE", "data": {"a": "aa", "b": "bb"}}
        obj = json.loads(json.dumps(data), object_hook=API.from_dict)
        await self.api.parse(obj, object)
        assert self.api.api_version == data["api_version"]
        assert self.api.method == data["method"]
        assert self.api.fetched == data["fetched"]

    @pytest.mark.asyncio
    async def test_parse_error(self):
        data = {
            "api_version": "v2",
            "method": "GET",
            "fetched": "ISO_DATE",
            "error": {"code": "404", "message": "User not found"},
        }
        obj = json.loads(json.dumps(data), object_hook=API.from_dict)
        with pytest.raises(ObjectNotFound):
            await self.api.parse(obj, object)

    def open_file(self, filename):
        with open('./tests/data/' + filename, 'r') as f:
            return f.read()

    def open_json(self, filename):
        return json.loads(self.open_file(filename), object_hook=API.from_dict)
    
    def test_from_dict(self):
        problem = self.open_json('problem.json')
        assert problem.code == 'helloworld'
        assert problem.name == 'Hello, World!'
        assert isinstance(problem.types, list)
        assert all(isinstance(problem_type, str) for problem_type in problem.types)
        assert problem.group == 'Uncategorized'
        assert problem.time_limit == 1.0
        assert problem.memory_limit == 65536
        assert isinstance(problem.language_resource_limits, list)
        assert problem.points == 1.0
        assert problem.partial is False
        assert problem.short_circuit is False
        assert isinstance(problem.languages, list)
        assert all(isinstance(language, str) for language in problem.languages)
        assert problem.is_organization_private is False
        assert isinstance(problem.organizations, list)
        assert problem.is_public is True

