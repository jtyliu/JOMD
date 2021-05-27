import matplotlib.pyplot as plt
import matplotlib.dates as mdt
import pandas as pd
import seaborn as sns
from utils.constants import GRAPH_RANK_COLOURS
from math import pi
from datetime import timedelta


categories = ['Users', 'DS', 'DP', 'GT', 'String', 'Math', 'Ad Hoc', 'Greedy']


def plot_solved(datas):
    plt.clf()
    plt.subplots()
    for username, data in datas.items():
        df = pd.Series(data)
        solved_num = df.max()
        print(type(solved_num))
        if isinstance(solved_num, float):
            solved_num = 0
        df.plot(label="%s (%d)" % (username, solved_num))
    sns.set_style("whitegrid")
    plt.xlabel('Date')
    plt.ylabel('Problem Solved Count')
    plt.legend(loc='upper left', fontsize='8')
    plt.savefig('./graphs/plot.png')


def plot_points(datas):
    plt.clf()
    plt.subplots()
    for username, data in datas.items():
        df = pd.Series(data)
        df.plot(label="%s (%.2f)" % (username, df.max()))
    sns.set_style("whitegrid")
    plt.xlabel('Date')
    plt.ylabel('Points')
    plt.legend(loc='upper left', fontsize='8')
    plt.savefig('./graphs/plot.png')


def plot_rating(data):
    # Setup
    plt.clf()
    users = data['users']
    data = sorted(list(data.items())[1:])

    # Make a list of tuples (user, user dates, user ratings)
    all_dates, all_ratings = [], []
    groups = []
    for i, user in enumerate(users):
        user_dates, user_ratings = [], []
        for date, ratings in data:
            if ratings[i] is not None:
                user_dates.append(date)
                user_ratings.append(ratings[i])
                all_dates.append(date)
                all_ratings.append(ratings[i])
        groups.append((user, user_dates, user_ratings))

    # Add the color blocks
    for (low, high), color in GRAPH_RANK_COLOURS.items():
        plt.axhspan(low, high, facecolor=color, alpha=0.8)

    # Set the theme
    plt.style.use('default')
    plt.grid(color='w', linestyle='solid', alpha=0.8)
    plt.gca().set_facecolor('#E7E7F0')

    # X-axis date formatting
    locator = mdt.AutoDateLocator(minticks=5, maxticks=8)
    formatter = mdt.ConciseDateFormatter(locator)
    plt.gca().xaxis.set_major_locator(locator)
    plt.gca().xaxis.set_major_formatter(formatter)

    # Set the X-axis scaling
    margin_x = timedelta(days=30)
    left = min(all_dates) - margin_x
    right = max(all_dates) + margin_x
    plt.gca().set_xlim(left=left, right=right)

    # Set the Y-axis scaling
    margin_y = 200
    bottom = min(1000, min(all_ratings) - margin_y)
    top = max(all_ratings) + margin_y
    plt.gca().set_ylim(bottom=bottom, top=top)

    # Plot the data
    for user, user_dates, user_ratings in groups:
        if user_ratings:
            label = f'{user} ({max(user_ratings)})'
        else:
            label = f'{user} (unrated)'
        plt.plot(user_dates, user_ratings, label=label, marker='s',
                 markerfacecolor='white', linestyle='-', markersize=5,
                 markeredgewidth=0.5)

    # Legend
    plt.legend(loc="upper left", prop={"size": 10})

    plt.savefig('./graphs/plot.png')


def plot_type_bar(data, as_percent):
    plt.clf()
    plt.subplots()
    df = pd.DataFrame(data)
    df.columns = categories
    ylabel = 'Points (%)' if as_percent else 'Points'
    df = pd.melt(df, id_vars='Users', var_name='Problem Type',
                 value_name=ylabel)
    sns.set_theme()
    sns.set_style("whitegrid")
    sns.barplot(x='Problem Type', y=ylabel, hue='Users', data=df,
                palette='tab10')
    plt.legend(loc='upper right', fontsize='8')
    plt.savefig('./graphs/plot.png')


def plot_type_radar(data, as_percent, maxval):
    # Code from
    # https://python-graph-gallery.com/391-radar-chart-with-several-individuals/
    plt.clf()
    plt.subplots()
    df = pd.DataFrame(data)

    # number of variable
    categories = list(df)[1:]
    N = len(categories)
    usernames = data['group']

    # What will be the angle of each axis in the plot?
    # (we divide the plot / number of variable)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # Initialise the spider plot
    ax = plt.subplot(111, polar=True)

    # If you want the first axis to be on top:
    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)

    # Draw one axe per variable + add labels labels yet
    plt.xticks(angles[:-1], categories)

    # Draw ylabels
    ax.set_rlabel_position(0)

    scale = maxval * 1.1
    if as_percent:
        plt.yticks(
            [scale / 4, scale / 2, 3 * scale / 4],
            [
                "%.1f%%" % (scale / 4),
                "%.1f%%" % (scale / 2),
                "%.1f%%" % (3 * scale / 4)
            ],
            color="grey", size=7
        )
    else:
        plt.yticks(
            [scale / 4, scale / 2, 3 * scale / 4],
            [
                "%.1f" % (scale / 4),
                "%.1f" % (scale / 2),
                "%.1f" % (3 * scale / 4)
            ],
            color="grey", size=7
        )
    plt.ylim(0, maxval * 1.1)

    # Plot each individual = each line of the data
    # I don't do a loop, because plotting more than
    # 3 groups makes the chart unreadable

    colours = ['b', 'g', 'r', 'c', 'm', 'y']

    for i in range(len(usernames)):
        values = df.loc[i].drop('group').values.flatten().tolist()
        values += values[:1]
        ax.plot(angles, values, colours[i], linewidth=1, linestyle='solid',
                label=usernames[i])
        ax.fill(angles, values, colours[i], alpha=0.1)

    # Add legend
    plt.legend(loc='lower right', bbox_to_anchor=(0.95, 0.95),
               labelspacing=0.1, fontsize='small')
    plt.savefig('./graphs/plot.png')
