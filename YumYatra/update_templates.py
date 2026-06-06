import os
import glob

template_dir = r'c:\Users\ganes\OneDrive\Desktop\django project\YumYatra\delivery\Templates'

for file_path in glob.glob(os.path.join(template_dir, '*.html')):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    if '{% load static %}' not in content:
        content = '{% load static %}\n' + content
        modified = True
    
    # Try adding to head
    if 'premium.css' not in content:
        if '</head>' in content:
            content = content.replace('</head>', '    <link rel="stylesheet" href="{% static \'premium.css\' %}">\n</head>')
            modified = True
        elif '<body>' in content: # fallback if no head
            content = content.replace('<body>', '<head><link rel="stylesheet" href="{% static \'premium.css\' %}"></head>\n<body>')
            modified = True
            
    # Add a class to links acting as buttons in admin_home
    if 'admin_home.html' in file_path and 'class="btn"' not in content:
        content = content.replace('<a href', '<a class="btn" href')
        modified = True
        
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {os.path.basename(file_path)}')
