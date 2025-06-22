import time
import urllib

import requests
import json
import sys
import re
import logging



# As reddit updates first, we'll use it, instead of RoyalRoad. Thanks to https://github.com/lizard-demon/hfydl for the inspiration
chapter_url = "https://www.reddit.com/r/HFY/comments/yd3cu3/wearing_power_armor_to_a_magic_school_1/.json"
HEADERS = {'User-Agent': 'WPAtaMS-Analyzer'}


def safe_request(url,headers) -> dict:
    """
    This function handles the request, and the rate limits

    :param url:
    :return dict:
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Requesting url {url}, with headers {headers}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Response gotten, content: {response.content[:100]}")
    except requests.exceptions.RequestException as e:
        logger.error(e)
        sys.exit(1)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        logger.error("404 Not Found, ")
        # A reparse of the last chapter (to get a different link) may be done, but this is not implemented for now
        sys.exit(1)
    elif response.status_code == 429 or response.status_code == 503:
        timeout = response.headers.get('Retry-After') if response.headers.get('Retry-After') is not None else 30 # reddit may not give this
        logger.warning(f"Retrying after {timeout} seconds")
        time.sleep(int(timeout))
        return safe_request(url, headers)
    else:
        logger.error("Request failed with status code: " + str(response.status_code))
        sys.exit(1)


# we want to recurse into the text. so I want to return a new

def extract(url:str, headers:dict[str,str], book=None)->list:
    """
    This function recurses into the book and extracts all the chapters
    :str url: Url of the starting chapter
    :dict headers: Headers of the request
    :param book: This should be left empty and the return should be used
    :return: The contents of the chapters
    """
    if book is None:
        book = []
    response = safe_request(url, headers)
    lines = response[0]['data']['children'][0]['data']['selftext'].split('\n')
    logging.info(f"Extracted {len(lines)} paragraphs")
    book.append(lines)
    for line in lines:
        if line.find('[Next](') != -1:
            logging.info(f"Found the link to the next chapter")
            index  = line.find('[Next](')
            next_link = line[index + 7:-1]+'.json'
            print(next_link)
            return extract(next_link, headers,book)
    else:
        return book


def load_book(path: str="chapters.json")->list:
    try:
        with open(path) as f:
            logging.info(f"Reading {path}")
            return json.loads(f.read())
    except FileNotFoundError:
        logging.warning(f"File {path} not found, creating a new one")
        # If it does not exist, Download anyway and save it for later
        return extract(chapter_url, HEADERS)

def clean(book:list[list[str]]) -> list:

    cleaned_book = []
    for idx,chapter in enumerate(book):
        logging.info(f"Cleaning chapter: {idx}")
        cleaned_chapter = [line for line in chapter if line.strip()!='']
        cleaned_book.append(cleaned_chapter)


    return cleaned_book

def timstampify(book:list[list[str]], start_time=1530):


    timestamps = [[start_time]]


    regex = re.compile(r'(?i)(?=.*\b(?:TIME:|HOURS)\b).*?((?:[01]\d|2[0-3]):?[0-5]\d)')

    logging.info("Compiled the regex")
    for idx, chapter in enumerate(book):
        logging.info(f"Analyzing chapter: {idx}")
        timestamps.append(timestamps_from_chapter(chapter, regex))


    return timestamps,0


def timestamps_from_chapter(chapter, regex):
    ch_timestamps = []
    for idx,line in enumerate(chapter):
        match = regex.search(line)
        if not match:
            # logging.info(f"No timestamps found in line {idx}")
            continue
        logging.info(f"Matched {idx}: {match.group(1)}")
        ch_timestamps.append(convert_to_MaM(match.group(1)))

    return ch_timestamps

def convert_to_MaM(timestamp):
    timestamp = timestamp.replace(':','')
    hours = int(timestamp[:2])
    minutes = int(timestamp[2:])

    return (60*hours)+minutes

def main(skip_chapter_download:bool=False):
    logger = logging.getLogger(__name__)


    if skip_chapter_download:
        logger.info(f"Skipping chapter download")
        book = load_book()
    else:
        logger.info(f"Starting download, starting link is {chapter_url}")
        book = extract(chapter_url, HEADERS)


    book = clean(book)
    AT,EoC = timstampify(book)
    print(AT)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main(skip_chapter_download=True)