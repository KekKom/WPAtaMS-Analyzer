import os

import time

import requests
import json
import sys
import re
import logging

from timestampify import timstampify

# As reddit updates first, we'll use it, instead of RoyalRoad. Thanks to https://github.com/lizard-demon/hfydl for the inspiration
chapter_url = "https://www.reddit.com/r/HFY/comments/yd3cu3/wearing_power_armor_to_a_magic_school_1/.json"
HEADERS = {'User-Agent': 'WPAtaMS-Analyzer'}


def safe_request(url, headers) -> dict:
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
        timeout = response.headers.get('Retry-After') if response.headers.get(
            'Retry-After') is not None else 30  # reddit may not give this
        logger.warning(
            f"Retrying after {timeout} seconds, due to {resonse.status_code}")  # This is not an error as we sys.exit(1) on error
        time.sleep(int(timeout))
        return safe_request(url, headers)
    else:
        logger.error("Request failed with status code: " + str(response.status_code))
        sys.exit(1)


# we want to recurse into the text. so I want to return a new

def extract(url: str, headers: dict[str, str], book=None) -> list:
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
            index = line.find('[Next](')
            next_link = line[index + 7:-1] + '.json'
            print(next_link)
            return extract(next_link, headers, book)
    else:
        return book


def load_book(path: str = "chapters.json") -> list:
    try:
        with open(path) as f:
            logging.info(f"Reading {path}")
            try:
                book = json.loads(f.read())
                logging.info(f"Loaded {len(book)} chapters")
                return book
            except json.decoder.JSONDecodeError:
                logging.error("Error reading json, removing the file and trying again")

                os.remove(path)
                logging.info(f"Removed {path}")
                return write_book(path)



    except FileNotFoundError:
        logging.warning(f"File {path} not found, creating a new one")
        # If it does not exist, Download anyway and save it for later
        return write_book(path)


def write_book(path):
    book = extract(chapter_url, HEADERS)
    logging.info(f"Writing {path}")
    with open(path, 'w') as f:
        f.write(json.dumps(book))
    return book


def clean(book: list[list[str]]) -> list[list[str]]:
    """
    Cleans a book organized as a list of chapters, where each chapter is a list of paragraphs.

    This function performs the following actions on each chapter:
    1. Removes the author's note and any content that comes after it.
    2. Removes any Markdown-style links.
    3. Removes any empty or whitespace-only paragraphs.

    Notes:
        This is by Gemini, it is somewhat how i would make it, just a tiny bit better

    Args:
        book: A list where each item is a chapter, and each chapter is a list of strings (paragraphs).

    Returns:
        A cleaned list of chapters, formatted in the same way as the input.
    """
    # This regex correctly identifies all variations of "Author's Note" found in your text.
    author_note_regex = re.compile(r"\((Author(['’])s Note)( \d+)?:", re.IGNORECASE)

    # This regex finds and will be used to remove Markdown-style links like [text](url)
    link_regex = re.compile(r'\[.*?\]\(https?://.*?\)')

    fully_cleaned_book = []

    # Iterate through each chapter in the book
    for idx, chapter in enumerate(book):
        logging.info(f"Cleaning chapter: {idx + 1}")

        # --- Step 1: Find the author's note and truncate the chapter ---

        note_index = -1
        # Search backwards from the end of the chapter for efficiency
        for i in range(len(chapter) - 1, -1, -1):
            if author_note_regex.search(chapter[i]):
                logging.info(f"Found author note: {i + 1}")
                note_index = i
                break  # Found the note, no need to search further back

        # Slice the chapter to get only the paragraphs before the note
        if note_index != -1:
            # Correct slice keeps everything UP TO the note paragraph
            content_paragraphs = chapter[:note_index]
            logging.info(f"Slicing to [:{note_index}], giving {len(content_paragraphs)} paragraphs")
        else:
            # If no note was found, process the whole chapter
            content_paragraphs = chapter
            logging.info("No author note found")

        logging.info(f"Starting step two for chapter {idx + 1}")
        # --- Step 2: Clean the remaining paragraphs ---
        # Use a list comprehension to remove links and filter out empty lines in one pass.
        # .sub() removes the links, and `if paragraph.strip()` removes empty/whitespace lines.
        cleaned_chapter = [link_regex.sub('', paragraph).strip() for paragraph in content_paragraphs if
                           paragraph.strip()]
        logging.info(f"Cleaned chapter: {len(cleaned_chapter)}")

        fully_cleaned_book.append(cleaned_chapter)

    return fully_cleaned_book


def main(skip_chapter_download: bool = False):
    logger = logging.getLogger(__name__)

    if skip_chapter_download:
        logger.info(f"Skipping chapter download")
        book = load_book()
    else:
        logger.info(f"Starting download, starting link is {chapter_url}")
        book = extract(chapter_url, HEADERS)

    book = clean(book)
    MaM, AT, EoC = timstampify(book)
    # print(AT)

    from matplotlib import pyplot as plt
    # a = [x for xs in AT for x in xs]
    a = [x//1440 for x in EoC]
    # a = EoC
    # print(a)
    print(a)
    plt.scatter(range(len(a)), a)
    plt.ylim(24 * 60)
    plt.ylim(len(a))
    plt.show()


    # print(EoC[-1]//1440)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.ERROR)
    main(skip_chapter_download=True)
