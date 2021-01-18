class Submission:

    def __init__(self, args=None):
        self.score_num = None
        self.score_denom = None
        self.problem_name = None
        if args is None:
            self.id = None
            self.problem = None
            self.user = None
            self.date = None
            self.language = None
            self.time = None
            self.memory = None
            self.points = None
            self.result = None
        else:
            self.id = args[0]
            self.problem = args[1]
            self.user = args[2]
            self.date = args[3]
            self.language = args[4]
            self.time = args[5]
            self.memory = args[6]
            self.points = args[7]
            self.result = args[8]

    def __iter__(self):
        yield self.id
        yield self.problem
        yield self.user
        yield self.date
        yield self.language
        yield self.time if self.time else 0.0
        yield self.memory if self.memory else 0.0
        yield self.points if self.points else 0.0
        yield self.result

    def __str__(self):
        return str(tuple(self))

    @staticmethod
    def loads(data):
        submission = Submission()
        submission.id = data['id']
        submission.problem = data['problem']
        submission.user = data['user']
        submission.date = data['date']
        submission.language = data['language']
        submission.time = data['time'] if data['time'] else 0.0
        submission.memory = data['memory'] if data['memory'] else 0.0
        submission.points = data['points'] if data['points'] else 0.0
        submission.result = data['result']
        submission.score_num = data.get('score_num')
        submission.score_denom = data.get('score_denom')
        submission.problem_name = data.get('problem_name')
        return submission
