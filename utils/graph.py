import matplotlib.pyplot as plt
import pandas as pd
from math import pi
import numpy as np


def plot_bar(data, maxval):
    # Code from https://www.geeksforgeeks.org/bar-plot-in-matplotlib/
    plt.clf()
    df = pd.DataFrame(data)
    categories = ['DS', 'DP', 'GT', 'String', 'Math', 'Ad Hoc', 'Greedy']
    N = len(categories)
    usernames = data['group']
    index = np.arange(N)
    barwidth = 1/(len(usernames)+1)

    colours = ['b', 'g', 'r', 'c', 'm', 'y']
    for i in range(len(usernames)):
        values = df.loc[i].drop('group').values.flatten().tolist()
        br = [j + barwidth for j in index]
        plt.bar(index, values, color=colours[i], width=barwidth,
                edgecolor='grey', label=usernames[i])
        index = br
    plt.xlabel('Problem Types', fontweight='bold')
    plt.ylabel('Points', fontweight='bold')
    plt.xticks([r for r in range(N)], categories)
    plt.legend(loc='lower right', bbox_to_anchor=(0.95, 0.95),
               labelspacing=0.1, fontsize='small')
    plt.savefig('./graphs/plot.png')


def plot_radar(data, maxval):
    # Code from
    # https://python-graph-gallery.com/391-radar-chart-with-several-individuals/
    plt.clf()
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
    plt.yticks(
        [scale/4, scale/2, 3*scale/4],
        ["%.1f%%" % (scale/4), "%.1f%%" % (scale/2), "%.1f%%" % (3*scale/4)],
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
