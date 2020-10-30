from utils.db import DbConn
from utils.problem import Problem
from utils.api import problem_api
import time


def main():
    page = 1
    db = DbConn()
    while True:
        data = problem_api.get_problems(page)
        problems = data['data']['objects']
        for problem in problems:
            code = problem['code']
            problem = problem_api.get_problem(code)
            problem = Problem.loads(problem['data']['object'])
            print(problem)
            if problem.is_public:
                db.cache_problem(problem)
            time.sleep(0.7)
        if not data['data']['has_more']:
            break
        page += 1


if __name__ == '__main__':
    main()
