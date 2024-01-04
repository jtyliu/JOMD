from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    TypeDecorator,
    Float,
    Boolean,
    DateTime,
    JSON,
    Table,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column
from utils.constants import DEBUG_DB
from typing import List
import datetime


__all__ = [
    'SubmissionCase',
    'Submission',
    'ParticipationSolution',
    'Participation',
    'ContestProblem',
    'ContestTag',
    'Contest',
    'ProblemType',
    'ProblemLanguageLimit',
    'Problem',
    'UserVolatility',
    'User',
    'Judge',
    'Language',
    'Organization',
    'Handle',
    'Gitgud',
    'CurrentGitgud',
    'session',
    'Base',
]

# Topologogical order
# Submission
# Participation
# Contest
# Problem
# Judge
# Language
# Organization

URI = "postgresql+psycopg2://postgres:postgres@db/postgres"

engine = create_engine(URI, echo=DEBUG)
class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, any]: JSON
    }

Session = sessionmaker(bind=engine, autoflush=False)
session = Session()

class AttrMixin:

    _cfg = cfg = dict()
    attr = ''

    def __init__(self, obj):
        self._cfg = obj.config
        self.cfg = obj.config

        def add_attr(attr, key):
            if attr == '':
                return key
            return attr + '__' + key

        def init(obj, cfg, attr):
            for key in cfg:
                if type(cfg[key]) is dict and hasattr(obj, key):
                    init(getattr(obj, key), cfg[key], add_attr(attr, key))
                else:
                    if hasattr(obj, key):
                        # TODO: Logging
                        # print(add_attr(attr, key), getattr(obj, key))
                        setattr(self, add_attr(attr, key), getattr(obj, key))
        init(obj, self.cfg, '')

    # Note this little hack of __getattr__ is only meant for building the data retrieved from API into a proper format which can be stored into the db
    # This is not intended for use outside of that scope
    def __getattr__(self, key):
        if not hasattr(self, 'cfg') or key not in self.cfg:
            raise Exception("Key not found in config!")
        if self.attr != '':
            self.attr += '__'
        self.attr += key
        if type(self.cfg[key]) is dict:
            self.cfg = self.cfg[key]
            return self
        else:
            ret = getattr(self, self.attr)
            self.attr = ''
            self.cfg = self._cfg
            return ret


contest_problem = Table(
    "contest_problem",
    Base.metadata,
    Column("contest_id", ForeignKey("contest.key")),
    Column("problem_id", ForeignKey("problem.code")),
)

contest_user = Table(
    "contest_user",
    Base.metadata,
    Column("contest_id", ForeignKey("contest.key")),
    Column("user_id", ForeignKey("user.id")),
)

problem_user = Table(
    "problem_user",
    Base.metadata,
    Column("problem_id", ForeignKey("problem.code")),
    Column("user_id", ForeignKey("user.id")),
)

language_problem = Table(
    "language_problem",
    Base.metadata,
    Column("problem_id", ForeignKey("problem.code")),
    Column("language_id", ForeignKey("language.id")),
)

organization_problem = Table(
    "organization_problem",
    Base.metadata,
    Column("problem_id", ForeignKey("problem.code")),
    Column("organization_id", ForeignKey("organization.id")),
)

contest_organization = Table(
    "contest_organization",
    Base.metadata,
    Column("contest_id", ForeignKey("contest.key")),
    Column("organization_id", ForeignKey("organization.id")),
)

organization_user = Table(
    "organization_user",
    Base.metadata,
    Column("organization_id", ForeignKey("organization.id")),
    Column("user_id", ForeignKey("user.id")),
)

judge_language = Table(
    "judge_language",
    Base.metadata,
    Column("judge_id", ForeignKey("judge.name")),
    Column("language_id", ForeignKey("language.id")),
)


