import os
import glob

template_dir = r'c:\Users\ganes\OneDrive\Desktop\django project\YumYatra\delivery\Templates'
for file_path in glob.glob(os.path.join(template_dir, '*.html')):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    if 'style.css' in content:
        content = content.replace('<link rel="stylesheet" href="{% static \'style.css\' %}">', '')
        modified = True
        
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Cleaned {os.path.basename(file_path)}')
