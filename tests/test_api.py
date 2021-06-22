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
        with open('./tests/data/' + filename, 'r') as f:
            return f.read()

    def open_json(self, filename):
        return json.loads(self.open_file(filename))

    class Jsonn:
        @classmethod
        def from_dict(cls, j):
            obj = cls()
            obj.__dict__.update(j)
            return obj

    def test_problem_model(self):
        problem = Problem(self.open_json('problem.json'))
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

    def test_contest_model(self):
        contest = Contest(self.open_json('contest.json'))
        assert contest.key == 'dmopc20c7'
        assert contest.name == 'DMOPC \'20 June Contest'
        assert contest.start_time == datetime.datetime(2021, 6, 19, 4, tzinfo=datetime.timezone.utc)
        assert contest.end_time == datetime.datetime(2021, 6, 21, 4, tzinfo=datetime.timezone.utc)
        assert contest.time_limit == 10800.0
        assert contest.is_rated is True
        assert contest.rate_all is True
        assert contest.has_rating is True
        assert contest.rating_floor is None
        assert contest.rating_ceiling is None
        assert contest.hidden_scoreboard is True
        assert contest.scoreboard_visibility == "P"
        assert contest.is_organization_private is False
        assert isinstance(contest.organizations, list)
        assert contest.is_private is False
        assert isinstance(contest.tags, list)
        assert all(isinstance(tag, str) for tag in contest.tags)
        if isinstance(contest.format, dict):
            format = contest.format
            assert format['name'] == 'atcoder'
            config = format['config']
            assert config['penalty'] == 5
            # Config can contain cumtime: bool, first_ac_bonus: int, time_bonus: int,
        else:
            format = contest.format
            assert format.name == 'atcoder'
            config = format.config
            assert config.penalty == 5

        for problem in contest.problems:
            if isinstance(problem, dict):
                assert isinstance(problem['points'], int)
                assert isinstance(problem['partial'], bool)
                assert isinstance(problem['is_pretested'], bool)
                assert isinstance(problem['max_submissions'], NoneType)
                assert isinstance(problem['label'], str)
                assert isinstance(problem['name'], str)
                assert isinstance(problem['code'], str)
            else:
                assert isinstance(problem.points, int)
                assert isinstance(problem.partial, bool)
                assert isinstance(problem.is_pretested, bool)
                assert isinstance(problem.max_submissions, NoneType)
                assert isinstance(problem.label, str)
                assert isinstance(problem.name, str)
                assert isinstance(problem.code, str)

        for ranking in contest.rankings:
            if isinstance(ranking, dict):
                assert isinstance(ranking['user'], str)
                assert isinstance(ranking['start_time'], (datetime.datetime, str))
                assert isinstance(ranking['end_time'], (datetime.datetime, str))
                assert isinstance(ranking['score'], float)
                assert isinstance(ranking['cumulative_time'], int)
                assert isinstance(ranking['tiebreaker'], float)
                assert isinstance(ranking['old_rating'], (int, NoneType))
                assert isinstance(ranking['new_rating'], (int, NoneType))
                assert isinstance(ranking['is_disqualified'], bool)
                for solution in ranking['solutions']:
                    if solution:
                        assert isinstance(solution['time'], float)
                        assert isinstance(solution['points'], float)
                        assert isinstance(solution['penalty'], int)
                    # If the user doesn't solve any problems it's None
            else:
                assert isinstance(ranking.user, str)
                assert isinstance(ranking.start_time, datetime.datetime)
                assert isinstance(ranking.end_time, datetime.datetime)
                assert isinstance(ranking.score, float)
                assert isinstance(ranking.cumulative_time, int)
                assert isinstance(ranking.tiebreaker, float)
                assert isinstance(ranking.old_rating, int)
                assert isinstance(ranking.new_rating, int)
                assert isinstance(ranking.is_disqualified, bool)
                for solution in ranking.solutions:
                    if solution:
                        assert isinstance(solution.time, float)
                        assert isinstance(solution.points, float)
                        assert isinstance(solution.penalty, int)

    def test_participation_model(self):
        particip = Participation(self.open_json('participation.json'))
        if hasattr(particip, '_user'):
            assert particip._user == "JoshuaL"
        else:
            assert particip.user == "JoshuaL"
        if hasattr(particip, '_contest'):
            assert particip._contest == "dmopc20c7"
        else:
            assert particip.contest == "dmopc20c7"
        assert particip.start_time == datetime.datetime(2021, 6, 20, 18, 57, 49, tzinfo=datetime.timezone.utc)
        assert particip.end_time == datetime.datetime(2021, 6, 20, 21, 57, 49, tzinfo=datetime.timezone.utc)
        assert particip.score == 40.0
        assert particip.cumulative_time == 4084
        assert particip.tiebreaker == 0.0
        assert particip.is_disqualified is False
        assert particip.virtual_participation_number == 0

    def test_user_model(self):
        # user = json.loads(self.open_file('user.json'), object_hook=self.Jsonn.from_dict)
        user = User(self.open_json('user.json'))
        assert user.id == 27823
        assert user.username == 'JoshuaL'
        assert user.points == 4420.798
        assert user.performance_points == 548.8746603923722
        assert user.problem_count == 599
        assert all(isinstance(code, str) for code in user.solved_problems)
        assert user.rank == 'user'
        assert user.rating == 1948
        assert user.volatility == 185
        assert all(isinstance(org, int) for org in user.organizations)

        for contest in user.contests:
            assert isinstance(contest.key, str)
            assert isinstance(contest.score, float)
            assert isinstance(contest.cumulative_time, int)
            assert isinstance(contest.rating, (int, NoneType))
            assert isinstance(contest.volatility, (int, NoneType))

        if hasattr(user, '_contests'):
            for contest in user._contests:
                assert isinstance(contest['key'], str)
                assert isinstance(contest['score'], float)
                assert isinstance(contest['cumulative_time'], int)
                assert isinstance(contest['rating'], (int, NoneType))
                assert isinstance(contest['volatility'], (int, NoneType))

        if hasattr(user, '_solved_problems'):
            assert all(isinstance(code, str) for code in user._solved_problems)

        if hasattr(user, '_organizations'):
            assert all(isinstance(org, int) for org in user._organizations)

    def test_submission_model(self):
        submission = Submission(self.open_json('submission.json'))
        assert submission.id == 2023196
        if hasattr(submission, '_problem'):
            assert submission._problem == 'boolean'
        else:
            assert submission.problem == 'boolean'
        if hasattr(submission, '_user'):
            assert submission._user == 'JoshuaL'
        else:
            assert submission.user == 'JoshuaL'
        assert submission.date == datetime.datetime(2020, 4, 9, 22, 33, 25, tzinfo=datetime.timezone.utc)
        if hasattr(submission, '_language'):
            assert submission._language == 'C'
        else:
            assert submission.language == 'C'
        assert submission.time == 1.605702267
        assert submission.memory == 776.0
        assert submission.points == 3.0
        assert submission.status == 'D'
        assert submission.result == 'AC'
        assert submission.case_points == 100.0
        assert submission.case_total == 100.0
        print(type(submission.cases))

        for cases in submission.cases:
            if isinstance(cases, dict):
                assert cases['type'] == 'batch'
                assert cases['batch_id'] == 1
                assert cases['points'] == 100.0
                assert cases['total'] == 100.0
                for case in cases['cases']:
                    assert isinstance(case['type'], str)
                    assert isinstance(case['case_id'], int)
                    assert isinstance(case['time'], float)
                    assert isinstance(case['memory'], float)
                    assert isinstance(case['points'], float)
                    assert isinstance(case['total'], float)
            else:
                assert cases.type == 'batch'
                assert cases.batch_id == 1
                assert cases.points == 100.0
                assert cases.total == 100.0
                for case in cases.cases:
                    assert isinstance(case.type, str)
                    assert isinstance(case.case_id, int)
                    assert isinstance(case.time, float)
                    assert isinstance(case.memory, float)
                    assert isinstance(case.points, float)
                    assert isinstance(case.total, float)