class Problem(Base):
    __tablename__ = "problem"

    code: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    # authors = relationship('User', secondary=problem_author_user,
    #                        back_populates='authored')
    authors: Mapped[dict[str, any]]
    types: Mapped[dict[str, any]]
    group: Mapped[str]
    time_limit: Mapped[float]
    memory_limit: Mapped[int]
    language_resource_limits: Mapped[dict[str, any]]
    points: Mapped[int]
    partial: Mapped[bool]
    short_circuit: Mapped[bool]
    languages = relationship("Language", secondary=language_problem, back_populates="problems")
    is_organization_private: Mapped[bool]
    organizations = relationship("Organization", secondary=organization_problem, back_populates="problems")
    is_public: Mapped[bool]

    contests = relationship("Contest", secondary=contest_problem, back_populates="problems")
    solved_users = relationship("User", secondary=problem_user, back_populates="solved_problems")
    submissions: Mapped[List["Submission"]] = relationship(back_populates="problem")

    def __init__(self, problem):
        self.code = problem.code
        self.name = problem.name
        # Authors is stored as array on usernames
        # Perhaps I can figure out a way to store an array of user objects
        # without creating a reference cycle
        # for username in problem.authors:
        #     user = session.query(User).\
        #         filter(User.username == username)
        #     self.authors.append(user)
        self.authors = problem.authors
        self.types = problem.types
        self.group = problem.group
        self.time_limit = problem.time_limit
        self.memory_limit = problem.memory_limit
        self.language_resource_limits = problem.language_resource_limits
        self.points = problem.points
        self.partial = problem.partial
        self.short_circuit = problem.short_circuit
        self.languages += problem.languages
        self.is_organization_private = problem.is_organization_private
        self.organizations += problem.organizations
        self.is_public = problem.is_public


class Contest(Base):
    __tablename__ = "contest"

    key: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    start_time: Mapped[datetime.datetime]
    end_time: Mapped[datetime.datetime]
    time_limit: Mapped[int]
    is_rated: Mapped[bool]
    rate_all: Mapped[bool]
    has_rating: Mapped[bool]
    rating_floor: Mapped[int]
    rating_ceiling: Mapped[int]
    hidden_scoreboard: Mapped[bool]
    is_organization_private: Mapped[bool]
    organizations = relationship("Organization", secondary=contest_organization, back_populates="contest")
    is_private: Mapped[bool]
    tags: Mapped[dict[str, any]]
    _format: Mapped[dict[str, any]] = mapped_column("format")
    rankings: Mapped[dict[str, any]]
    problems = relationship("Problem", secondary=contest_problem, back_populates="contests")

    participations: Mapped[List["Participation"]] = relationship(back_populates="contest")
    users = relationship("User", secondary=contest_user, back_populates="contests")

    def __init__(self, contest):
        self.key = contest.key
        self.name = contest.name
        self.start_time = contest.start_time
        self.end_time = contest.end_time
        self.time_limit = contest.time_limit
        self.is_rated = contest.is_rated
        self.rate_all = contest.rate_all
        self.has_rating = contest.has_rating
        self.rating_floor = contest.rating_floor
        self.rating_ceiling = contest.rating_ceiling
        self.hidden_scoreboard = contest.hidden_scoreboard
        self.is_organization_private = contest.is_organization_private
        self.organizations += contest.organizations
        self.is_private = contest.is_private
        self.tags = contest.tags
        self._format = contest.format
        self.rankings = contest.rankings
        self.problems += contest.problems


class Participation(Base):
    __tablename__ = "participation"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="participation")
    contest_id: Mapped[str] = mapped_column(ForeignKey("contest.key"))
    contest: Mapped["Contest"] = relationship(back_populates="participations")
    score: Mapped[float]
    cumulative_time: Mapped[int]
    tiebreaker: Mapped[float]
    is_disqualified: Mapped[bool]
    virtual_participation_number: Mapped[int]

    def __init__(self, part):
        self.id = part.id
        self.user.append(part.user)
        self._contest = part.contest
        self.contest.append(part.contest)
        self.score = part.score
        self.cumulative_time = part.cumulative_time
        self.tiebreaker = part.tiebreaker
        self.is_disqualified = part.is_disqualified
        self.virtual_participation_number = part.virtual_participation_number


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    points: Mapped[float]
    performance_points: Mapped[float]
    problem_count: Mapped[int]
    rank: Mapped[str]
    rating: Mapped[int]
    max_rating: Mapped[int]
    solved_problems = relationship("Problem", secondary=problem_user, back_populates="solved_users")
    organizations = relationship("Organization", secondary=organization_user, back_populates="users")
    contests = relationship("Contest", secondary=contest_user, back_populates="users")

    # authored = relationship('Problem', secondary=problem_author_user,
    #                         back_populates='authors')
    participation: Mapped[List["Participation"]] = relationship(back_populates="user")
    submissions: Mapped[List["Submission"]] = relationship(back_populates="user")

    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.points = user.points
        self.performance_points = user.performance_points
        self.problem_count = user.problem_count
        self.rank = user.rank
        self.rating = user.rating
        self.solved_problems += user.solved_problems
        self.organizations += user.organizations
        self.contests += user.contests
        self.max_rating = user.max_rating


