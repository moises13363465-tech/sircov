import os
import glob
import re

templates_dir = r"c:\xampp\htdocs\sircov\templates"

# Script element to inject
inject_str = '<script src="{{ url_for(\'static\', filename=\'js/darkmode.js\') }}"></script>'

# We will inject this right before </head>
pattern = re.compile(r'(</head>)', re.IGNORECASE)

files = glob.glob(os.path.join(templates_dir, "*.html"))
modified_count = 0

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already injected
    if 'darkmode.js' in content:
        continue
        
    match = pattern.search(content)
    if match:
        new_content = content[:match.start()] + f"    {inject_str}\n" + content[match.start():]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        modified_count += 1
        print(f"Injected in {os.path.basename(file_path)}")

print(f"Total files injected: {modified_count}")
