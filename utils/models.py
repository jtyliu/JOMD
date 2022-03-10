from datetime import datetime
from operator import add
from typing import List, Optional
from sqlalchemy.orm import relation, sessionmaker, relationship
from sqlalchemy import create_engine, select, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, String, Integer, DateTime, Float, Boolean, Table, ForeignKey, Text)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from utils.constants import DEBUG
import time
import logging

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

URI = 'sqlite:///utils/db/JOMD1.db'

engine = create_engine(URI, echo=DEBUG)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine, autoflush=False)
session = Session()
logger = logging.getLogger(__name__)


total_time = 0
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    global total_time
    total = time.time() - conn.info['query_start_time'].pop(-1)
    logger.info("Start Query: %s", statement)
    logger.info("Query params: %s", parameters)
    logger.info("Total Time: %f", total)
    total_time += total

# import atexit

# def exit_handler():
#     global total_time
#     print("Total time communicating with db", total_time)

# atexit.register(exit_handler)


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


class SubmissionCase(Base):
    __tablename__ = 'submission_case'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    type: Optional[str] = Column(String)
    case_id: Optional[int] = Column(Integer)
    status: Optional[str] = Column(String)
    time: Optional[float] = Column(Float)
    memory: Optional[float] = Column(Float)
    points: Optional[float] = Column(Float, index=True)
    total: Optional[float] = Column(Float, index=True)

    submission_id: Optional[int] = Column(Integer, ForeignKey('submission.id'))
    submission: Optional['Submission'] = relationship('Submission', back_populates='cases')


class Submission(Base):
    __tablename__ = 'submission'

    id: int = Column(Integer, primary_key=True)
    date: Optional[datetime] = Column(DateTime, index=True)
    time: Optional[float] = Column(Float)
    memory: Optional[float] = Column(Float)
    points: Optional[float] = Column(Float)
    status: Optional[str] = Column(String)
    result: Optional[str] = Column(String)
    case_points: Optional[float] = Column(Float)
    case_total: Optional[float] = Column(Float)

    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: Optional['Problem'] = relationship('Problem', back_populates='submissions')
    user_id: Optional[int] = Column(Integer, ForeignKey('user.id'))
    user: Optional['User'] = relationship('User', back_populates='submissions')
    language_id: Optional[int] = Column(Integer, ForeignKey('language.id'))
    language: Optional['Language'] = relationship('Language', back_populates='submissions')
    cases: Optional[List[SubmissionCase]] = relationship('SubmissionCase', back_populates='submission')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ParticipationSolution(Base):
    __tablename__ = 'participation_solution'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    points: Optional[float] = Column(Float, index=True)
    time: Optional[float] = Column(Float)

    participation_id: Optional[int] = Column(Integer, ForeignKey('participation.id'))
    participation: Optional['Participation'] = relationship('Participation', back_populates='solutions')
    contest_id: Optional[int] = Column(String, ForeignKey('contest.key'))
    contest = relationship('Contest', back_populates='solutions')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Participation(Base):
    __tablename__ = 'participation'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    start_time: Optional[datetime] = Column(DateTime)
    end_time: Optional[datetime] = Column(DateTime)
    score: Optional[float] = Column(Float)
    cumulative_time: Optional[int] = Column(Integer)
    tiebreaker: Optional[float] = Column(Float)
    old_rating: Optional[int] = Column(Integer)
    new_rating: Optional[int] = Column(Integer)
    is_disqualified: Optional[bool] = Column(Boolean)
    virtual_participation_number: Optional[int] = Column(Integer)

    user_id: Optional[int] = Column(Integer, ForeignKey('user.id'))
    user: Optional['User'] = relationship('User', back_populates='contests')
    contest_id: Optional[str] = Column(String, ForeignKey('contest.key'))
    contest: Optional['Contest'] = relationship('Contest', back_populates='rankings')
    solutions: Optional[List[ParticipationSolution]] = \
        relationship('ParticipationSolution', back_populates='participation',
                     cascade='all, delete', passive_deletes=True)

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ContestProblem(Base):
    __tablename__ = 'contest_problem'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    is_pretested: Optional[bool] = Column(Boolean, index=True)
    max_submissions: Optional[int] = Column(Integer, index=True)
    label: Optional[str] = Column(String, index=True)

    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: Optional['Problem'] = relationship('Problem')
    contest_id: Optional[str] = Column(String, ForeignKey('contest.key'))
    contest: Optional['Contest'] = relationship('Contest', back_populates='problems')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ContestTag(Base):
    __tablename__ = 'contest_tag'
    # Many to many?
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    tag: Optional[str] = Column(String, index=True)

    contest_id: Optional[str] = Column(String, ForeignKey('contest.key'))
    contest: Optional['Contest'] = relationship('Contest', back_populates='_tags')

    def __init__(self, tag):
        self.tag = tag


