# For now code structure is secondary, i need to try some infrastructure in the downloading

import requests
import json

# As reddit updates first, we'll use it, instead of RoyalRoad. Thanks
chapter_url = "https://www.reddit.com/r/HFY/comments/yd3cu3/wearing_power_armor_to_a_magic_school_1/.json"
next_found = True
HEADERS = {'User-Agent': 'WPAtaMS-Analyzer'}

f = open("aaaa.txt","w")

while next_found is True:
    response = json.loads(requests.get(chapter_url+".json", headers=HEADERS, timeout=10).text)
    text = response[0]['data']['children'][0]['data']['selftext']
    lines : list[str]= text.split('\n')

    for idx,line in enumerate(lines):
        if line.find('[Next](')!=-1:
            # print(line, idx)
            if idx == 0:
                lines.pop(idx)
                continue
            else:
                next_found = True

                index = line.find('[Next](')

                print(line[index + 7:-1])
                chapter_url = line[index+7:-1]
                f.writelines(lines[:idx])
                f.write('\n')
                break
    else:
        next_found = False


f.close()

