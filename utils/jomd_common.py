import asyncio
import typing
from utils.query import Query
import random
import hikari
from lightbulb.converters import base
import typing as t
import re


def list_to_str(arg):
    if arg is None:
        return None
    return "&".join(arg)


def str_to_list(arg):
    if arg is None:
        return None
    return arg.split("&")


def is_int(val):
    return re.match(r"[-+]?\d+", val) is not None


class PointRangeConverter(base.BaseConverter[t.List[int]]):
    """Implementation of the base converter for converting arguments into a point range."""

    __slots__ = ()

    async def convert(self, arg: str) -> t.List[int]:
        try:
            if "-" in arg:
                arg = arg.split("-")
                if len(arg) != 2:
                    raise TypeError("Too many arguements, invalid range")
                return list(map(int, arg))
            point_high = point_low = int(arg)
            return [point_high, point_low]
        except ValueError:
            raise TypeError("Point value is not an integer")


# def parse_gimme(argument) -> typing.Optional[str]:
# keywords = [
#         'adhoc', 'Ad Hoc', 'math', 'Advanced Math', 'Intermediate Math',
#         'Simple Math', 'bf', 'Brute Force', 'ctf', 'Capture the Flag', 'ds',
#         'Data Structures', 'd&c', 'Divide and Conquer', 'dp',
#         'Dynamic Programming', 'geo', 'Geometry', 'gt', 'Graph Theory',
#         'greedy', 'Greedy Algorithms', 'regex', 'Regular Expressions',
#         'string', 'String Algorithms'
#     ]
#     if argument in keywords:
#         raise BadArgument('Argument is keyword')

#     try:
#         point_range(argument)
#     except BadArgument:
#         return argument.replace('\'', '')
#     raise BadArgument('Argument is point range')


def calculate_points(points, fully_solved):
    b = 150 * (1 - 0.997**fully_solved)
    p = 0
    for i in range(min(100, len(points))):
        p += (0.95**i) * points[i]
    return b + p


async def gimme_common(username, points, types):
    query = Query()
    unsolved = query.get_unsolved_problems(username, types, points[0], points[1])

    if len(unsolved) == 0:
        return None, None

    problem = random.choice(unsolved)

    # Sometimes the problem might not contain the memory info
    # so we need to call the api
    problem = await query.get_problem(problem.code)

    points = str(problem.points)
    if problem.partial:
        points += "p"

    memory = problem.memory_limit
    if memory >= 1024 * 1024:
        memory = "%dG" % (memory // 1024 // 1024)
    elif memory >= 1024:
        memory = "%dM" % (memory // 1024)
    else:
        memory = "%dK" % (memory)

    embed = hikari.Embed(
        title=problem.name,
        url="https://dmoj.ca/problem/%s" % problem.code,
        description="Points: %s\nProblem Types: %s" % (points, ", ".join(problem.types)),
        color=0xFCDB05,
    )

    embed.set_thumbnail(await query.get_pfp(username))
    embed.add_field(name="Group", value=problem.group, inline=True)
    embed.add_field(name="Time", value="%ss" % problem.time_limit, inline=True)
    embed.add_field(name="Memory", value=memory, inline=True)

    return embed, problem
