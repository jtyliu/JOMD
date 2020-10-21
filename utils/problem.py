import json

class Problem:

    def __init__(self, args=None):
        if args is None:
            self.code = None
            self.name = None
            self.types = None
            self.category = None
            self.time_limit = None
            self.memory_limit = None
            self.points = None
            self.is_partial = None
            self.is_organization_private = None
            self.is_public = None
        else:
            self.code = args[0]
            self.name = args[1]
            self.types = args[2].split('&')
            self.group = args[3]
            self.time_limit = args[4]
            self.memory_limit = args[5]
            self.points = args[6]
            self.partial = args[7]
            self.is_organization_private = args[8]
            self.is_public = args[9]

    def __iter__(self):
        yield self.code
        yield self.name
        yield '&'.join(self.types)
        yield self.group
        yield self.time_limit
        yield self.memory_limit
        yield self.points
        yield self.partial
        yield self.is_organization_private
        yield self.is_public
    
    def __str__(self):
        return str(tuple(self))

    @staticmethod
    def loads(data):
        problem = Problem()
        problem.code = data['code']
        problem.name = data['name']
        problem.types = data['types']
        problem.group = data['group']
        problem.time_limit = data['time_limit']
        problem.memory_limit = data['memory_limit']
        problem.points = data['points']
        problem.partial = data['partial']
        problem.is_organization_private = data['is_organization_private']
        problem.is_public = data['is_public']
        return problem