class Contest(Base):
    __tablename__ = 'contest'

    key: str = Column(String, primary_key=True)
    name: Optional[str] = Column(String, index=True)
    start_time: Optional[datetime] = Column(DateTime, index=True)
    end_time: Optional[datetime] = Column(DateTime, index=True)
    time_limit: Optional[float] = Column(Float)
    is_rated: Optional[bool] = Column(Boolean)
    rate_all: Optional[bool] = Column(Boolean)
    has_rating: Optional[bool] = Column(Boolean)
    rating_floor: Optional[int] = Column(Integer)
    rating_ceiling: Optional[int] = Column(Integer)
    hidden_scoreboard: Optional[bool] = Column(Boolean, index=True)
    scoreboard_visibility: Optional[str] = Column(String, index=True)
    is_organization_private: Optional[bool] = Column(Boolean, index=True)
    is_private: Optional[bool] = Column(Boolean, index=True)
    format__name: Optional[str] = Column(String)
    format__config__cumtime: Optional[bool] = Column(Boolean)
    format__config__first_ac_bonus: Optional[int] = Column(Integer)
    format__config__time_bonus: Optional[int] = Column(Integer)

    problems: List[ContestProblem] = \
        relationship('ContestProblem', back_populates='contest', cascade='all, delete')
    _tags: List[ContestTag] = \
        relationship('ContestTag', back_populates='contest', cascade='all, delete')
    tags: List[str] = association_proxy('_tags', 'tag')
    # TODO: Check if this has the correct behavior when deleted
    organizations: List['Organization'] = \
        relationship('Organization', secondary=lambda: contest_organization, back_populates='contests')
    solutions = relationship('ParticipationSolution', cascade='all, delete', back_populates='contest')
    rankings: List[Participation] = relationship('Participation', back_populates='contest',
                                                 cascade='all, delete')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ProblemType(Base):
    # Many to many?
    __tablename__ = 'problem_type'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    type: Optional[int] = Column(Integer, index=True)

    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: Optional['Problem'] = relationship('Problem', back_populates='_types')

    def __init__(self, type):
        self.type = type


class ProblemLanguageLimit(Base):
    __tablename__ = 'problem_language_limit'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    type: Optional[int] = Column(Integer, index=True)
    time_limit: Optional[float] = Column(Float)
    memory_limit: Optional[int] = Column(Integer)

    language_id: Optional[str] = Column(String, ForeignKey('language.key'))
    language: Optional['Language'] = relationship('Language')
    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: Optional['Problem'] = relationship('Problem', back_populates='language_resource_limits')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Problem(Base):
    __tablename__ = 'problem'

    code: str = Column(String, primary_key=True)
    name: Optional[str] = Column(String, index=True)
    group: Optional[str] = Column(String, index=True)
    time_limit: Optional[float] = Column(Float)
    memory_limit: Optional[int] = Column(Integer)
    points: Optional[int] = Column(Integer, index=True)
    partial: Optional[bool] = Column(Boolean)
    short_circuit: Optional[bool] = Column(Boolean)
    is_organization_private: Optional[bool] = Column(Boolean, index=True)
    is_public: Optional[bool] = Column(Boolean, index=True)

    languages: List['Language'] = relationship('Language', secondary=lambda: language_problem,
                                               back_populates='problems')
    organizations: List['Organization'] = relationship('Organization', secondary=lambda: organization_problem,
                                                       back_populates='problems')
    _types: List[ProblemType] = relationship('ProblemType', back_populates='problem',
                                             cascade='all, delete')
    types: List[str] = association_proxy('_types', 'type')
    language_resource_limits: List[ProblemLanguageLimit] = \
        relationship('ProblemLanguageLimit', back_populates='problem', cascade='all, delete')
    submissions: List[Submission] = relationship('Submission', back_populates='problem')
    authors: List['User'] = relationship('User', secondary=lambda: problem_user,
                                         back_populates='problems_authored')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class UserVolatility(Base):
    # Many to many????
    __tablename__ = 'user_volatility'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    volatility: Optional[int] = Column(Integer, index=True)

    user_id: Optional[int] = Column(Integer, ForeignKey('user.id'))
    user: Optional['User'] = relationship('User', back_populates='vols')

    def __init__(self, volatility):
        self.volatility = volatility


class User(Base):
    __tablename__ = 'user'

    id: int = Column(Integer, primary_key=True)
    username: Optional[str] = Column(String, index=True)
    points: Optional[float] = Column(Float, index=True)
    performance_points: Optional[float] = Column(Float)
    problem_count: Optional[int] = Column(Integer)
    rank: Optional[str] = Column(String)
    rating: Optional[int] = Column(Integer)
    volatility: Optional[int] = Column(Integer)

    organizations: List['Organization'] = relationship('Organization', secondary=lambda: organization_user,
                                                       back_populates='users')
    # NOTE: For now, the api returns contests in different ways,
    # will implement volatilities once contests are more consistent
    vols: List[UserVolatility] = relationship('UserVolatility', back_populates='user',
                                              cascade='all, delete')
    volatilities: List[int] = association_proxy('vols', 'volatility')
    contests: List[Participation] = relationship('Participation', back_populates='user', passive_deletes=True)
    submissions: List[Submission] = relationship('Submission', back_populates='user',
                                                 passive_deletes=True)
    problems_authored: List[Problem] = relationship('Problem', secondary=lambda: problem_user,
                                                    back_populates='authors', passive_deletes=True)
    solved_problems: List[Problem] = \
        relationship("Problem", secondary=Submission.__table__,
                     primaryjoin="and_(User.id == Submission.user_id, Submission.result == 'AC')",
                     viewonly=True)

    contests: List[Contest] = relationship('Participation', back_populates='user')

    def __init__(self, obj):
        # TODO Add max_rating hybrid property
        AttrMixin.__init__(self, obj)


