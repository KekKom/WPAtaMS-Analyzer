import csv
import logging
import re


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

    with open(path, newline='') as csvfile:
        raw_exceptions = csv.reader(csvfile, delimiter=',', quotechar='#')

        for row in raw_exceptions:
            key = (int(row[0]), int(row[1]))
            exceptions[key] = int(row[2])

    return exceptions

def convert_to_MaM(timestamp):
    timestamp = timestamp.replace(':', '')
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

def timstampify(book: list[list[str]], start_time=930, exceptions_path: str="exceptions.csv"):
    MaM: list[list[int]] = [[start_time]]
    AT:  list[list[int]] = [[start_time]]
    # I want three different lists, not references

    EoC: list[int] = [start_time] # This is a flat list of one index per chapter

    book = book[1:] if book else []

    exceptions = load_exceptions(exceptions_path)

    regex = re.compile(r'\btime\s*:\s*((?:[01]\d|2[0-3]):?[0-5]\d)',
                       re.IGNORECASE)  # "time: hh:mm" (with the ':' being optional)

    logging.info("Compiled the regex")
    for idx, chapter in enumerate(book):
        logging.info(f"Analyzing chapter: {idx}")
        from_chapter = timestamps_from_chapter(chapter, regex)
        MaM.extend(from_chapter)

    day          = 0
    previous_MaM = MaM[0][0]
    previous_AT  = AT[0][0]

    for c_idx, chapter in enumerate(MaM[1:], start=1):
        # Chapter 1 is manually analyzed, skipping it

        # OK, as there are exceptions, we have more possibilities

        # Technically, an exception could be added for a timestampless chapter
        if len(chapter) == 0:
            if exceptions[(c_idx,0)] is None:
                EoC.append(EoC[c_idx-1]) # use last chapter's EoC
                continue
            else:
                # If there is a date change
                # TODO: Implement this, left empty for now, needs more of the structure
                pass

        for jdx, timestamp in enumerate(chapter):
            day = timestamp // 1440
            if timestamp < previous_timestamp:
                pass

    return MaM, AT, EoC






def convert_to_DDHHMM(timestamp:int):
    days = timestamp // (24*60)
    hours = timestamp % (24*60)
    return (days, hours)
