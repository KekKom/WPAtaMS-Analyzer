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
    elif response.status_code == 429:
        timeout = response.headers.get('Retry-After') if response.headers.get('Retry-After') is not None else 30 # reddit may not give this
        logger.warning(f"Retrying after {timeout} seconds")
        time.sleep(int(timeout))
        return safe_request(url, headers)
    else:
        logger.error("Request failed with status code: " + str(response.status_code))
        sys.exit(1)


# we want to recurse into the text. so I want to return a new

def extract(url, headers, book):
    response = safe_request(url, headers)
    lines = response[0]['data']['children'][0]['data']['selftext'].split('\n')
    logging.info(f"Extracted {len(lines)} paragraphs")
    book.append(lines)
    for line in lines:
        if line.find('[Next](') != -1:
            index  = line.find('[Next](')
            next_link = line[index + 7:-1]+'.json'
            print(next_link)
            return extract(next_link, headers,book)
    else: return None




def main():
    logger = logging.getLogger(__name__)

    logger.info(f"Starting download, starting link is {chapter_url}")
    book = []

    a = extract(chapter_url, HEADERS, book)
    print(book)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()