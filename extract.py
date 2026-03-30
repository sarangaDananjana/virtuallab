import json
import urllib.request
import pypdf

pdf_path = r'c:\Users\Saranga\Virtual Lab Site\Steam Ingestion Implementation Plan.pdf'
out_path = r'c:\Users\Saranga\Virtual Lab Site\data_output.txt'

with open(out_path, 'w', encoding='utf-8') as fout:
    fout.write("--- PDF CONTENT ---\n\n")
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page in reader.pages:
            fout.write(page.extract_text() + "\n")
    except Exception as e:
        fout.write(f"Failed to read PDF: {e}\n")

    fout.write("\n\n--- STEAM API CONTENT ---\n\n")
    try:
        url = "https://store.steampowered.com/api/appdetails?appids=3321460"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            fout.write(json.dumps(data, indent=2))
    except Exception as e:
        fout.write(f"Failed to fetch API: {e}\n")
