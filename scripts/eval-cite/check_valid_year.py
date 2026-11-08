from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def check_valid_year():
    bib_path = ROOT / 'assets' / 'bib' / 'cites.bib'
    
    with open(bib_path, 'r', encoding='utf-8') as r:
        content = r.read()
    
    pattern = r'(?i)\byear\s*=\s*[\{""]?(\d{4})[\}""]?'
    years = re.findall(pattern, content)
    
    invalidated_cites = [int(y) for y in years if int(y) < 2016]
    return invalidated_cites

def main():
    invalid_years = sorted(set(check_valid_year()))
    
    for idx, year in enumerate(invalid_years, start=1):
        print(f"{idx:02d}. {year}")

if __name__ == '__main__':
    main()