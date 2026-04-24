import json

with open('c:/Bussiness/QR-Menu-Maker/QR-Menu-Maker-BE/docs/logs.1777024458244.json', 'r', encoding='utf-8') as f:
    logs = json.load(f)

for log in logs:
    print(log.get('message', ''))
