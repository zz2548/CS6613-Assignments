#!/usr/bin/env python3
"""
Verify M2 Ingestion - Required for milestone documentation
"""
import sys
sys.path.append('/workspace')

from ingestion.mongo_helper import MongoHelper

def verify_ingestion():
    mongo = MongoHelper()
    
    print("=" * 70)
    print("M2 INGESTION VERIFICATION")
    print("=" * 70)
    
    # Get counts
    counts = mongo.count_documents()
    print(f"\nDocument Counts:")
    print(f"  Webpages: {counts['webpages']}")
    print(f"  Videos:   {counts['videos']}")
    print(f"  Slides:   {counts['slides']}")
    print(f"  TOTAL:    {sum(counts.values())}")
    
    # Sample webpage
    print("\n" + "=" * 70)
    print("SAMPLE WEBPAGE")
    print("=" * 70)
    webpage = mongo.db.webpages.find_one()
    if webpage:
        print(f"Title: {webpage['title']}")
        print(f"URL: {webpage['url']}")
        print(f"Word Count: {webpage['metadata'].get('word_count', 'N/A')}")
        print(f"Content Preview:\n{webpage['content'][:500]}...\n")
    
    # List all URLs (required for M2)
    print("=" * 70)
    print("ALL INGESTED URLs (Required for M2 Documentation)")
    print("=" * 70)
    for doc_type, url in mongo.get_all_urls():
        print(f"[{doc_type}] {url}")
    
    # Content statistics
    print("\n" + "=" * 70)
    print("CONTENT STATISTICS")
    print("=" * 70)
    
    total_words = 0
    for doc in mongo.db.webpages.find():
        total_words += doc['metadata'].get('word_count', 0)
    
    print(f"Total words ingested: {total_words:,}")
    print(f"Average words per page: {total_words // counts['webpages']:,}")

if __name__ == "__main__":
    verify_ingestion()
