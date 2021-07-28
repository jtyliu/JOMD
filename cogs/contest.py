from utils.jomd_common import scroll_message
from utils.constants import SITE_URL, TZ, ADMIN_ROLES
from utils.models import *
from utils.query import Query
from utils.api import ObjectNotFound
import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timezone
from sqlalchemy import orm
import asyncio
from operator import itemgetter, attrgetter

# Post new contests
# Rating change predictions for all users in a server


class ContestCog(commands.Cog, name='Contest'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['contest'], usage='[contest key] [+server, +all, dmoj_handles]')
    async def ranklist(self, ctx, key, *args):
        '''List rating predictions of a contest'''
        q = session.query(Contest).filter(Contest.key == key)
        # Clear cache
        if q.count():
            session.delete(q.scalar())
            session.commit()
        query = Query()
        try:
            contest = await query.get_contest(key)
            contest = session.query(Contest).\
                options(
                    orm.joinedload(Contest.rankings).
                    options(
                        orm.joinedload(Participation.solutions),
                        orm.joinedload(Participation.user),
                    ),
                    orm.joinedload(Contest.problems)
            ).filter(Contest.key == key).scalar()
        except ObjectNotFound:
            await ctx.send('Contest not found')
            return

        if contest.hidden_scoreboard and contest.end_time > datetime.utcnow():
            return await ctx.send('Contest ongoing')

        if contest.is_organization_private:
            return await ctx.send('Contest not found')

        q = session.query(Handle).filter(Handle.guild_id == ctx.guild.id)
        handles = q.all()

        usernames = []
        showAll = False
        if len(args) == 0:
            usernames += list(map(attrgetter('handle'), handles))
        for arg in args:
            arg = arg.lower()
            if arg == '+server':
                usernames += list(map(attrgetter('handle'), handles))
            elif arg == '+all':
                showAll = True
            else:
                usernames.append((await query.get_user(arg)).username)

        # The only way to calculate rating changes is by getting the volitility of all the users
        # that means 100+ seperate api calls
        # How does evan do it?
        # TODO: Use the custom api on evan's site
        import requests
        r = requests.get(f'https://evanzhang.ca/rating/contest/{key}/api')
        if r:
            rankings = r.json()['users']

        # Don't really need this, just sanity check
        # users = await asyncio.gather(*[query.get_user(username)
        #                              for username in users])
        # usernames = [user.username for user in users]
        # Filter for those who participated in contest
        user_rankings = session.query(User.username).join(User.contests).\
            join(Participation.contest).filter(Contest.key == contest.key).all()
        user_rankings = [username for (username,) in user_rankings]
        if showAll:
            usernames = list(set(user_rankings))
        else:
            usernames = list(set(usernames) & set(user_rankings))

        # The length is 0 is contest is still ongoing
        problems = len(contest.problems)

        data = []
        labels = [contest.problems[i].label for i in range(len(contest.problems))]

        for rank_num, ranking in enumerate(contest.rankings):
            # TODO: ok ish, but placements match the rankings
            for username in usernames:
                if ranking.user.username == username:
                    # If contest is not rated, this crashes
                    if contest.is_rated:
                        if username in rankings:
                            evan_ranking = rankings[username]
                            rank_dict = {
                                'rank': int(evan_ranking['rank']),
                                'username': username + ':',
                                'old_rating': evan_ranking['old_rating'],
                                'new_rating': evan_ranking['new_rating'],
                            }
                            if evan_ranking['rating_change'] and evan_ranking['rating_change'] > 0:
                                rank_dict['rating_change'] = '+' + str(evan_ranking['rating_change'])
                            else:
                                rank_dict['rating_change'] = evan_ranking['rating_change']
                        else:
                            # User joined contest but was not rated
                            # TODO: Placement does not match ranking
                            rank_dict = {
                                'rank': len(rankings) + 1,
                                'username': username + ':',
                                'old_rating': 'N/A',
                                'new_rating': 'N/A',
                                'rating_change': 'N/A'
                            }
                    else:
                        rank_dict = {
                            'rank': rank_num + 1,
                            'username': username + ':',
                        }
                    # This is a quick fix :>
                    problems = len(ranking.solutions)

                    # NOTE: For some reason solutions are not ordered by id but by points
                    ranking.solutions.sort(key=lambda x: x.id)

                    for cnt in range(problems):
                        solution = ranking.solutions[cnt]
                        label = labels[cnt]
                        if solution.points:
                            if int(solution.points) == solution.points:
                                rank_dict[label] = int(solution.points)
                            else:
                                rank_dict[label] = round(solution.points, 2)
                        else:
                            rank_dict[label] = '-'
                    data.append(rank_dict)
        max_len = {}
        max_len['rank'] = len('#')
        max_len['username'] = len('Handle')
        for i in range(problems):
            max_len[labels[i]] = len(labels[i])
        max_len['rating_change'] = max_len['old_rating'] = max_len['new_rating'] = 3

        for rank in data:
            for k, v in rank.items():
                max_len[k] = max(len(str(v)), max_len.get(k, 0))

        format_output = '{:>' + str(max_len['rank']) + '} '
        format_output += '{:' + str(max_len['username'] + 1) + '}  '
        for i in range(problems):
            format_output += '{:' + str(max_len[labels[i]]) + '} '

        to_format = [
            '#',
            'Handle',
            *[labels[i] for i in range(problems)],
        ]

        hyphen_format = [
            '—' * max_len['rank'],
            '—' * max_len['username'],
            *['—' * max_len[labels[i]] for i in range(problems)],
        ]
        if contest.is_rated:
            format_output += ' '
            format_output += '{:>' + str(max_len['rating_change']) + '}  '
            format_output += '{:' + str(max_len['old_rating']) + '} '
            format_output += '{:' + str(max_len['new_rating']) + '} '
            to_format += [
                '∆',
                'Old',
                'New',
            ]

            hyphen_format += [
                '—' * max_len['rating_change'],
                '—' * max_len['old_rating'],
                '—' * max_len['new_rating'],
            ]
        outputBegin = format_output.format(*to_format)
        outputBegin += '\n'
        hyphens = format_output.format(*hyphen_format)
        outputBegin += hyphens
        outputBegin += '\n'
        outputEnd = hyphens + '\n'

        content = []
        output = outputBegin

        data.sort(key=lambda x: x['rank'])

        for rank in data:
            if contest.is_rated:
                output += format_output.format(
                    rank['rank'],
                    rank['username'],
                    *[rank[labels[i]] for i in range(problems)],
                    str(rank['rating_change']),
                    str(rank['old_rating']),
                    str(rank['new_rating']),
                )
            else:
                output += format_output.format(
                    rank['rank'],
                    rank['username'],
                    *[rank[labels[i]] for i in range(problems)],
                )
            output += '\n'
            if(len(output) + len(outputEnd) * 2 > 1980):
                output += outputEnd
                content.append('```yaml\n' + output + '```')
                output = outputBegin
        output += outputEnd
        content.append('```yaml\n' + output + '```')
        await ctx.send('Results for ' + contest.name + ' (' + SITE_URL + 'contest/' + key + '): ')
        message = await ctx.send(content[0])
        await scroll_message(ctx, self.bot, message, content)

    @commands.command(aliases=['pc'], usage='[contest key]')
    async def postcontest(self, ctx, key, option=''):
        '''Updates post-contest role'''
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        def has_admin_perms(ctx):
            return any(get(ctx.guild.roles, name=role) in ctx.author.roles for role in ADMIN_ROLES)

        update_all = option == '+all' and has_admin_perms(ctx)

        query = Query()

        if not update_all:
            username = query.get_handle(ctx.author.id, ctx.guild.id)

            if username is None:
                return await ctx.send('Your account is not linked!')

        q = session.query(Contest).filter(Contest.key == key)
        # Clear cache
        if q.count():
            q.delete()
            session.commit()
        try:
            contest = await query.get_contest(key)
        except ObjectNotFound:
            await ctx.send('Contest not found')
            return

        if contest.is_organization_private:
            return await ctx.send('Contest not found')

        role = get(ctx.guild.roles, name='postcontest ' + key)
        if not role:
            return await ctx.send(f'No `postcontest {key}` role found.')

        if update_all:
            q = session.query(User).join(User.contests).\
                filter(Participation.contest_id == key).\
                filter(Participation.end_time < datetime.now(timezone.utc).astimezone()).\
                filter(Participation.virtual_participation_number == 0).subquery()
            q = session.query(Handle.id).join(q, q.c.username == Handle.handle).\
                filter(Handle.guild_id == ctx.guild.id)

            for (user_id,) in q:
                try:
                    await ctx.guild.get_member(user_id).add_roles(role)
                except discord.Forbidden:
                    return await ctx.send('No permission to assign the role')
            return await ctx.send('Updated post contest for ' + key)

        q = session.query(Participation.end_time).join(User.contests).\
            filter(User.username == username).\
            filter(Participation.contest_id == key).\
            filter(Participation.virtual_participation_number == 0)

        if q.count():
            end_time = q.scalar()

            if end_time > datetime.now(timezone.utc).astimezone():
                return await ctx.send('Your window is not done')
            else:
                try:
                    await ctx.author.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send('No permission to assign the role')
                return await ctx.send('You\'ve been added to post contest')
        return await ctx.send('You haven\'t joined the contest yet')


def setup(bot):
    bot.add_cog(ContestCog(bot))
