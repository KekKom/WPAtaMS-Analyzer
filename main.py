import time

import requests
import json
import sys

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"Countdown: {i} seconds remaining", end='\r')
        time.sleep(1)
    print("Time's up!                         ")

# As reddit updates first, we'll use it, instead of RoyalRoad. Thanks
chapter_url = "https://www.reddit.com/r/HFY/comments/yd3cu3/wearing_power_armor_to_a_magic_school_1/.json"
next_found = True
HEADERS = {'User-Agent': 'WPAtaMS-Analyzer2'}

f = open("aaaa.txt","w")

while next_found is True:
    print(f"[DEBUG] Fetching URL: {chapter_url}", file=sys.stdout)

    response = requests.get(chapter_url+".json", headers=HEADERS, timeout=10)
    print(f"[DEBUG] Response: {response}", file=sys.stdout)
    if response.status_code != 200:
        #as nothing changed this should work
        countdown(60)
        continue
    response = response.text
    print(f"[DEBUG] First 100 characters: {response[:100]}", file=sys.stdout)
    response = json.loads(response)
    print("[DEBUG] JSON loaded")
    print(f"[DEBUG] Response received", file=sys.stdout)
    text = response[0]['data']['children'][0]['data']['selftext']
    print(f"[DEBUG] Text length: {len(text)} characters", file=sys.stdout)
    lines : list[str]= text.split('\n')

    for idx,line in enumerate(lines):
        if line.find('[Next](')!=-1:
            print(f"[DEBUG] Found 'Next' in line {idx}: {line}", file=sys.stdout)
            if idx == 0:
                print(f"[DEBUG] 'Next' link is first line, removing and continuing", file=sys.stdout)
                lines.pop(idx)
                continue
            else:
                next_found = True
                index = line.find('[Next](')
                next_link = line[index + 7:-1]
                print(f"[DEBUG] Next chapter URL: {next_link}", file=sys.stdout)
                chapter_url = next_link
                f.writelines(lines[:idx])
                f.write('\n')
                break
    else:
        print("[DEBUG] No 'Next' link found. Ending download.", file=sys.stdout)
        next_found = False

    time.sleep(1)
f.close()