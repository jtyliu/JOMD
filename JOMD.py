import os
import discord
import dotenv
import json
import requests
import re
import time

from discord.ext import commands

dotenv.load_dotenv()

BOT_TOKEN=os.environ["JOMD_BOT_TOKEN"]
API_TOKEN=os.environ["JOMD_TOKEN"]

pref='+'
bot=commands.Bot(command_prefix=pref)

def get_user(username):
    api_json = None
    try:
        api_response = requests.get(f'https://dmoj.ca/api/v2/user/{username}')
        api_json = json.loads(api_response.text)
    except:
        pass
    return api_json

def get_pfp(username):
    pfp = None
    try:
        response = requests.get(f'https://dmoj.ca/user/{username}')
        pfp = re.findall(r"<div class=\"user-gravatar\">\n<img src=\"(.*)\" width=\"135px\" height=\"135px\">\n</div>",response.text)
    except:
        pass
    assert len(pfp) == 1
    return pfp[0]

def get_placement(username):
    rank = None
    try:
        response = requests.get(f'https://dmoj.ca/user/{username}')
        rank = re.findall(r"<div><b class=\"semibold\">Rank by points:</b> #(.*)</div>",response.text)
    except:
        pass
    assert len(rank) == 1
    return rank[0]

def get_problem(problem_code):
    problem_json = None
    try:
        response = requests.get(f'https://dmoj.ca/api/v2/problem/{problem_code}')
        problem_json = json.loads(response.text)
    except:
        pass
    return problem_json

def get_problems():
    problem_json = None
    try:
        response = requests.get(f'https://dmoj.ca/api/v2/problems')
        problem_json = json.loads(response.text)
    except:
        pass
    return problem_json

def get_submissions_page(username,page):
    submission_json = None
    try:
        response = requests.get(f'https://dmoj.ca/api/v2/submissions?user={username}&page={page}')
        submission_json = json.loads(response.text)
    except:
        pass
    return submission_json

def get_submissions(username):
    sub_json = get_submissions_page(username,1)
    submissions = sub_json['data']['objects']
    for i in range(2,sub_json['data']['total_pages']+1):
        sub_json = get_submissions_page(username,i)
        submissions += sub_json['data']['objects']
    return submissions

def calculate_points(points,fully_solved):
    b = 150*(1-0.997**fully_solved)
    p = 0
    for i in range(min(100,len(points))):
        p += (0.95**i)*points[i]
    return b+p

@bot.command(name='user')
async def user(ctx,*username):
    # Beautify the errors
    if len(username) > 1:
        return await ctx.send(f'Too many arguments, {pref}user <user>')
    
    if len(username) < 1:
        return await ctx.send(f'Too few arguments, {pref}user <user>')

    username=username[0]

    user = get_user(username)
    
    if "error" in user:
        return await ctx.send(f'{username} does not exist on DMOJ')
    
    data = user['data']['object']
    username = data['username']
    embed = discord.Embed(
                        title = username,
                        url = f'https://dmoj.ca/user/{username}',
                        description = 'Calculated points: %.2f' % data['performance_points'],
                        color=0xfcdb05
    )

    is_rated = lambda x:1 if x['rating'] is not None else 0

    embed.set_thumbnail(url=get_pfp(username))
    embed.add_field(name="Rank by points", value=get_placement(username), inline=False)
    embed.add_field(name="Problems Solved", value=data['problem_count'], inline=False)
    embed.add_field(name="Rating", value=data['rating'], inline=True)
    embed.add_field(name="Contests Written", value=sum(map(is_rated,data['contests'])), inline=True)
    await ctx.send(embed=embed)
    return None

@bot.command(name='predict')
async def predict(ctx,*args):

    if len(args) > 6:
        return await ctx.send(f'Too many arguments, {pref}predict <user> <points>')

    if len(args) < 2:
        return await ctx.send(f'Too few arguments, {pref}predict <user> <points>')

    username = args[0]
    user = get_user(username)
    if "error" in user:
        return await ctx.send(f'{username} does not exist on DMOJ')
    
    msg = await ctx.send(f'Fetching Submissions for {username}. This may take a few seconds')
    subs = get_submissions(username)
    
    problems = get_problems()['data']['objects']
    code_to_points = dict()
    problems_AC = dict()
    for i in subs:
        problem_code, points, result = i['problem'], i['points'], i['result']
        if points is not None and points != 0:

            if  result == 'AC' and problem_code not in problems_AC:
                problems_AC[problem_code]=1

            if problem_code not in code_to_points:
                code_to_points[problem_code]=points
            
            elif points>code_to_points[problem_code]:
                code_to_points[problem_code]=points

    fully_solved_problems=sum(list(problems_AC.values()))
    points = list(code_to_points.values())
    points.sort(reverse=True)
    embed = discord.Embed(
                    title='Point prediction', 
                    description='Current points: %.2fp' % calculate_points(points,fully_solved_problems), 
                    color=0xfcdb05
    )

    embed.set_thumbnail(url=get_pfp(username))

    for i in args[1:]:
        points.insert(len(points),int(i))
        fully_solved_problems+=1
        points.sort(reverse=True)
        updated_points=calculate_points(points,fully_solved_problems)
        embed.add_field(name="Solve another %sp" % i, value="Total points: %.2f" % updated_points, inline=False)
    await msg.edit(content='',embed=embed)



    


def main():
    print("Bot is Running")
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()