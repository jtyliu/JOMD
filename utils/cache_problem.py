from utils.db import DbConn
from utils.submission import Submission
from utils.problem import Problem
from JOMD import get_problems,get_problem
import time


def main():
    page = 1
    db = DbConn()
    while True:
        data = get_problems(page)
        problems = data['data']['objects']
        for problem in problems:
            code = problem['code']
            problem = get_problem(code)['data']['object']
            problem = Problem.loads(problem)
            print(problem)
            if problem.is_public:
                db.cache_problem(problem)
            time.sleep(0.7)
        if not data['data']['has_more']:
            break
        page += 1

if __name__ == '__main__':
    main()