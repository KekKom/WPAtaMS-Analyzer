import numpy as np
from matplotlib import pyplot as plt
from matplotlib import ticker




def plot_multiple(chapter, idx):

    unit = 1/(len(chapter)+1) # the +1 is to create a bit of space at the beginning

    for jdx,timestamp in enumerate(chapter):
        plt.scatter(idx+(jdx+1)*unit,timestamp)
    return

def minutesToHhmm(x, pos=0):
    hours, minutes = divmod(int(x), 60)
    return f'{hours:02d}:{minutes:02d}'


def plot_chapter_markers(amount):
    for idx in range(1,amount):
        plt.axvline(idx,c='gray',alpha=0.2)


def plt_hour_markers(skip,subplot):
    for marker in range(0,1440,skip*60):
        plt.axhline(marker,c='gray',alpha=0.2)

    # arcane magic below

    subplot.yaxis.set_major_formatter(ticker.FuncFormatter(minutesToHhmm))
    subplot.yaxis.set_major_locator(ticker.MultipleLocator(60))

    return


def plot(MaM,*args,**kwargs):


    size = (19.2, 10.8)
    fig = plt.figure(figsize=size)
    ax = fig.add_subplot(1,1,1)


    plot_chapter_markers(len(MaM))
    # noinspection PyTypeChecker
    plt_hour_markers(2,ax) # pycharm is wrong, it has that

    for idx, chapter in enumerate(MaM):
        # Now for the three possibilities
        if len(chapter) == 0:
            # draw a red x at -100
            plt.scatter(idx+0.5,0, marker='x',c='red')
        elif len(chapter) == 1:
            plt.scatter(idx+0.5,chapter[0])
        else:
            plot_multiple(chapter,idx)



    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x,pos:int(x)))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1,0.5))

    plt.xlim(0,len(MaM))
    plt.ylim(-20,1460)
    plt.tight_layout()
    plt.show()
    return