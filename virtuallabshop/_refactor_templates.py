"""
Safe template refactoring script.
Creates .bak backups and uses careful extraction to convert templates
to use {% extends "base.html" %}.

Strategy:
1. Read the full file
2. Find the boundaries of: head, header, main content, footer, mobile menu, scripts
3. Extract ONLY the unique parts
4. Write the new file with {% extends %}
5. Keep .bak backup
"""
import re, os

TEMPLATE_DIR = r'c:\Users\Saranga\Virtual Lab Site\virtuallabshop\shop\templates'

def process_template(filename):
    filepath = os.path.join(TEMPLATE_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    with open(filepath + '.bak', 'w', encoding='utf-8') as f:
        f.write(content)
    
    name = os.path.splitext(filename)[0]
    
    # === EXTRACT TITLE ===
    title_m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    title = title_m.group(1).strip() if title_m else 'Virtual Lab Games'
    
    # === EXTRACT META DESC ===
    desc_m = re.search(r'<meta\s+name="description"\s*\n?\s*content="(.*?)"', content, re.DOTALL)
    desc = desc_m.group(1).strip() if desc_m else ''
    
    # === EXTRACT BODY CLASS ===
    body_m = re.search(r'<body\s+class="(.*?)"', content)
    body_class = body_m.group(1) if body_m else ''
    default_body = 'bg-aurora text-white selection:bg-gold-400/30 selection:text-white noise'
    
    # === EXTRACT PAGE-SPECIFIC CSS ===
    # Get all style blocks
    extra_css = ''
    for style_m in re.finditer(r'<style>(.*?)</style>', content, re.DOTALL):
        raw = style_m.group(1)
        # Remove the standard language helper CSS lines
        cleaned_lines = []
        skip_block = False
        for line in raw.split('\n'):
            s = line.strip()
            # Skip language helper declarations
            if any(x in s for x in [
                '.lang-si {', 'body.sinhala-mode .lang-en {',
                'body.sinhala-mode .lang-si {', '.block-lang.lang-si {',
                'body.sinhala-mode .block-lang.lang-en {',
                'body.sinhala-mode .block-lang.lang-si {',
            ]):
                skip_block = True
                continue
            if skip_block:
                if s == '}':
                    skip_block = False
                continue
            # Skip lang helper comments
            if s.startswith('/* Language') or s.startswith('/* Lang'):
                continue
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        if result:
            extra_css += result + '\n'
    
    extra_css = extra_css.strip()
    # Remove empty lines at start
    extra_css = re.sub(r'^\s*\n', '', extra_css)
    
    # === EXTRACT DESKTOP NAV (if different from default) ===
    desktop_nav = ''
    nav_m = re.search(r'(<nav class="hidden lg:flex.*?</nav>)', content, re.DOTALL)
    if nav_m:
        nav_html = nav_m.group(1)
        # Check if it's the default nav (Home, Blog, Support)
        has_blog = "blog_page" in nav_html
        has_quiz = "quiz-dashboard" in nav_html
        if not has_blog or has_quiz:
            # Non-default nav — keep it
            desktop_nav = nav_html
    
    # === EXTRACT MAIN CONTENT ===
    # Content is between </header> and either <footer or mobile menu or scripts
    header_end = content.find('</header>')
    if header_end >= 0:
        header_end += len('</header>')
    else:
        body_tag_m = re.search(r'<body[^>]*>', content)
        header_end = body_tag_m.end() if body_tag_m else 0
    
    # Find where unique content ends
    footer_pos = content.find('<footer')
    mobile_pos = content.find('<div id="mobileMenuContainer"')
    
    # Use the earliest of footer or mobile menu
    content_end = len(content)
    if footer_pos >= 0:
        content_end = min(content_end, footer_pos)
    if mobile_pos >= 0:
        content_end = min(content_end, mobile_pos)
    
    main_content = content[header_end:content_end].strip()
    
    # === EXTRACT PAGE-SPECIFIC SCRIPTS ===
    # Find all script blocks after the main content area
    extra_scripts = []
    all_scripts_start = content_end
    for script_m in re.finditer(r'(<script(?:\s+[^>]*)?>)(.*?)(</script>)', content[all_scripts_start:], re.DOTALL):
        full_tag = script_m.group(0)
        open_tag = script_m.group(1)
        script_body = script_m.group(2).strip()
        
        # Skip if it's an external script src reference that's standard
        if 'src=' in open_tag:
            # Keep non-standard external scripts (like lottie)
            extra_scripts.append(full_tag)
            continue
        
        # Skip if empty
        if not script_body:
            continue
        
        # Check if this script ONLY contains mobile menu + lang toggle + year
        is_shared_only = True
        
        # Check for unique page logic markers
        unique_markers = [
            'loadGames', 'loadOrders', 'loadCart', 'loadBlog',
            'loadProduct', 'submitForm', 'loadTickets', 'fetchPosts',
            'loadActivation', 'API_URL', 'apiCall', 'fetch(',
            'FormData', 'fileInput', 'showToast', 'DOMContentLoaded',
        ]
        
        for marker in unique_markers:
            if marker in script_body:
                is_shared_only = False
                break
        
        if is_shared_only:
            # Check if it's also not just year + mobile + lang
            has_only_shared = all(
                kw in script_body for kw in ['year', 'navToggle']
            ) or all(
                kw in script_body for kw in ['langToggleBtn', 'setLanguage']
            )
            if has_only_shared:
                continue  # Skip — handled by base.html
        
        # Clean the script: remove mobile menu logic, lang toggle logic, year setter
        cleaned = script_body
        
        # Remove year setter
        cleaned = re.sub(
            r"document\.getElementById\('year'\)(?:\.textContent\s*=\s*new\s+Date\(\)\.getFullYear\(\);|&&.*?;)",
            '',
            cleaned
        )
        
        # Remove mobile menu logic block
        cleaned = re.sub(
            r'(?://\s*---?\s*Mobile Menu.*?(?=//\s*---?\s*Language|$))',
            '', cleaned, flags=re.DOTALL
        )
        cleaned = re.sub(
            r"const navToggle\s*=.*?}\);",
            '', cleaned, flags=re.DOTALL
        )
        
        # Remove language toggle logic block  
        cleaned = re.sub(
            r'(?://\s*---?\s*Language.*?setLanguage\(.*?\);)',
            '', cleaned, flags=re.DOTALL
        )
        cleaned = re.sub(
            r"const langToggleBtn\s*=.*?setLanguage\(.*?\);",
            '', cleaned, flags=re.DOTALL
        )
        
        cleaned = cleaned.strip()
        if cleaned and cleaned != '});' and len(cleaned) > 10:
            extra_scripts.append(f'<script>\n{cleaned}\n</script>')
    
    extra_js = '\n'.join(extra_scripts).strip()
    
    # === EXTRACT MOBILE NAV LINKS (if active page differs from default) ===
    mobile_nav = ''
    mobile_nav_m = re.search(
        r'<hr class="border-white/10 my-4">\s*(.*?)</nav>',
        content, re.DOTALL
    )
    if mobile_nav_m:
        raw_nav = mobile_nav_m.group(1).strip()
        # Check if Shop link is active (gold) — that's the base.html default
        # If a different link is active, we need to override
        if 'bg-white/10 text-gold-400' in raw_nav:
            # Find which link is active
            active_m = re.search(r'href="{% url \'(\w+[^\']*)\' %}"[^>]*bg-white/10 text-gold-400', raw_nav)
            if active_m:
                active_url = active_m.group(1)
                if active_url != 'shop-page':
                    mobile_nav = raw_nav
        else:
            mobile_nav = raw_nav
    
    # === EXTRACT LANG EN/SI TITLES ===
    si_title = title
    si_desc = desc
    
    # Look for SI title in JS
    si_title_m = re.search(r"isSi\s*\?\s*'([^']+)'", content)
    if si_title_m:
        si_title = si_title_m.group(1)
    else:
        si_title_m2 = re.search(r"document\.title\s*=\s*isSi\s*\?\s*'([^']+)'", content)
        if si_title_m2:
            si_title = si_title_m2.group(1)
    
    si_desc_m = re.search(r"newDesc\s*=\s*isSi\s*\n?\s*\?\s*'([^']+)'", content, re.DOTALL)
    if si_desc_m:
        si_desc = si_desc_m.group(1)
    
    # === BUILD OUTPUT ===
    parts = []
    parts.append('{% extends "base.html" %}')
    parts.append('{% load static %}')
    parts.append('')
    parts.append(f'{{% block title %}}{title}{{% endblock %}}')
    if desc:
        parts.append(f'{{% block meta_description %}}{desc}{{% endblock %}}')
    parts.append('')
    parts.append(f'{{% block title_en %}}{title}{{% endblock %}}')
    parts.append(f'{{% block title_si %}}{si_title}{{% endblock %}}')
    parts.append(f'{{% block desc_en %}}{desc}{{% endblock %}}')
    parts.append(f'{{% block desc_si %}}{si_desc}{{% endblock %}}')
    
    if body_class and body_class != default_body:
        parts.append('')
        parts.append(f'{{% block body_class %}}{body_class}{{% endblock %}}')
    
    if extra_css:
        parts.append('')
        parts.append('{% block extra_head %}')
        parts.append('<style>')
        parts.append(extra_css)
        parts.append('</style>')
        parts.append('{% endblock %}')
    
    if desktop_nav:
        parts.append('')
        parts.append('{% block desktop_nav %}')
        parts.append(desktop_nav)
        parts.append('{% endblock %}')
    
    if mobile_nav:
        parts.append('')
        parts.append('{% block mobile_nav_links %}')
        parts.append(mobile_nav)
        parts.append('{% endblock %}')
    
    parts.append('')
    parts.append('{% block content %}')
    parts.append(main_content)
    parts.append('{% endblock %}')
    
    if extra_js:
        parts.append('')
        parts.append('{% block extra_js %}')
        parts.append(extra_js)
        parts.append('{% endblock %}')
    
    output = '\n'.join(parts) + '\n'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)
    
    orig_size = len(content)
    new_size = len(output)
    reduction = ((orig_size - new_size) / orig_size * 100)
    print(f"  {filename}: {orig_size:,} -> {new_size:,} bytes ({reduction:.0f}% smaller)")
    return True


if __name__ == '__main__':
    # These templates should use base.html 
    # (quiz_dashboard.html already done manually, shop.html already done, payment_done.html already done)
    templates = [
        'blog.html', 'view_blog.html', 'cart.html', 'product_details.html',
        'orders.html', 'profile.html', 'register.html', 'login.html',
        'pick_storage.html', 'submit_ticket.html', 'my_tickets.html',
        'activation.html',
    ]
    
    print("Refactoring templates...")
    print("Backups saved as .bak files\n")
    
    for t in templates:
        try:
            process_template(t)
        except Exception as e:
            print(f"  ERROR processing {t}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nDone!")
