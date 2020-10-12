import json
import sqlite3

class JOMDdb:
    def __init__(self):
        self.conn = sqlite3.connect('db/JOMD.db')
        self.init_tables()
    
    def init_tables(self):
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS problems ('
            'code           TEXT PRIMARY KEY,'
            'name           TEXT,'
            'types          TEXT,'
            'category       TEXT,'
            'time_limit     REAL,'
            'memory_limit   INTEGER,'
            'points         REAL,'
            'is_partial     BOOLEAN'
            ')'
        )
        
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS submissions ('
            'id             INTEGER PRIMARY KEY,'
            'problem        TEXT,'
            'user           TEXT,'
            'date           DATE,'
            'language       TEXT,'
            'time           REAL,'
            'memory         REAL,'
            'points         REAL,'
            'result         TEXT'
            ')'
        )

    def cache_problem(self,problems):
        query = ('INSERT OR REPLACE INTO problems VALUES'
                '(?, ?, ?, ?, ?, ?, ?, ?)')
        problems = map(problem_dict_to_tuple, problems)
        self.conn.executemany(query,problems)
        self.conn.commit()

    def cache_submission(self,submissions):
        query = ('INSERT OR REPLACE INTO submissions VALUES'
                '(?, ?, ?, ?, ?, ?, ?, ?, ?)')
        submissions = map(submission_dict_to_tuple, submissions)
        self.conn.executemany(query,submissions)
        self.conn.commit()
    
    def get_problems(self,code):
        query = ('SELECT * FROM problems WHERE '
                'code = ?')
        res = self.conn.execute(query,(code,)).fetchall()
        return list(map(problem_tuple_to_dict,res))

    def get_submissions(self, username):
        query = ('SELECT * FROM submissions WHERE '
                'user = ?')
        res = self.conn.execute(query,(username,)).fetchall()
        return list(map(submission_tuple_to_dict,res))
    
    def get_unsolvedproblems(self, username, low, high):
        query = ('SELECT problem.* FROM '
                'problems problem LEFT JOIN '
                '(SELECT problem, max(points) points FROM submissions WHERE user=? GROUP BY problem) '
                'submission ON submission.problem = problem.code WHERE '
                'ifnull(submission.points, 0) < problem.points AND '
                '(problem.points BETWEEN ? AND ?)')
        res = self.conn.execute(query,(username,low,high,)).fetchall()
        return list(map(problem_tuple_to_dict,res))
    def close(self):
        self.conn.close()

#code, name, types, category, time_limit, memory_limit, points, is_partial
def problem_tuple_to_dict(problem):
    return {
        'code':problem[0],
        'name':problem[1],
        'types':problem[2].split('&'),
        'group':problem[3],
        'time_limit':problem[4],
        'memory_limit':problem[5],
        'points':problem[6],
        'partial':problem[7],
    }

def problem_dict_to_tuple(problem):
    return (
        problem['code'],
        problem['name'],
        '&'.join(problem['types']),
        problem['group'],
        problem['time_limit'],
        problem['memory_limit'],
        problem['points'],
        problem['partial'],
    )

def submission_tuple_to_dict(submission):
    return {
        'id':submission[0],
        'problem':submission[1],
        'user':submission[2],
        'date':submission[3],
        'language':submission[4],
        'time':submission[5],
        'memory':submission[6],
        'points':submission[7],
        'result':submission[8],
    }

def submission_dict_to_tuple(submission):
    return (
        submission['id'],
        submission['problem'],
        submission['user'],
        submission['date'],
        submission['language'],
        submission['time'] if submission['time'] else 0.0,
        submission['memory'] if submission['memory'] else 0.0,
        submission['points'] if submission['points'] else 0.0,
        submission['result'],
    )