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
        if isinstance(solved_num, float):
            solved_num = 0
        df.plot(label='%s (%d)' % (username, solved_num))
    sns.set_style('whitegrid')
    plt.xlabel('Date')
    plt.ylabel('Problem Solved Count')
    plt.legend(loc='upper left', fontsize='8')
    plt.savefig('./graphs/plot.png')


def plot_points(datas):
    plt.clf()
    plt.subplots()
    for username, data in datas.items():
        df = pd.Series(data)
        df.plot(label='%s (%.2f)' % (username, df.max()))
    sns.set_style('whitegrid')
    plt.xlabel('Date')
    plt.ylabel('Points')
    plt.legend(loc='upper left', fontsize='8')
    plt.savefig('./graphs/plot.png')


def plot_rating(data):
    df = pd.DataFrame(data, columns=['username', 'rating', 'date'])

    fig, ax = plt.subplots()

    for (low, high), color in GRAPH_RANK_COLOURS.items():
        ax.axhspan(low, high, facecolor=color, alpha=0.8)

    # Set the theme
    plt.style.use('default')
    ax.grid(color='w', linestyle='solid', alpha=0.8)
    fig.gca().set_facecolor('#E7E7F0')

    # X-axis date formatting
    locator = mdt.AutoDateLocator(minticks=5, maxticks=8)
    formatter = mdt.ConciseDateFormatter(locator)
    fig.gca().xaxis.set_major_locator(locator)
    fig.gca().xaxis.set_major_formatter(formatter)

    # Set the X-axis scaling
    margin_x = timedelta(days=30)
    left = df['date'].min() - margin_x
    right = df['date'].max() + margin_x
    fig.gca().set_xlim(left=left, right=right)

    # Set the Y-axis scaling
    margin_y = 200
    bottom = min(1000, df['rating'].min() - margin_y)
    top = df['rating'].max() + margin_y
    fig.gca().set_ylim(bottom=bottom, top=top)

    for username in df['username'].unique():
        data = df[df['username'] == username]
        data = data.pivot(index='date', columns='username')
        ax.plot(data, label=username, marker='s',
                markerfacecolor='white', linestyle='-', markersize=5,
                markeredgewidth=0.5)

    # Legend
    ax.legend(loc='upper left', prop={'size': 10})

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
    sns.set_style('whitegrid')
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
                '%.1f%%' % (scale / 4),
                '%.1f%%' % (scale / 2),
                '%.1f%%' % (3 * scale / 4)
            ],
            color='grey', size=7
        )
    else:
        plt.yticks(
            [scale / 4, scale / 2, 3 * scale / 4],
            [
                '%.1f' % (scale / 4),
                '%.1f' % (scale / 2),
                '%.1f' % (3 * scale / 4)
            ],
            color='grey', size=7
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
