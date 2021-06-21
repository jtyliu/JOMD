from sqlalchemy.util.langhelpers import NoneType
from utils.api import *
import asyncio
import json
import pytest
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

    class DataMock:
        async def parse(self, data, _type):
            return data

    @pytest.mark.asyncio
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
        assert self.api.api_version == data["api_version"]
        assert self.api.method == data["method"]
        assert self.api.fetched == data["fetched"]
        assert self.api.data == data["data"]

    @pytest.mark.asyncio
    async def test_parse_error(self):
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
        with pytest.raises(ObjectNotFound):
            await self.api.parse(data, object)


class TestAPIModels:

    def open_file(self, filename):
        with open('./data/' + filename, 'r') as f:
            return f.read()

    def open_json(self, filename):
        return json.loads(self.open_file(filename))

    class Jsonn:
        @classmethod
        def from_dict(self, j):
            obj = self()
            obj.__dict__.update(j)
            return obj

    def test_user_model(self):
        # user = json.loads(self.open_file('user.json'), object_hook=self.Jsonn.from_dict)
        user = User(self.open_json('user.json'))
        assert user.id == 27823
        assert user.username == 'JoshuaL'
        assert type(user.points) is float
        assert type(user.performance_points) is float
        assert type(user.problem_count) is int
        assert all(type(code) is str for code in user.solved_problems)
        assert user.rank == 'user'
        assert type(user.rating) is int
        assert type(user.volatility) is int
        assert all(type(org) is int for org in user.organizations)

        for contest in user.contests:
            assert type(contest.key) is str
            assert type(contest.score) is float
            assert type(contest.cumulative_time) is int
            assert isinstance(contest.rating, (int, NoneType))
            assert isinstance(contest.volatility, (int, NoneType))

        if hasattr(user, '_contests'):
            for contest in user._contests:
                assert type(contest['key']) is str
                assert type(contest['score']) is float
                assert type(contest['cumulative_time']) is int
                assert isinstance(contest['rating'], (int, NoneType))
                assert isinstance(contest['volatility'], (int, NoneType))

        if hasattr(user, '_solved_problems'):
            assert all(type(code) is str for code in user._solved_problems)

        if hasattr(user, '_organizations'):
            assert all(type(org) is int for org in user._organizations)
