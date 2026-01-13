#!/usr/bin/env python3
"""
Script to analyze URLs for /blog/ paths from CSV data
"""

# The CSV data as a multi-line string
csv_data = """state	query	url	title	snippet	pattern
Alabama	"white for life" dentistry Alabama	https://www.gentledentistrytampa.com/teeth-whitening/	Teeth Whitening Tampa FL - Opalescence Boost™ Teeth Whitening	Call and ask about our "White for Life" Program and our "Dental Savings Plan"! ... Alabama. She received her Fellowship at the Academy of General Dentistry ...
Alabama	"white for life" dentistry Alabama	https://riverwestdentalid.com/services/	Services – Riverwest Dental	Brighten your smile for free when you join our "White For Life" program and attend your six month routine cleanings. ... Recursos Posteriores Al Tratamiento ...
Alabama	"white for life" dentistry Alabama	https://westgatedentalcentre.com/the-science-behind-orthodontic-treatments-impact-on-your-airway/	How an Orthodontist Improves Airway Health	General Dentistry · Dental Fillings · Wisdom Teeth Extraction · Sleep Apnea Treatment · Implant Overdentures · Dental Implant Surgery · White for Life Program ...
Arizona	"white for life" dentistry Arizona	http://dog-diamond.com/blog/column/20240811column/	ペットホテル パピーパーティ 犬の保育園(dog nursery)｜DOG ...	Austin Ekeler's return from an ankle injury will help goyard sale which reads Wei ein Leben lang translated to white for life ...
California	"white for life" dentistry California	https://www.marconidentalgroup.com/4-signs-youre-flossing-wrong/	4 Signs You're Flossing Wrong - Marconi Dental Group	The relative dental health of adults in California is quite good. For ... Keeping Your Smile White for Life. August 12, 2015 July 18, 2022. If you've ...
"""

import csv
from io import StringIO

# Parse the CSV
reader = csv.DictReader(StringIO(csv_data), delimiter='\t')

blog_urls = []
total_urls = 0

for row in reader:
    total_urls += 1
    url = row.get('url', '')

    if '/blog/' in url.lower():
        blog_urls.append({
            'state': row.get('state', ''),
            'url': url,
            'title': row.get('title', ''),
            'query': row.get('query', '')
        })

print("="*80)
print("URL ANALYSIS RESULTS")
print("="*80)
print(f"\nTotal URLs analyzed: {total_urls}")
print(f"URLs containing '/blog/': {len(blog_urls)}")
if total_urls > 0:
    print(f"Percentage: {(len(blog_urls)/total_urls*100):.2f}%\n")

if blog_urls:
    print("\nURLs with /blog/ path:")
    print("-"*80)
    for i, item in enumerate(blog_urls, 1):
        print(f"\n{i}. State: {item['state']}")
        print(f"   URL: {item['url']}")
        print(f"   Title: {item['title'][:80]}...")
        print(f"   Query: {item['query']}")
else:
    print("\nNo URLs containing '/blog/' were found in this sample.")

print("\n" + "="*80)
