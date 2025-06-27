import logging
import re


def timstampify(book: list[list[str]], start_time=930):
    MaM: list[list[int]] = [[start_time]]
    AT: list[list[int]] = [[start_time]]
    # I want three different ~~arrays~~ lists not references

    EoC: list[int] = [start_time] # This is a flat list of one index per chapter

    book.pop(0) # as we are adding that chapter above


    regex = re.compile(r'\btime\s*:\s*((?:[01]\d|2[0-3]):?[0-5]\d)',
                       re.IGNORECASE)  # basically just "time: hh:mm" (with : being optional), obviously

    logging.info("Compiled the regex")
    for idx, chapter in enumerate(book):
        logging.info(f"Analyzing chapter: {idx}")
        MaM.append(timestamps_from_chapter(chapter, regex))

    previous_timestamp = MaM[0][0]
    timestamp_AT = previous_timestamp
    for idx, chapter in enumerate(MaM):
        # The first one is done so we skip it, as by our definitions the epoch for all of them is 00:00 on arrival day
        if idx == 0:
            continue

        # There are exactly three possibilities
        # One the current chapter has no timestamps, in that case update EoC with the idx-1's last timestamp (in AT)

        if len(chapter) == 0:

            EoC.append(EoC[idx-1])


        # If there is a timestamp, we need to check if a date change happened, BUT that may happen inside a chapter or between them
        chapter_AT: list[int] = []
        for timestamp in chapter:
            # As a list of length 1 will still work
            # timestamp is in MaM, so we are comparing it to previous_timestamp (also MaM)
            day = (timestamp_AT // (24*60))
            if timestamp < previous_timestamp: # This fails at a 24 or more hour times skip
                day = day + 1
            timestamp_AT = (day * 24 * 60) + timestamp
            chapter_AT.append(timestamp_AT)
            previous_timestamp = timestamp

        AT.append(chapter_AT)

        if len(chapter) > 0:
            EoC.append(AT[idx][-1])

    return MaM, AT, EoC


def timestamps_from_chapter(chapter, regex):
    ch_timestamps = []
    for idx, line in enumerate(chapter):
        match = regex.search(line)
        if not match:
            # logging.info(f"No timestamps found in line {idx}")
            continue
        logging.info(f"Matched {idx}: {match.group(1)}")
        ch_timestamps.append(convert_to_MaM(match.group(1)))

    return ch_timestamps


def convert_to_MaM(timestamp):
    timestamp = timestamp.replace(':', '')
    hours = int(timestamp[:2])
    minutes = int(timestamp[2:])

    return (60 * hours) + minutes


def convert_to_DDHHMM(timestamp:int):
    days = timestamp // (24*60)
    hours = timestamp % (24*60)
    return (days, hours)
