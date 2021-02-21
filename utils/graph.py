import matplotlib.pyplot as plt
import matplotlib.dates as mdt
import pandas as pd
from math import pi
import seaborn as sns


categories = ['Users', 'DS', 'DP', 'GT', 'String', 'Math', 'Ad Hoc', 'Greedy']

# TODO: Fiddle around with matplotlib to make the graphs look better

def plot_solved(datas):
    plt.clf()
    plt.subplots()
    for username, data in datas.items():
        df = pd.Series(data)
        df.plot(label="%s (%.2f)" % (username, df.max()))
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
    # Credit to https://github.com/jacklee1792/dmoj-rating
    plt.clf()
    plt.subplots()
    df = pd.DataFrame(data)
    df = df.T
    max_ratings = df.iloc[1:].max()

    for i in range(len(df.columns)):
        username = data['users'][i]
        ddf = df.iloc[:, i].dropna()
        # Make sure there is data, to plot
        # Don't plot users with no contest score
        try:
            ddf.iloc[1:]\
                .plot(label=f'{username} ({max_ratings[i] or 0})',
                    marker='s', markerfacecolor='white')
        except TypeError:
            pass

    colors = ['#d2d2d3', '#a0ff8f', '#adb0ff', '#f399ff', '#ffd363',
              '#ff3729', '#a11b00']
    rng = [[0, 1000], [1001, 1200], [1201, 1500], [1501, 1800],
           [1801, 2200], [2201, 3000], [3001, 9999]]

    ma = df.iloc[1:].max().max()
    mi = df.iloc[1:].min().min()
    offset = 100

    for i in range(7):
        if mi - offset > rng[i][1]:
            continue
        elif ma + offset < rng[i][0]:
            break
        mi_range = max(mi - offset, rng[i][0])
        ma_range = min(ma + offset, rng[i][1])
        plt.axhspan(mi_range, ma_range, facecolor=colors[i])

    plt.gca().set_ylim([mi-offset, ma+offset])
    plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%m/%d/%Y'))
    plt.gcf().autofmt_xdate()
    plt.legend(loc="upper left", prop={"size": 8})
    plt.xlabel('Date')
    plt.ylabel('Rating')

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

    scale = maxval*1.1
    if as_percent:
        plt.yticks(
            [scale/4, scale/2, 3*scale/4],
            [
                "%.1f%%" % (scale/4),
                "%.1f%%" % (scale/2),
                "%.1f%%" % (3*scale/4)
            ],
            color="grey", size=7
        )
    else:
        plt.yticks(
            [scale/4, scale/2, 3*scale/4],
            [
                "%.1f" % (scale/4),
                "%.1f" % (scale/2),
                "%.1f" % (3*scale/4)
            ],
            color="grey", size=7
        )
    plt.ylim(0, maxval*1.1)

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
