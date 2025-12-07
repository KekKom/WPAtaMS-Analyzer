import numpy as np
from matplotlib import pyplot as plt
from matplotlib import ticker



def plot_multiple(chapter, idx):

    unit = 1/(len(chapter)+1) # the +1 is to create a bit of space at the beginning

    for jdx,timestamp in enumerate(chapter):
        plt.scatter(idx+(jdx+1)*unit,timestamp)
    return

def minutesToHhmm(x, pos=0):
    days,_ = divmod(x, 1440)
    hours, minutes = divmod(int(x), 60)
    return f'Day {int(days)} {hours:02d}:{minutes:02d}'


def plot_chapter_markers(amount,ax):
    for idx in range(1,amount):
        plt.axvline(idx,c='gray',alpha=0.2)

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: int(x)))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(5, 0.5))


def plt_hour_markers(skip,subplot,max):
    for marker in range(0,max,skip*60):
        plt.axhline(marker,c='gray',alpha=0.2)

    # arcane magic below

    subplot.yaxis.set_major_formatter(ticker.FuncFormatter(minutesToHhmm))
    subplot.yaxis.set_major_locator(ticker.MultipleLocator(60*12))

    return




def plot(MaM, AT, EoC,*args,**kwargs):

    size = (19.2, 10.8)
    fig = plt.figure(figsize=size)
    ax = fig.add_subplot(1,1,1)

    x = np.linspace(0,len(MaM)+10,1_000).reshape(-1,1)




    for idx, chapter in enumerate(AT):
        # Now for the three possibilities
        if len(chapter) == 0:
            # draw a red x at -100
            plt.scatter(idx+0.5,6*60, marker='x',c='red')
        elif len(chapter) == 1:
            plt.scatter(idx+0.5,chapter[0])
        else:
            plot_multiple(chapter,idx)




    plot_chapter_markers(len(MaM)+10,ax)
    # noinspection PyTypeChecker
    plt_hour_markers(12, ax, max(EoC)+60+1440)  # pycharm is wrong, it has that

    plt.xlim(0,len(MaM)+10)
    plt.ylim(-20,max(EoC)+60+1440)
    plt.tight_layout()
    plt.legend()
    plt.show()
    return


