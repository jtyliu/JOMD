import os
import discord
import dotenv
import json
import requests
import re

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

def get_placement(username):
    rank = None
    try:
        response = requests.get(f'https://dmoj.ca/user/{username}')
        rank = re.findall(r"<div><b class=\"semibold\">Rank by points:</b> #(.*)</div>",response.text)
    except:
        pass
    assert len(rank) == 1
    return rank[0]

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

def calculate_points(points):
    b = 150*(1-0.997**len(points))
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
    data = user['data']['object']
    print(user)
    if "error" in user:
        return await ctx.send(f'{username} does not exist on DMOJ')
    
    embed = discord.Embed(
                        title = username,
                        url = f'https://dmoj.ca/user/{username}',
                        description = 'Calculated points: %.2f' % data['performance_points'],
                        color=0xfcdb05
    )
    is_rated = lambda x:1 if x['rating'] is not None else 0
    embed.add_field(name="Placement", value=get_placement(username), inline=False)
    embed.add_field(name="Problems Solved", value=data['problem_count'], inline=False)
    embed.add_field(name="Rating", value=data['rating'], inline=True)
    embed.add_field(name="Contests Written", value=sum(map(is_rated,data['contests'])), inline=True)
    await ctx.send(embed=embed)
    return None

@bot.command(name='predict')
async def predict(ctx,*args):

    if len(args) > 10:
        return await ctx.send(f'Too many arguements, {pref}predict <user> <points>')

    if len(args) < 2:
        return await ctx.send(f'Too few arguements, {pref}predict <user> <points>')

    username = args[0]
    user = get_user(username)
    if "error" in user:
        return await ctx.send(f'{username} does not exist on DMOJ')
    
    await ctx.send(f'Fetching Submissions. This may take a few seconds')
    subs = get_submissions(username)

    code_to_points = dict()
    for i in subs:
        problem, points = i['problem'], i['points']
        if points is not None and points != 0:
            if problem not in code_to_points:
                code_to_points[problem]=points
            elif points>code_to_points[problem]:
                code_to_points[problem]=points

    points = list(code_to_points.values())
    points.sort(reverse=True)
    await ctx.send('Current points %.2f' % calculate_points(points))
    for i in args[1:]:
        points.insert(len(points),int(i))
        points.sort(reverse=True)
        updated_points=calculate_points(points)
        await ctx.send('Solved %s | Updated points %.2f' % (i,updated_points))



    


def main():
    print("Bot is Running")
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()