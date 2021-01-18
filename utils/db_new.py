from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, String, Integer, Date, String, TypeDecorator,
                        Float, Boolean, DateTime, JSON, Table, ForeignKey,
                        Text)
from sqlalchemy.orm import relationship
# Will cause a cycle but don't worry as it is not used
# only to specify types
# will remove to be safe
# from utils.api_new import (Problem as Problem_API, Contest as Contest_API,
#                            Participation as Participation_API,
#                            User as User_API, Submission as Submission_API,
#                            Organization as Organization_API,
#                            Language as Language_API, Judge as Judge_API)
from utils.constants import DEBUG_DB
import json

URI = 'sqlite:///utils/db/JOMD1.db'

Base = declarative_base()
engine = create_engine(URI, echo=DEBUG_DB)
Session = sessionmaker(bind=engine, autoflush=False)
session = Session()


class Json(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


contest_problem = Table(
    'contest_problem', Base.metadata,
    Column('contest_id', String, ForeignKey('contest.key')),
    Column('problem_id', String, ForeignKey('problem.code')),
)

contest_participation = Table(
    'contest_participation', Base.metadata,
    Column('contest_id', String, ForeignKey('contest.key')),
    Column('participation_id', String, ForeignKey('participation.id')),
)

contest_user = Table(
    'contest_user', Base.metadata,
    Column('contest_id', String, ForeignKey('contest.key')),
    Column('user_id', Integer, ForeignKey('user.id')),
)

problem_user = Table(
    'problem_user', Base.metadata,
    Column('problem_id', String, ForeignKey('problem.code')),
    Column('user_id', Integer, ForeignKey('user.id')),
)

language_problem = Table(
    'language_problem', Base.metadata,
    Column('problem_id', String, ForeignKey('problem.code')),
    Column('language_id', Integer, ForeignKey('language.id')),
)

organization_problem = Table(
    'organization_problem', Base.metadata,
    Column('problem_id', String, ForeignKey('problem.code')),
    Column('organization_id', Integer, ForeignKey('organization.id')),
)

contest_organization = Table(
    'contest_organization', Base.metadata,
    Column('contest_id', String, ForeignKey('contest.key')),
    Column('organization_id', Integer, ForeignKey('organization.id')),
)

participation_user = Table(
    'participation_user', Base.metadata,
    Column('participation_id', String, ForeignKey('participation.id')),
    Column('user_id', Integer, ForeignKey('user.id')),
)

language_submission = Table(
    'language_submission', Base.metadata,
    Column('language_id', Integer, ForeignKey('language.id')),
    Column('submission_id', Integer, ForeignKey('submission.id')),
)

organization_user = Table(
    'organization_user', Base.metadata,
    Column('organization_id', Integer, ForeignKey('organization.id')),
    Column('user_id', Integer, ForeignKey('user.id')),
)

judge_language = Table(
    'judge_language', Base.metadata,
    Column('judge_id', String, ForeignKey('judge.name')),
    Column('language_id', Integer, ForeignKey('language.id')),
)

submission_user = Table(
    'submission_user', Base.metadata,
    Column('submission_id', Integer, ForeignKey('submission.id')),
    Column('user_id', Integer, ForeignKey('user.id')),
)

problem_submission = Table(
    'problem_submission', Base.metadata,
    Column('submission_id', Integer, ForeignKey('submission.id')),
    Column('problem_id', String, ForeignKey('problem.code')),
)


class Problem(Base):
    __tablename__ = 'problem'

    code = Column(String, primary_key=True)
    name = Column(String)
    # authors = relationship('User', secondary=problem_author_user,
    #                        back_populates='authored')
    authors = Column(Json)
    types = Column(Json)
    group = Column(String)
    time_limit = Column(Float)
    memory_limit = Column(Integer)
    language_resource_limits = Column(Json)
    points = Column(Integer)
    partial = Column(Boolean)
    short_circuit = Column(Boolean)
    languages = relationship("Language", secondary=language_problem,
                             back_populates='problems')
    is_organization_private = Column(Boolean)
    organizations = relationship("Organization",
                                 secondary=organization_problem,
                                 back_populates='problems')
    is_public = Column(Boolean)

    contests = relationship("Contest", secondary=contest_problem,
                            back_populates='problems')
    solved_users = relationship('User', secondary=problem_user,
                                back_populates='solved_problems')
    submissions = relationship('Submission', secondary=problem_submission,
                               back_populates='problem')

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
    __tablename__ = 'contest'

    key = Column(String, primary_key=True)
    name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    time_limit = Column(Integer)
    is_rated = Column(Boolean)
    rate_all = Column(Boolean)
    has_rating = Column(Boolean)
    rating_floor = Column(Integer)
    rating_ceiling = Column(Integer)
    hidden_scoreboard = Column(Boolean)
    is_organization_private = Column(Boolean)
    organizations = relationship('Organization',
                                 secondary=contest_organization,
                                 back_populates='contest')
    is_private = Column(Boolean)
    tags = Column(Json)
    _format = Column('format', Json)
    rankings = Column(Json)
    problems = relationship('Problem', secondary=contest_problem,
                            back_populates='contests')

    participations = relationship('Participation',
                                  secondary=contest_participation,
                                  back_populates='contest')
    users = relationship('User', secondary=contest_user,
                         back_populates='contests')

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
    __tablename__ = 'participation'

    id = Column(String, primary_key=True)
    user = relationship('User', secondary=participation_user,
                        back_populates='participation')
    contest = relationship('Contest', secondary=contest_participation,
                           back_populates='participations')
    score = Column(Float)
    cumulative_time = Column(Integer)
    tiebreaker = Column(Float)
    is_disqualified = Column(Boolean)
    virtual_participation_number = Column(Integer)

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
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    points = Column(Float)
    performance_points = Column(Float)
    problem_count = Column(Integer)
    rank = Column(String)
    rating = Column(Integer)
    volatility = Column(Integer)
    solved_problems = relationship('Problem', secondary=problem_user,
                                   back_populates='solved_users')
    organizations = relationship('Organization', secondary=organization_user,
                                 back_populates='users')
    contests = relationship('Contest', secondary=contest_user,
                            back_populates='users')

    # authored = relationship('Problem', secondary=problem_author_user,
    #                         back_populates='authors')
    participation = relationship('Participation', secondary=participation_user,
                                 back_populates='user')
    submissions = relationship('Submission', secondary=submission_user,
                               back_populates='user')

    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.points = user.points
        self.performance_points = user.performance_points
        self.problem_count = user.problem_count
        self.rank = user.rank
        self.rating = user.rating
        self.volatility = user.volatility
        self.solved_problems += user.solved_problems
        self.organizations += user.organizations
        self.contests += user.contests
        

class Submission(Base):
    __tablename__ = 'submission'

    id = Column(Integer, primary_key=True)
    problem = relationship('Problem', secondary=problem_submission,
                           back_populates='submissions')
    user = relationship('User', secondary=submission_user,
                        back_populates='submissions')
    date = Column(DateTime)
    language = relationship('Language', secondary=language_submission,
                            back_populates='submissions')
    time = Column(Float)
    memory = Column(Float)
    points = Column(Float)
    result = Column(String)
    status = Column(String)
    case_points = Column(Float)
    case_total = Column(Float)
    cases = Column(Json)

    def __init__(self, submission):
        self.id = submission.id
        self.problem.append(submission.problem)
        self.user.append(submission.user)
        self.date = submission.date
        self.language.append(submission.language)
        self.time = submission.time
        self.memory = submission.memory
        self.points = submission.points
        self.result = submission.result
        self.status = submission.status
        self.case_points = submission.case_points
        self.case_total = submission.case_total
        self.cases = submission.cases


class Organization(Base):
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    slug = Column(String)
    short_name = Column(String)
    is_open = Column(Boolean)
    member_count = Column(Integer)

    problems = relationship('Problem', secondary=organization_problem,
                            back_populates='organizations')
    contest = relationship('Contest', secondary=contest_organization,
                           back_populates='organizations')
    users = relationship('User', secondary=organization_user,
                         back_populates='organizations')

    def __init__(self, organization):
        self.id = organization.id
        self.slug = organization.slug
        self.short_name = organization.short_name
        self.is_open = organization.is_open
        self.member_count = organization.member_count


class Language(Base):
    __tablename__ = 'language'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    short_name = Column(String)
    common_name = Column(String)
    ace_mode_name = Column(String)
    pygments_name = Column(String)
    code_template = Column(String)

    problems = relationship('Problem', secondary=language_problem,
                            back_populates='languages')
    submissions = relationship('Submission', secondary=language_submission,
                               back_populates='language')
    judges = relationship('Judge', secondary=judge_language,
                          back_populates='languages')

    def __init__(self, language):
        self.id = language.id
        self.key = language.key
        self.short_name = language.short_name
        self.common_name = language.common_name
        self.ace_mode_name = language.ace_mode_name
        self.pygments_name = language.pygments_name
        self.code_template = language.code_template


# I don't thinkg I'll ever use this
class Judge(Base):
    __tablename__ = 'judge'

    name = Column(String, primary_key=True)
    start_time = Column(DateTime)
    ping = Column(Float)
    load = Column(Float)
    languages = relationship('Language', secondary=judge_language,
                             back_populates='judges')

    def __init__(self, judge):
        self.name = judge.name
        self.start_time = judge.start_time
        self.ping = judge.ping
        self.load = judge.load
        for language_key in judge.languages:
            language = session.query(Language).\
                filter(Language.key == language_key).first()
            self.languages.append(language)


Base.metadata.create_all(engine)
