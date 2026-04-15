import re
import codecs

path = r'C:\Users\ASUS\.gemini\antigravity\brain\f495097d-4eac-47b2-b438-03a5efad0b07\.system_generated\logs\overview.txt'
with codecs.open(path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# We look for the big block output by view_file for sop.html
matches = re.finditer(r'1: {% extends "page\.html" %}.*?200:           <a href="{{ h.url_for_static.*?\n', text, re.DOTALL)
m_list = list(matches)
if m_list:
    content = m_list[-1].group(0)
    lines = content.split('\n')
    cleaned = [re.sub(r'^\d+: ', '', line) for line in lines]
    
    out_path = r'd:\ProyekBengkuluSatuData\ckan-docker\src\ckanext-bengkulusatudata\ckanext\bengkulusatudata\templates\lainnya\sop.html'
    with codecs.open(out_path, 'w', encoding='utf-8') as out:
         out.write('\n'.join(cleaned) + '          </a>\n        </div>\n      </div>\n    </div> <!-- Akhir Grid -->\n  </div>\n{% endblock %}')
    print('Restored sop.html')
else:
    print('Failed to find sop contents')
