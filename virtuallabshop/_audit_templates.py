"""
Template refactoring helper script.
Reads a Django template file and extracts:
- Title
- Meta description
- Extra head content (page-specific CSS)
- Body class
- Main content (between header and footer)
- Extra JS (page-specific scripts)
- Lang toggle EN/SI titles and descriptions
"""
import re, sys, os

def extract_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    name = os.path.basename(filepath)
    
    # Extract title
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else 'Virtual Lab Games'
    
    # Extract meta description
    desc_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"', content, re.DOTALL)
    desc = desc_match.group(1).strip() if desc_match else ''
    
    # Extract body class
    body_match = re.search(r'<body\s+class="(.*?)"', content)
    body_class = body_match.group(1) if body_match else ''
    
    # Check for mobile menu
    has_mobile_menu = 'mobileMenuContainer' in content
    
    # Check for lang toggle  
    has_lang_toggle = 'langToggleBtn' in content
    
    # Find page-specific inline styles (after lang-si block)
    # Look for styles that are NOT the standard lang-si block
    style_blocks = re.findall(r'<style>(.*?)</style>', content, re.DOTALL)
    extra_styles = []
    for block in style_blocks:
        # Skip the standard language CSS block
        if 'lang-si' in block and 'body.sinhala-mode' in block:
            # Check if there's extra CSS beyond the standard lang block
            lines = block.strip().split('\n')
            extra_lines = []
            in_lang_block = False
            for line in lines:
                if any(kw in line for kw in ['lang-si', 'sinhala-mode', 'block-lang']):
                    in_lang_block = True
                    continue
                if in_lang_block and line.strip() == '}':
                    in_lang_block = False
                    continue
                if not in_lang_block and line.strip():
                    extra_lines.append(line)
            if extra_lines:
                extra_styles.append('\n'.join(extra_lines))
        else:
            extra_styles.append(block.strip())
    
    # Extract lang toggle titles from JS
    en_title = title
    si_title = title
    en_desc = desc
    si_desc = desc
    
    # Look for setLanguage patterns
    title_en_match = re.search(r"(?:enTitle|'en'.*?document\.title)\s*=\s*['\"](.+?)['\"]", content)
    title_si_match = re.search(r"(?:siTitle|'si'.*?document\.title)\s*=\s*['\"](.+?)['\"]", content)
    
    si_title_match = re.search(r"isSi\s*\?\s*'([^']+)'\s*:", content)
    if si_title_match:
        si_title = si_title_match.group(1)
    
    print(f"=== {name} ===")
    print(f"Title: {title}")
    print(f"Desc: {desc[:80]}...")
    print(f"Body class: {body_class}")
    print(f"Has mobile menu: {has_mobile_menu}")
    print(f"Has lang toggle: {has_lang_toggle}")
    print(f"Extra styles: {len(extra_styles)} blocks")
    if extra_styles:
        for i, style in enumerate(extra_styles):
            print(f"  Style block {i}: {style[:100]}...")
    print()

if __name__ == '__main__':
    template_dir = r'c:\Users\Saranga\Virtual Lab Site\virtuallabshop\shop\templates'
    templates = ['blog.html', 'view_blog.html', 'cart.html', 'product_details.html', 
                 'orders.html', 'profile.html', 'register.html', 'login.html',
                 'pick_storage.html', 'submit_ticket.html', 'my_tickets.html',
                 'quiz_dashboard.html', 'activation.html', 'quiz_attempt.html']
    for t in templates:
        extract_template(os.path.join(template_dir, t))
