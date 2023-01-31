#!/usr/bin/env python
import json
with open('csvjson.json') as f:
    # load json objects to dictionaries
    jsons = map(json.loads, f)

result = list()
items_set = set()

for js in jsons:
    
    
    # only add unseen items (referring to 'title' as key)
    if not js['title'] in items_set:
        # mark as seen
        items_set.add(js['title'])
        # add to results
        result.append(js)

# write to new json file
with open('new_file.json' ,'w') as nf:
    json.dump(result, nf)

print(result)