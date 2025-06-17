# Project DEADLINE: A Statistical Timeline and Prediction for WPAtaMS
---

Project DEADLINE is my attempt at statistical analysis of the webserial "Wearing Power Armor to a Magic School" written by JCB112 (or WPatMS for short).
I want to analyze both the amount of time that passed in the book. The other goal is to statically estimate the chapter
in which the so-called "Communication deadline" will happen.

## 1. Introduction
WPAtaMS is a weekly webserial I quite enjoy, but as it is with everything it has some flaws.
The main one is its slowness. When you start reading it, you notice that after 70 chapters (1.5 years of IRL time) only a week has passed.
One such person was [Unknown65](https://www.royalroad.com/profile/389704) on royal road, who started their analysis on [chapter 86](https://www.royalroad.com/fiction/70510/wearing-power-armor-to-a-magic-school/chapter/1699786/chapter-86-you-cannot-handle-my-potions).
The early deadline analyses also started there. Using a simple arithmetic proportion I estimated the chapter that the deadline should happen.

Not much happened for a few weeks, but that changed when I really came into the fold.
I found some mistakes in Unknown65's estimation of the amount of time that passed. 
To be completely honest, I made some mistakes in my correction, but that motivated me to start this project.

I decided that, as humans make mistakes, the process of analysis had to be automated.
In retrospect that also gave me more data to fit better models on.

Now, this version is one that I call "V4 Rewrite". I am doing this because the previous codebase was unreadable at this point. 
Sometimes just **write it again** is the correct way of doing something.

## 2. Methodology
I know from experience that the timestamp extraction and deadline estimation are not that easy to understand from the python,
so I'll explain it as simply as possible.

### What is a timestamp?
In the book sometimes a line similar to this is stated

```Dragon’s Heart Tower, Level 23, Residence 30. Local Time: 0200.```

As one can see, a location and current time are given. In this project this will be called a timestamp.
I ignore the location part, and focus on the time.

Using a [regex](https://en.wikipedia.org/wiki/Regular_expression) I can identify all possible timestamps, and extract the time.

If anyone is curious the regex is ``

### How are timestamps stored?

Timestamps are stored in on of three formats:
1. **Minutes after midnight** (*MaM*). As the name suggests, the time is stored as the number of minutes after midnight on the given day.
2. **Absolute timestamp** (*AT*). This chapter puts time 0 (*called the epoch*) at midnight on the first day of the book.
3. **Time at the end of chapter** (*EoC*). This format only has one entry per chapter, being either the last timestamp of the chapter (in AT) or the previous chapter's EoC, if the current does not have a timestamp

### How does one detect a date change?

You know how when a digital clock changes from 23:59 to 00:00 the MaM changes, this fact is used in this project to find date changes.

Unfortunetely 
