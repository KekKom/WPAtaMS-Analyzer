redditChapterText = """
"""

import ebooklib
from ebooklib import epub
import os

bookFile = epub.read_epub("./WPAtaMS.epub")

book1 = []

for chapter in bookFile.get_items_of_type(ebooklib.ITEM_DOCUMENT):
    byteChapter = chapter.get_body_content()
    strChapter = str(byteChapter,'UTF-8')
    book1.append(strChapter.split('\n'))

#chapter 0 and the last one are the ToC and the cover image respecly, let's detete them
book1.pop(0)
book1.pop(-1)

# The book starts at 1530 but that chapter does not have a timestamp, so we are going to add it
book1[0].append("This is manually added TIME: 1530")

book1.append(redditChapterText.split('\n'))

with open("res.csv","w") as f:
    for i in range(2,len(book1)):
        book = book1[:i]
        import re

        def toMinutes(timestamp)->int:
            hours = int(timestamp[:2])
            minutes = int(timestamp[2:])
            return (60*hours)+minutes


        timestamps = [] # this is an array of timestamps in the "minutes after midnight" format

        for chapter in book:
            chTimestamps = []
            for line in chapter:
                if re.search(r'([01][0-9]|2[0-3])[0-5][0-9]|([01][0-9]|2[0-3]):[0-5][0-9]',line) is not None:
                    if line.upper().find("TIME:") != -1 or line.upper().find("HOURS") != -1:
                        timestamp = re.search(r'([01][0-9]|2[0-3])[0-5][0-9]|([01][0-9]|2[0-3]):[0-5][0-9]',line)
                        timestamp = timestamp.group().replace(':','')
                        chTimestamps.append(toMinutes(timestamp))
            timestamps.append(chTimestamps)


        from matplotlib import pyplot as plt
        from matplotlib import ticker as ticker
        from random import random

        fig = plt.figure(figsize=(19.2,10.8))
        ax = fig.add_subplot(111)

        fig = plt.gcf()
        size = fig.get_size_inches()*fig.dpi

        unit = size[1].item()/len(timestamps)
        halfUnit = unit/2

        datechanges = []

        previousTimestamp = 24*60
        previousPosition = unit


        for chapterNumber,chapter in enumerate(timestamps):

            xStart = unit*chapterNumber
            xEnd = xStart+unit
            color = (random(),random(),random())

            if len(chapter) == 0:
                # print(chapterNumber)
                plt.scatter(xStart+halfUnit,-20,marker='x',color='red')
            elif len(chapter) == 1:
                plt.scatter(xStart+halfUnit,chapter[0],color=color)
            else:
                interUnit = unit/len(chapter)
                for timestampNumer,timestamp in enumerate(chapter):
                    plt.scatter(xStart+(interUnit*timestampNumer),timestamp,color=color)

                    # Line between timestamps in a chapter with more than 1 tmestamp
                    # Well first if last chapter, do not draw a line
                    if timestampNumer+1 != len(chapter):
                        xPoses = [xStart+(interUnit*timestampNumer),xStart+(interUnit*(timestampNumer+1))]
                        yPoses = [timestamp,chapter[timestampNumer+1]]
                        plt.plot(xPoses, yPoses, c=(0,0,1,0.5))
                    
        for chapterNumber,chapter in enumerate(timestamps):
            xStart = unit*chapterNumber
            xEnd = xStart+unit
            plt.axvline(xStart,color=(0.7,0.7,0.7,0.5))


        for chapterNumber,chapter in enumerate(timestamps):
            xStart = unit*chapterNumber
            xEnd = xStart+unit

            # Because if the chapter does not chnage the time, it won't change the date
            if len(chapter) == 0:
                continue
            
            interUnit = unit/len(chapter)

            for timestampNumer,timestamp in enumerate(chapter):
                if previousTimestamp - timestamp > 120 and previousPosition != 0:
                    datechanges.append((chapterNumber+1,previousPosition))
                previousTimestamp = timestamp
                previousPosition = xStart + (interUnit * timestampNumer)


        for datechange in datechanges:
            plt.axvline(datechange[1],color=(0.7,0.3,0.3,0.5))
            pass


        def minutes_to_hhmm(x,pos=0):
            hours = int(x // 60)
            minutes = int(x % 60)
            return f'{hours:02d}:{minutes:02d}'

        ax.yaxis.set_major_formatter(ticker.FuncFormatter(minutes_to_hhmm))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(60))

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'Chapter {int(x/unit)+1}'))
        ax.xaxis.set_major_locator(ticker.MultipleLocator(unit*10))



        fullDays = len(datechanges)-1 #it just works out this way, don't ask

        firstDayOfset = 24*60 - timestamps[0][0] # this works out to 8 and a half hours

        lastDayOfset = previousTimestamp # this is a bit harder, we do not know if the last chapter has a time .... but prevTimestamp has it, also conviniently this is in *"minutes after midnight"*

        totalMinutesInBook = firstDayOfset+lastDayOfset+(fullDays*24*60)

        # to check i asked wolframAlpha "15280 minutes = 10 days + 8.5 hours + 6 hours + 10 minutes" and it came out as "true"

        decimalHoursInBook = totalMinutesInBook/60 # this is decimal hours
        decimalDaysInBook = decimalHoursInBook/24 # this is decimal days

        decimalDaysInBook,decimalHoursInBook,totalMinutesInBook

        daysInBook = decimalDaysInBook // 1
        hoursInBook = (decimalHoursInBook - 24*daysInBook) // 1
        minutesInBook = totalMinutesInBook - 60*24*daysInBook - 60*hoursInBook

        currentTime = f"Day {daysInBook:.0f}, {hoursInBook:.0f}:{minutesInBook:.0f}"


        # Assuming 35 days translates to a specific number of minutes:
        day35Beginning = ((len(timestamps) + 1) * (35 * 24 * 60)) / totalMinutesInBook
        day35T1530 = ((len(timestamps) + 1) * (((35 * 24 * 60) + (15 * 60) + 30))) / totalMinutesInBook  # 35 days + 15:30 (in minutes)
        day35End = ((len(timestamps) + 1) * (((35 * 24 * 60) + (23 * 60) + 59))) / totalMinutesInBook  # End of 35th day (23:59)

        f.write(f"{len(timestamps)+1},{day35Beginning},{day35End},{day35T1530}\n")
        print(f"{len(timestamps)+1},{day35Beginning},{day35End},{day35T1530}")


