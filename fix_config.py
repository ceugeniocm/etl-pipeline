import json

with open('config.json', 'r') as f:
    config = json.load(f)

config['validation']['required'] = []
config['validation']['rejection_threshold'] = "100%"

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
