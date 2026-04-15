import re
import codecs

path = r'C:\Users\ASUS\.gemini\antigravity\brain\f495097d-4eac-47b2-b438-03a5efad0b07\.system_generated\logs\overview.txt'
with codecs.open(path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# For survey
matches = re.finditer(r'1: {% extends "page\.html" %}.*?82:\s', text, re.DOTALL)
m = list(matches)
if m:
    content = m[-1].group(0)
    lines = content.split('\n')
    cleaned = [re.sub(r'^\d+: ', '', line) for line in lines]
    out_path = r'd:\ProyekBengkuluSatuData\ckan-docker\src\ckanext-bengkulusatudata\ckanext\bengkulusatudata\templates\lainnya\survey.html'
    with codecs.open(out_path, 'w', encoding='utf-8') as out:
         out.write('\n'.join(cleaned))
    print('Restored survey.html')

# For SOP
matches2 = re.finditer(r'1: {% extends "page\.html" %}.*?208:\s', text, re.DOTALL)
m2 = list(matches2)
if m2:
    for match in m2:
        if 'BUKU 1: Permintaan Data' in match.group(0):
            content = match.group(0)
            lines = content.split('\n')
            cleaned = [re.sub(r'^\d+: ', '', line) for line in lines]
            out_path2 = r'd:\ProyekBengkuluSatuData\ckan-docker\src\ckanext-bengkulusatudata\ckanext\bengkulusatudata\templates\lainnya\sop.html'
            with codecs.open(out_path2, 'w', encoding='utf-8') as out:
                 out.write('\n'.join(cleaned))
            print('Restored sop.html')
            break
