import os, re
templates_dir = r'c:\Users\Saranga\Virtual Lab Site\virtuallabshop\shop\templates'
count = 0
for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            def class_replacer(match):
                class_str = match.group(1)
                if 'from-brand-500 to-gold-400' in class_str:
                    class_str = class_str.replace('bg-gradient-to-r from-brand-500 to-gold-400', 'bg-gold-gradient')
                    class_str = class_str.replace('bg-gradient-to-br from-brand-500 to-gold-400', 'bg-gold-gradient')
                    class_str = class_str.replace('text-white', 'text-black')
                return f'class="{class_str}"'
            
            new_content = re.sub(r'class="([^"]*)"', class_replacer, content)
            
            if new_content != content:
                count += 1
                print(f"Updated {file}")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
print(f"Updated {count} files.")
