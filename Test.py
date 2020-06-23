import requests
import re


def get_placement(username):
    response = requests.get(f'https://dmoj.ca/user/{username}').text
    rank = re.findall(r"<div><b class=\"semibold\">Rank by points:</b> #(.*)</div>",response)
    assert len(rank) == 1
    print(rank[0])


get_placement("JoshuaL")