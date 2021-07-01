from operator import add
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, String, Integer, DateTime, Float, Boolean, Table, ForeignKey, Text)
from sqlalchemy.ext.associationproxy import association_proxy
# Topologogical order
# Submission
# Participation
# Contest
# Problem
# User
# Judge
# Language
# Organization

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
]

URI = 'sqlite:///utils/db/JOMD1.db'

engine = create_engine(URI)
Base = declarative_base(bind=engine)
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
                if type(cfg[key]) is dict:
                    init(getattr(obj, key), cfg[key], add_attr(attr, key))
                else:
                    setattr(self, add_attr(attr, key), getattr(obj, key))
        init(obj, self.cfg, '')

    def __getattr__(self, key):
        print("__getattr__", key)
        if not hasattr(self, 'cfg') or key not in self.cfg:
            return super().__getattr_(key)
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String)
    case_id = Column(Integer)
    status = Column(String)
    time = Column(Float)
    memory = Column(Float)
    points = Column(Float, index=True)
    total = Column(Float, index=True)
    submission_id = Column(Integer, ForeignKey('submission.id'))
    submission = relationship('Submission', back_populates='cases')


class Submission(Base, AttrMixin):
    __tablename__ = 'submission'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, index=True)
    time = Column(Float)
    memory = Column(Float)
    points = Column(Float)
    status = Column(String)
    result = Column(String)
    case_points = Column(Float)
    case_total = Column(Float)

    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem', back_populates='submissions')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='submissions')
    language_id = Column(Integer, ForeignKey('language.id'))
    language = relationship('Language', back_populates='submissions')
    cases = relationship('SubmissionCase', back_populates='submission')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ParticipationSolution(Base):
    __tablename__ = 'participation_solution'

    id = Column(Integer, primary_key=True, autoincrement=True)
    points = Column(Float, index=True)
    time = Column(Float)
    participation_id = Column(Integer, ForeignKey('participation.id'))
    participation = relationship('Participation', back_populates='solutions')


class Participation(Base, AttrMixin):
    __tablename__ = 'participation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    score = Column(Float)
    cumulative_time = Column(Integer)
    tiebreaker = Column(Float)
    old_rating = Column(Integer)
    new_rating = Column(Integer)
    is_disqualified = Column(Boolean)
    virtual_participation_number = Column(Integer)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='contests')
    contest_id = Column(String, ForeignKey('contest.key'))
    contest = relationship('Contest', back_populates='rankings')
    solutions = relationship('ParticipationSolution', back_populates='participation')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ContestProblem(Base):
    __tablename__ = 'contest_problem'

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_pretested = Column(Boolean, index=True)
    max_submissions = Column(Integer, index=True)
    label = Column(String, index=True)
    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem')
    contest_id = Column(String, ForeignKey('contest.key'))
    contest = relationship('Contest', back_populates='problems')


class ContestTag(Base):
    __tablename__ = 'contest_tag'
    # Many to many?
    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String, index=True)
    contest_id = Column(String, ForeignKey('contest.key'))
    contest = relationship('Contest', back_populates='_tags')


class Contest(Base, AttrMixin):
    __tablename__ = 'contest'

    key = Column(String, primary_key=True)
    name = Column(String, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    time_limit = Column(Float)
    is_rated = Column(Boolean)
    rate_all = Column(Boolean)
    has_rating = Column(Boolean)
    rating_floor = Column(Integer)
    rating_ceiling = Column(Integer)
    hidden_scoreboard = Column(Boolean, index=True)
    scoreboard_visibility = Column(String, index=True)
    is_organization_private = Column(Boolean, index=True)
    is_private = Column(Boolean, index=True)
    format__name = Column(String)
    format__config__cumtime = Column(Boolean)
    format__config__first_ac_bonus = Column(Integer)
    format__config__time_bonus = Column(Integer)

    problems = relationship('ContestProblem', back_populates='contest',
                            cascade='all, delete-orphan')
    _tags = relationship('ContestTags', back_populates='contest',
                         cascade='all, delete-orphan')
    tags = association_proxy('_tags', 'tag')
    organizations = relationship('Organization', secondary=lambda: contest_organization,
                                 back_populates='contests')
    rankings = relationship('Participation', back_populates='contest')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class ProblemType(Base):
    # Many to many?
    __tablename__ = 'problem_type'

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Integer, index=True)
    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem', back_populates='_types')


class ProblemLanguageLimit(Base):
    __tablename__ = 'problem_language_limit'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Integer, index=True)
    language_id = Column(String, ForeignKey('language.key'))
    language = relationship('Language')
    time_limit = Column(Float)
    memory_limit = Column(Integer)
    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem', back_populates='language_resource_limits')


