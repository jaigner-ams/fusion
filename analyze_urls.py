import csv
import sys

# CSV data will be read from a file
csv_file = 'urls_data.csv'

# Count URLs containing /blog/
blog_urls = []
total_urls = 0

try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Try to detect the delimiter
        sample = f.read(1024)
        f.seek(0)

        # Use tab as delimiter since the data appears to be tab-separated
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            total_urls += 1
            url = row.get('url', '')

            if '/blog/' in url:
                blog_urls.append({
                    'state': row.get('state', ''),
                    'url': url,
                    'title': row.get('title', '')
                })

        print(f"Total URLs analyzed: {total_urls}")
        print(f"URLs containing '/blog/': {len(blog_urls)}")
        print(f"\nPercentage: {(len(blog_urls)/total_urls*100):.2f}%\n")

        if blog_urls:
            print("URLs with /blog/ path:")
            print("-" * 80)
            for i, item in enumerate(blog_urls, 1):
                print(f"{i}. [{item['state']}] {item['url']}")
                print(f"   Title: {item['title']}")
                print()
        else:
            print("No URLs containing '/blog/' were found.")

except FileNotFoundError:
    print(f"Error: Could not find {csv_file}")
    print("Please save your CSV data to a file named 'urls_data.csv'")
except Exception as e:
    print(f"Error: {e}")