class Judge(Base):
    __tablename__ = 'judge'

    name: str = Column(String, primary_key=True)
    start_time: Optional[datetime] = Column(DateTime)
    ping: Optional[float] = Column(Float)
    load: Optional[float] = Column(Float)
    languages: List['Language'] = relationship('Language', secondary=lambda: judge_language,
                                               back_populates='judges')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Language(Base):
    __tablename__ = 'language'

    id: int = Column(Integer, primary_key=True)
    key: Optional[str] = Column(String, index=True)
    short_name: Optional[str] = Column(String)
    common_name: Optional[str] = Column(String)
    ace_mode_name: Optional[str] = Column(String)
    pygments_name: Optional[str] = Column(String)
    code_template: Optional[str] = Column(String)

    judges: List[Judge] = relationship('Judge', secondary=lambda: judge_language,
                                       back_populates='languages')
    problems: List[Problem] = relationship('Problem', secondary=lambda: language_problem,
                                           back_populates='languages')
    submissions: List[Submission] = relationship('Submission', back_populates='language')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Organization(Base):
    __tablename__ = 'organization'

    id: int = Column(Integer, primary_key=True)
    slug: Optional[str] = Column(String, index=True)
    short_name: Optional[str] = Column(String)
    is_open: Optional[bool] = Column(Boolean)
    member_count: Optional[int] = Column(Integer)

    users: List[User] = relationship('User', secondary=lambda: organization_user,
                                     back_populates='organizations')
    problems: List[Problem] = relationship('Problem', secondary=lambda: organization_problem,
                                           back_populates='organizations')
    contests: List[Contest] = relationship('Contest', secondary=lambda: contest_organization,
                                           back_populates='organizations')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Handle(Base):
    __tablename__ = 'handle'
    # NOTE: Should there be a foreign key to user?

    _id: int = Column(Integer, primary_key=True, autoincrement=True)
    id: Optional[int] = Column(Integer, index=True)
    handle: Optional[str] = Column(String, index=True)
    user_id: Optional[int] = Column(Integer, index=True)
    guild_id: Optional[int] = Column(Integer, index=True)


class Gitgud(Base):
    __tablename__ = 'gitgud'
    # NOTE: Should there be a foreign key to user?

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    handle: Optional[str] = Column(String, index=True)
    guild_id: Optional[int] = Column(Integer, index=True)
    point: Optional[int] = Column(Integer)
    time: Optional[datetime] = Column(DateTime, index=True)

    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: List[Problem] = relationship('Problem')


class CurrentGitgud(Base):
    __tablename__ = 'current_gitgud'
    # NOTE: Should there be a foreign key to user?

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    handle: Optional[str] = Column(String)
    guild_id: Optional[int] = Column(Integer)
    point: Optional[int] = Column(Integer)
    time: Optional[datetime] = Column(DateTime, index=True)

    problem_id: Optional[str] = Column(String, ForeignKey('problem.code'))
    problem: List[Problem] = relationship('Problem')


contest_organization = Table(
    'contest_organization', Base.metadata,
    Column('contest_id', String, ForeignKey('contest.key'), primary_key=True),
    Column('organization_id', Integer, ForeignKey('organization.id'), primary_key=True),
)

judge_language = Table(
    'judge_language', Base.metadata,
    Column('judge_id', String, ForeignKey('judge.name'), primary_key=True),
    Column('language_id', Integer, ForeignKey('language.id'), primary_key=True),
)

language_problem = Table(
    'language_problem', Base.metadata,
    Column('problem_id', String, ForeignKey('problem.code'), primary_key=True),
    Column('language_id', Integer, ForeignKey('language.id'), primary_key=True),
)

organization_problem = Table(
    'organization_problem', Base.metadata,
    Column('problem_id', String, ForeignKey('problem.code'), primary_key=True),
    Column('organization_id', Integer, ForeignKey('organization.id'), primary_key=True),
)

organization_user = Table(
    'organization_user', Base.metadata,
    Column('organization_id', Integer, ForeignKey('organization.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
)

participation_user = Table(
    'participation_user', Base.metadata,
    Column('participation_id', Integer, ForeignKey('participation.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
)

problem_user = Table(
    'problem_user', Base.metadata,
    Column('problem_code', String, ForeignKey('problem.code'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
)
# Base.metadata.create_all(engine)
