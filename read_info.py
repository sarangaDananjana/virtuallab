import json
import urllib.request
import sys
import subprocess

try:
    import pypdf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    import pypdf

pdf_path = r'c:\Users\Saranga\Virtual Lab Site\Steam Ingestion Implementation Plan.pdf'
print("--- PDF CONTENT ---\n")
try:
    reader = pypdf.PdfReader(pdf_path)
    for page in reader.pages:
        print(page.extract_text())
except Exception as e:
    print(f"Failed to read PDF: {e}")

print("\n\n--- STEAM API CONTENT ---\n")
try:
    url = "https://store.steampowered.com/api/appdetails?appids=3321460"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(json.dumps(data, indent=2)[:2000] + "\n...[truncated]...")
except Exception as e:
    print(f"Failed to fetch API: {e}")
