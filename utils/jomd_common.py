from discord.ext.commands.errors import BadArgument
import typing
from utils.query import Query
import random
import discord

def list_to_str(arg):
    if arg is None:
        return None
    return '&'.join(arg)


def str_to_list(arg):
    if arg is None:
        return None
    return arg.split('&')


def is_int(val):
    try:
        int(val)
        return True
    except (TypeError, ValueError):
        return False


def str_not_int(argument) -> typing.Optional[str]:
    if is_int(argument):
        raise BadArgument("Passed argument is not int")
    return argument.replace('\'', '')


def point_range(argument) -> typing.Optional[list]:
    if '-' in argument:
        argument = argument.split('-')
        if len(argument) != 2:
            raise BadArgument('Too many -, invalid range')
        try:
            point_high = int(argument[0])
            point_low = int(argument[1])
            return [point_high, point_low]
        except ValueError as e:
            raise BadArgument('Point values are not an integer')
    try:
        point_high = point_low = int(argument)
        return [point_high, point_low]
    except ValueError as e:
        raise BadArgument('Point value is not an integer')


def parse_gimme(argument) -> typing.Optional[str]:
    keywords = [
        'adhoc', 'Ad Hoc', 'math', 'Advanced Math', 'Intermediate Math',
        'Simple Math', 'bf', 'Brute Force', 'ctf', 'Capture the Flag', 'ds',
        'Data Structures', 'd&c', 'Divide and Conquer', 'dp',
        'Dynamic Programming', 'geo', 'Geometry', 'gt', 'Graph Theory',
        'greedy', 'Greedy Algorithms', 'regex', 'Regular Expressions',
        'string', 'String Algorithms'
    ]
    if argument in keywords:
        raise BadArgument("Argument is keyword")

    try:
        print(point_range(argument))
    except BadArgument:
        return argument.replace('\'', '')
    raise BadArgument("Argument is point range")


def calculate_points(points, fully_solved):
    b = 150*(1-0.997**fully_solved)
    p = 0
    for i in range(min(100, len(points))):
        p += (0.95**i)*points[i]
    return b+p


async def gimme_common(username, points, types):
    query = Query()
    unsolved = query.get_unsolved_problems(username, types, points[0],
                                           points[1])

    if len(unsolved) == 0:
        return None, None

    problem = random.choice(unsolved)

    points = str(problem.points)
    if problem.partial:
        points += 'p'

    memory = problem.memory_limit
    if memory >= 1024*1024:
        memory = '%dG' % (memory//1024//1024)
    elif memory >= 1024:
        memory = '%dM' % (memory//1024)
    else:
        memory = '%dK' % (memory)

    embed = discord.Embed(
        title=problem.name,
        url='https://dmoj.ca/problem/%s' % problem.code,
        description='Points: %s\nProblem Types: %s' %
                    (points, ', '.join(problem.types)),
        color=0xfcdb05,
    )

    embed.set_thumbnail(url=await query.get_pfp(username))
    embed.add_field(name='Group', value=problem.group, inline=True)
    embed.add_field(
        name='Time',
        value='%ss' % problem.time_limit,
        inline=True
    )
    embed.add_field(name='Memory', value=memory, inline=True)

    return embed, problem
