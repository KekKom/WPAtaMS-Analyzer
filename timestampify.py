import csv
import logging
import os
import re

import pandas as pd


def load_exceptions(path: str) -> dict[tuple[int, int], int]:
    """
    Loads date correction exceptions from a CSV file.

    The CSV file must contain rows with the following format:
        chapter_number (int), timestamp_index (int), date_change (int)

    - `chapter_number`: The chapter number in the source material.
    - `timestamp_index`: The index of a specific timestamp within that chapter, 0 for .
    - `date_change`:
        - A positive integer indicates the number of days that have passed.
        - A zero or negative value means the date change in a chapter should be ignored.

    Args:
        path (str): Path to the CSV file.

    Returns:
        dict[tuple[int, int], int]: A mapping from (chapter_number, timestamp_index)
        to the date correction value.
    """
    exceptions = {}
    
    if not os.path.isfile(path):
        logging.error('File "%s" does not exist. Running with no exceptions', path)
        return exceptions

    raw_exceptions = pd.read_csv(path,comment='#',header=None).to_dict()



    try:
        df = pd.read_csv(path, comment="#", header=None)
        for _, row in df.iterrows():
            key = (int(row[0]), int(row[1]))
            exceptions[key] = int(row[2])
    except Exception as e:
        logging.error("Failed to load exceptions from '%s': %s", path, e)

    return exceptions


def convert_to_MaM(timestamp):
    timestamp = timestamp.replace(':', '')
    timestamp = timestamp.zfill(4)
    hours = int(timestamp[:2])
    minutes = int(timestamp[2:])

    return (60 * hours) + minutes


def timestamps_from_chapter(chapter, regex):
    ch_timestamps = []
    for idx, line in enumerate(chapter):
        match = regex.search(line)
        if not match:
            logging.debug(f"No timestamps found in line {idx}")
            continue
        logging.info(f"Matched {idx}: {match.group(1)}")
        ch_timestamps.append(convert_to_MaM(match.group(1)))
    return ch_timestamps


def timstampify(book: list[list[str]], start_time=930, exceptions_path: str = "exceptions.csv"):
    MaM: list[list[int]] = [[start_time]]
    AT: list[list[int]] = [[start_time]]
    # I want three different lists, not references

    EoC: list[int] = [start_time]  # This is a flat list of one index per chapter

    book = book[1:] if book else []

    exceptions = load_exceptions(exceptions_path)

    regex = re.compile(r'\btime\s*:*\s*((?:[01]\d|2[0-3]):?[0-5]\d)',
                       re.IGNORECASE)  # "time: hh:mm" (with the ':' being optional)

    logging.info("Compiled the regex")
    for idx, chapter in enumerate(book):
        if idx > 145:
            pass
        logging.info(f"Analyzing chapter: {idx}")
        from_chapter = timestamps_from_chapter(chapter, regex)
        MaM.append(from_chapter)

    day = 0
    previous_MaM = MaM[0][0]
    previous_AT = AT[0][0]

    for c_idx, chapter in enumerate(MaM):
        # Chapter 1 is manually analyzed, skipping it
        if c_idx == 0:
            continue

        # OK, as there are exceptions, we have more possibilities

        # Technically, an exception could be added for a timestampless chapter
        if len(chapter) == 0:
            day_jump = handle_exceptions(c_idx, 0, exceptions, previous_MaM)
            day += day_jump

            previous_AT  += day_jump * 1_440

            AT.append([])
            EoC.append(previous_AT)
            continue

        chapter_AT = []
        for ts_idx, timestamp in enumerate(chapter):

            day += handle_exceptions(c_idx, ts_idx, exceptions, previous_MaM, timestamp)

            previous_MaM = timestamp
            previous_AT  = timestamp + (day * 1_440)
            chapter_AT.append(previous_AT)

        AT.append(chapter_AT)
        EoC.append(previous_AT)

        # if (day+1) != day_chapters[c_idx]:
        #     pass



    return MaM, AT, EoC


def handle_exceptions(c_idx, ts_idx, exceptions, previous_MaM, timestamp=9000):
    exception = exceptions.get((c_idx, ts_idx), None)
    if exception is not None:
        days_jump = max(exception, 0)
    elif timestamp < previous_MaM:
        days_jump = 1
    else:
        days_jump = 0
    return days_jump


def convert_to_DDHHMM(timestamp: int):
    # 3084 minutes

    days, remainder = divmod(timestamp, 1440)
    hours, minutes = divmod(remainder, 60)

    return f"{days:02d}:{hours:02d}:{minutes:02d}"
