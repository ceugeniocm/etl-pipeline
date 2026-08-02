import json

with open('config.json', 'r') as f:
    config = json.load(f)

with open('full_mapping.json', 'r') as f:
    new_mapping = json.load(f)

config['mapping']['columns'] = new_mapping['columns']
config['mapping']['types'] = new_mapping['types']

# Optionally add more required fields if we want to be strict, 
# but for now let's just do what was asked: "add all the columns for mapping"

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