class Problem(Base, AttrMixin):
    __tablename__ = 'problem'

    code = Column(String, primary_key=True)
    name = Column(String, index=True)
    group = Column(String, index=True)
    time_limit = Column(Float)
    memory_limit = Column(Integer)
    points = Column(Integer, index=True)
    partial = Column(Boolean)
    short_circuit = Column(Boolean)
    is_organization_private = Column(Boolean, index=True)
    is_public = Column(Boolean, index=True)

    languages = relationship('Language', secondary=lambda: language_problem,
                             back_populates='problems')
    organizations = relationship('Organization', secondary=lambda: organization_problem,
                                 back_populates='problems')
    _types = relationship('ProblemType', back_populates='problem',
                          cascade='all, delete-orphan')
    types = association_proxy('_types', 'type')
    language_resource_limits = relationship('ProblemLanguageLimit', back_populates='problem',
                                            cascade='all, delete-orphan')
    submissions = relationship('Submission', back_populates='problem')

    # authors = Column(User)

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class UserVolatility(Base):
    # Many to many????
    __tablename__ = 'user_volatility'

    id = Column(Integer, primary_key=True, autoincrement=True)
    volatility = Column(Integer, index=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='vols')


class User(Base, AttrMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, index=True)
    points = Column(Float, index=True)
    performance_points = Column(Float)
    problem_count = Column(Integer)
    rank = Column(String)
    rating = Column(Integer)
    volatility = Column(Integer)

    organizations = relationship('Organization', secondary=lambda: organization_user,
                                 back_populates='users')
    vols = relationship('UserVolatility', back_populates='user',
                        cascade='all, delete-orphan')
    volatilities = association_proxy('vols', 'volatility')
    contests = relationship('Participation', back_populates='user')
    submissions = relationship('Submission', back_populates='user')
    # solved_problems = [Problem]

    def __init__(self, obj):
        # https://stackoverflow.com/questions/19780178/sqlalchemy-hybrid-expression-with-relationship
        AttrMixin.__init__(self, obj)


class Judge(Base, AttrMixin):
    __tablename__ = 'judge'

    name = Column(String, primary_key=True)
    start_time = Column(DateTime)
    ping = Column(Float)
    load = Column(Float)
    languages = relationship('Language', secondary=lambda: judge_language,
                             back_populates='judges')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Language(Base, AttrMixin):
    __tablename__ = 'language'

    id = Column(Integer, primary_key=True)
    key = Column(String, index=True)
    short_name = Column(String)
    common_name = Column(String)
    ace_mode_name = Column(String)
    pygments_name = Column(String)
    code_template = Column(String)

    judges = relationship('Judge', secondary=lambda: judge_language,
                          back_populates='languages')
    problems = relationship('Problem', secondary=lambda: language_problem,
                            back_populates='languages')
    submissions = relationship('Submission', back_populates='language')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Organization(Base, AttrMixin):
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    slug = Column(String, index=True)
    short_name = Column(String)
    is_open = Column(Boolean)
    member_count = Column(Integer)

    users = relationship('User', secondary=lambda: organization_user,
                         back_populates='organizations')
    problems = relationship('Problem', secondary=lambda: organization_problem,
                            back_populates='organizations')
    contests = relationship('Contest', secondary=lambda: contest_organization,
                                 back_populates='organizations')

    def __init__(self, obj):
        AttrMixin.__init__(self, obj)


class Handle(Base):
    __tablename__ = 'handle'
    # NOTE: Should there be a foreign key to user?

    _id = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(Integer, index=True)
    handle = Column(String, index=True)
    user_id = Column(Integer, index=True)
    guild_id = Column(Integer, index=True)


class Gitgud(Base):
    __tablename__ = 'gitgud'
    # NOTE: Should there be a foreign key to user?

    _id = Column(Integer, primary_key=True, autoincrement=True)
    handle = Column(String, index=True)
    guild_id = Column(Integer, index=True)
    point = Column(Integer)
    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem')
    time = Column(DateTime, index=True)


class CurrentGitgud(Base):
    __tablename__ = 'current_gitgud'
    # NOTE: Should there be a foreign key to user?

    _id = Column(Integer, primary_key=True)
    handle = Column(String)
    guild_id = Column(Integer)
    problem_id = Column(String, ForeignKey('problem.code'))
    problem = relationship('Problem')
    point = Column(Integer)
    time = Column(DateTime, index=True)


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
    Column('participation_id', Integer, ForeignKey('participation.key'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
)
