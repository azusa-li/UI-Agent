import json

user_name = 'cceatmore'

with open(f'query_results3/{user_name}.json', 'r') as f:
    data = json.load(f)

print(len(data))

for index,d in enumerate(data):
    if index == 0:
        print(d['title'])
        step_str = d['steps']
        step_list = json.loads(step_str)
        print(json.dumps(step_list, ensure_ascii=False))
        break