class Submission(Base):
    __tablename__ = "submission"

    id: Mapped[int] = mapped_column(primary_key=True)
    # TODO: Should only be a single foreign key
    problem_id: Mapped[str] = mapped_column(ForeignKey("problem.code"))
    problem: Mapped["Problem"] = relationship(back_populates="submissions")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="submissions")
    date: Mapped[datetime.datetime]
    language_id: Mapped[int] = mapped_column(ForeignKey("language.id"))
    language: Mapped["Language"] = relationship(back_populates="submissions")
    time: Mapped[float]
    memory: Mapped[float]
    points: Mapped[float]
    result: Mapped[str]
    status: Mapped[str]
    case_points: Mapped[float]
    case_total: Mapped[float]
    cases: Mapped[dict[str, any]]
    # This is for +gimme to retrieve unsolved problems
    _code: Mapped[str]
    _user: Mapped[str]

    def __init__(self, submission):
        self.id = submission.id
        self.problem += submission.problem
        self._code = submission._problem
        self._user = submission._user
        self.user += submission.user
        self.date = submission.date
        self.language += submission.language
        self.time = submission.time
        self.memory = submission.memory
        self.points = submission.points
        self.result = submission.result
        self.status = submission.status
        self.case_points = submission.case_points
        self.case_total = submission.case_total
        self.cases = submission.cases


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str]
    short_name: Mapped[str]
    is_open: Mapped[bool]
    member_count: Mapped[int]

    problems = relationship("Problem", secondary=organization_problem, back_populates="organizations")
    contest = relationship("Contest", secondary=contest_organization, back_populates="organizations")
    users = relationship("User", secondary=organization_user, back_populates="organizations")

    def __init__(self, organization):
        self.id = organization.id
        self.slug = organization.slug
        self.short_name = organization.short_name
        self.is_open = organization.is_open
        self.member_count = organization.member_count


class Language(Base):
    __tablename__ = "language"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str]
    short_name: Mapped[str]
    common_name: Mapped[str]
    ace_mode_name: Mapped[str]
    pygments_name: Mapped[str]
    code_template: Mapped[str]

    problems = relationship("Problem", secondary=language_problem, back_populates="languages")
    submissions: Mapped[List["Submission"]] = relationship(back_populates="language")
    judges = relationship("Judge", secondary=judge_language, back_populates="languages")

    def __init__(self, language):
        self.id = language.id
        self.key = language.key
        self.short_name = language.short_name
        self.common_name = language.common_name
        self.ace_mode_name = language.ace_mode_name
        self.pygments_name = language.pygments_name
        self.code_template = language.code_template


# I don't think I'll ever use this
class Judge(Base):
    __tablename__ = "judge"

    name: Mapped[str] = mapped_column(primary_key=True)
    start_time: Mapped[datetime.datetime]
    ping: Mapped[float]
    load: Mapped[float]
    languages = relationship("Language", secondary=judge_language, back_populates="judges")

    def __init__(self, judge):
        self.name = judge.name
        self.start_time = judge.start_time
        self.ping = judge.ping
        self.load = judge.load
        for language_key in judge.languages:
            language = session.query(Language).filter(Language.key == language_key).first()
            self.languages.append(language)


class Handle(Base):
    __tablename__ = "handle"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(index=True)
    handle: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int]
    guild_id: Mapped[int] = mapped_column(index=True)


class Gitgud(Base):
    __tablename__ = "gitgud"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    handle: Mapped[str]
    guild_id: Mapped[int]
    point: Mapped[int]
    # TODO: make it a foreign key problem table
    problem_id: Mapped[str]
    time: Mapped[datetime.datetime]


class CurrentGitgud(Base):
    __tablename__ = "current_gitgud"
    _id: Mapped[int] = mapped_column(primary_key=True)
    handle: Mapped[str]
    guild_id: Mapped[int]
    # TODO: make it a foreign key problem table
    problem_id: Mapped[str]
    point: Mapped[int]
    time: Mapped[datetime.datetime]


Base.metadata.create_all(engine)
