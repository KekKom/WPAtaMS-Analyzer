# Project DEADLINE: A Statistical Timeline and Prediction for WPAtaMS
---

Project DEADLINE is my attempt at statistical analysis of the webserial "Wearing Power Armor to a Magic School" written by JCB112 (or WPatMS for short).
I want to analyze both the amount of time that passed in the book and statistically estimate the chapter in which the so-called "Communication deadline" will happen.

## 0. Table of contents
<!-- TOC -->
  * [# Project DEADLINE: A Statistical Timeline and Prediction for WPAtaMS](#-project-deadline-a-statistical-timeline-and-prediction-for-wpatams)
  * [0. Table of contents](#0-table-of-contents)
  * [1. Introduction](#1-introduction)
  * [2. Methodology](#2-methodology)
    * [What is a timestamp?](#what-is-a-timestamp)
    * [How are timestamps stored?](#how-are-timestamps-stored)
    * [How does one detect a date change?](#how-does-one-detect-a-date-change)
  * [3. Results](#3-results)
    * [The table™](#the-table)
<!-- TOC -->


## 1. Introduction
WPAtaMS is a weekly webserial I quite enjoy, but as is with everything, it has some flaws.
The main one is the slow pace. When you start reading it, you notice that after 70 chapters (1.5 years of IRL time), only a week has passed.
One such person was [Unknown65](https://www.royalroad.com/profile/389704) on royal road, who started their analysis on [chapter 86](https://www.royalroad.com/fiction/70510/wearing-power-armor-to-a-magic-school/chapter/1699786/chapter-86-you-cannot-handle-my-potions).
The early deadline analyses also started there. Using a simple arithmetic proportion, I estimated the chapter within which the deadline should happen.

Little happened for a few weeks, but that changed when I really came into the fold.
I found some mistakes in Unknown65's estimation of the amount of time that passed. 
To be completely honest, I made some mistakes in my correction, but that motivated me to start this project.

I decided that, as humans make mistakes, the process of analysis had to be automated.
In retrospect, that also gave me more data to fit better models on.

Now, this version is one that I call "V4 Rewrite". I am doing this because the previous codebase was unreadable at this point. 
Sometimes, just **write it again** is the correct way of doing something.

## 2. Methodology
I know from experience that the timestamp extraction and deadline estimation are not that easy to understand from the Python code.
So I'll explain it as simply as possible.

### What is a timestamp?
In the book, sometimes a line similar to the one below is stated.

```Dragon’s Heart Tower, Level 23, Residence 30. Local Time: 0200.```

As one can see, a location and current time are given. In this project, this will be called a timestamp.
I ignore the location part and focus on the time.

Using a [regex](https://en.wikipedia.org/wiki/Regular_expression), I can identify all possible timestamps and extract the time.

If anyone is curious, the regex is ``

### How are timestamps stored?

Timestamps are stored in one of three formats:
1. **Minutes after midnight** (*MaM*). As the name suggests, the time is stored as the number of minutes after midnight on the given day.
2. **Absolute timestamp** (*AT*). This chapter puts time 0 (*called the epoch*) at midnight on the first day of the book.
3. **Time at the end of chapter** (*EoC*). This format only has one entry per chapter, being either the last timestamp of the chapter (in AT) or the previous chapter's EoC, if the current chapter does not have a timestamp

### How does one detect a date change?

You know how when a digital clock changes from 23:59 to 00:00, the MaM changes; this fact is used in this project to find date changes.

Unfortunetely 
## 3. Results

We are finally close to the end. 

### The table™
The table™ is a semi-manually table of when does each day start and end. I treat this as my ground truth.

| Day number | Day of week | Chapters |                                                                                                         Important events |
|:-----------|:-----------:|:--------:|-------------------------------------------------------------------------------------------------------------------------:|
| 1          |   Tuesday   |   1-12   |                                                                                                  arrival and orientation |
| 2          |  Wednesday  |  13-31   |                                                       it ends at the weapon inspection, has the null fight and library 1 |
| 3          |  Thursday   |  31-35   |      food 1, grapple, apprentice, and jumping into the portal (note 35 does end exactly at midnight, which matches ch41) |
| 4          |   Friday    |  35-41   |             portal shenanigans, bomb, etc (note ch41 has the whole, and is the only one that has timestamps for the day) |
| 5          |  Saturday   |  41-55   |                                                                     emma returns, letter, assembly, library 2, library 3 |
| 6          |   Sunday    |  56-67   |                      giving the letter to the Dean, showing the Realms through sight-seers, date night with Thacea in vr |
| 7          |   Monday    |  68-72   |                               Professor Vanavan's class (Magic Theory and Mana-field Studies), killing birds with Ilunor |
| 8          |   Tuesday   |  72-77   |             Professor Articord's class (Nexus and Adjacent Realm History and Politics), Assassination attempt at Thalmin |
| 9          |  Wednesday  |  78-84   |        Larial Essen's / Sorecar's class (Mana-Field Perception and Light-Magic Theory), Mixer, Names of the burned books |
| 10         |  Thursday   |  84-87   |                           Professor Belnor's class (Potions Theory, Potions Crafting, and Healing Magic), Dean Tea Party |
| 11         |   Friday    |  88-97   |                     Professor Chiska's class (PE), first library checkup, planing for the trip, post scarcity discussion |
| 12         |  Saturday   |  97-108  | Trip to Elaseer, Buying a magic wand, Searching for Rila, Buying pens/business-plan, Adventurer's Guild, Meeting Etholin |
| 13         |   Sunday    | 108-115  |                    House choosing ceremony, Talking to Rila, Explanation of Earth space exploration and the solar system |
| 14         |   Monday    | 116-118  |                                   Space warfare and Nexian cosmology conversation, Magic Theory and Mana-field Studies 2 |
| 15         |   Tuesday   | 119-119  |                                                   Nexus and Adjacent Realm History and Politics 2, meeting the Goldthorn |
| 16         |  Wednesday  | 119-122  |                               Manafield Perception and Light Magic Theory 2, dragon's location, electricity conversation |
| 17         |  Thursday   | 122-125  |       announcement of The Quest for the Everblooming Blossom, Ping issues a challenge, tasking Sorecar with the bodywork |
| 18         |   Friday    | 125-127  |                                                                                                        Ping v Emma fight |
| 19         |  Saturday   | 127-131  |      printing the motorcycle, preparing for the quest, representation of manastreams, Emma and Thalmin, Dean x Goldthorn |
| 20         |   Sunday    | 131-132  |                                   Ping plans to counter Emma, Thalmin's gold diggers, Taint conversation, buying a horse |
| 21         |   Monday    | 132-133  |                         Skipped Magic Theory and Mana-field Studies 3, getting the bodywork, Chiska teleport to the Dean |
| 22         |   Tuesday   |   133-   |                                             Start of The Quest for the Everblooming Dawn, aprentice "stealth", magic RTS |

