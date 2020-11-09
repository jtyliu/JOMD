from discord.ext.commands.errors import BadArgument


def is_int(val):
    try:
        int(val)
        return True
    except (TypeError, ValueError):
        return False


def parse_user(username):
    # Should I provide a range?
    if is_int(username):
        return None, int(username)
    if username:
        username = username.replace('\'', '')
    return username, None


def parse_predict(username, points):
    username, point = parse_user(username)
    if point:
        points.insert(0, point)
    return username, points


def parse_gimme(username, points, filters, point_range):
    keywords = ['adhoc', 'Ad Hoc', 'math', 'Advanced Math', 'Intermediate Math', 'Simple Math', 'bf', 'Brute Force', 'ctf', 'Capture the Flag', 'ds', 'Data Structures', 'd&c', 'Divide and Conquer', 'dp', 'Dynamic Programming', 'geo', 'Geometry', 'gt', 'Graph Theory', 'greedy', 'Greedy Algorithms', 'regex', 'Regular Expressions', 'string', 'String Algorithms']

    try:
        if username is not None:
            points = point_range(username)
            username = None
    except BadArgument:
        if username in keywords:
            filters.insert(0, username)
            username = None

    if username:
        username = username.replace('\'', '')
    return username, points, filters
