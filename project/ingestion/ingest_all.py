#!/usr/bin/env python3
"""
Ingestion pipeline for Introduction to AI course from pantelis.github.io
"""

from mongo_helper import MongoHelper
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Set, List
import re

class CourseIngestion:
    def __init__(self):
        self.mongo = MongoHelper()
        self.visited_urls: Set[str] = set()
        self.base_url = "https://pantelis.github.io"
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and within course domain"""
        parsed = urlparse(url)
        
        # Must be from pantelis.github.io
        if 'pantelis.github.io' not in parsed.netloc:
            return False
        
        # Skip non-HTML content
        skip_extensions = ['.pdf', '.zip', '.jpg', '.png', '.gif', '.mp4']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
            
        # Skip external links
        if url.startswith('http') and 'pantelis.github.io' not in url:
            return False
            
        return True
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all valid links from a page"""
        links = []
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])
            # Remove fragments
            url = url.split('#')[0]
            if self.is_valid_url(url) and url not in self.visited_urls:
                links.append(url)
        return links
    
    def ingest_webpage(self, url: str, max_depth: int = 3, current_depth: int = 0):
        """Recursively fetch and store webpage content"""
        if url in self.visited_urls or current_depth > max_depth:
            return
        
        self.visited_urls.add(url)
        
        try:
            print(f"{'  ' * current_depth}Fetching: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else url
            
            # Remove script, style, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extract main content
            content = soup.get_text(separator='\n', strip=True)
            
            # Store in MongoDB
            metadata = {
                'depth': current_depth,
                'word_count': len(content.split())
            }
            
            self.mongo.insert_webpage(url, title, content, metadata)
            print(f"{'  ' * current_depth}✓ Stored: {title[:50]}...")
            
            # Extract and follow links (only for course-related pages)
            if current_depth < max_depth:
                links = self.extract_links(soup, url)
                time.sleep(0.5)  # Be nice to the server
                
                for link in links:
                    self.ingest_webpage(link, max_depth, current_depth + 1)
                    
        except Exception as e:
            print(f"{'  ' * current_depth}✗ Failed: {url} - {e}")
    
    def run_website_ingestion(self):
        """Ingest the entire course website"""
        print("=" * 60)
        print("INGESTING COURSE WEBSITE")
        print("=" * 60)
        
        # Start URLs
        start_urls = [
            "https://pantelis.github.io/courses/ai/",
            "https://pantelis.github.io/courses/ai/syllabus/",
        ]
        
        for url in start_urls:
            self.ingest_webpage(url, max_depth=3)
        
        print(f"\n✓ Website ingestion complete! Visited {len(self.visited_urls)} pages")
    
    def ingest_youtube_videos(self, video_urls: List[str]):
        """Ingest YouTube videos (placeholder - needs yt-dlp)"""
        print("\n" + "=" * 60)
        print("INGESTING YOUTUBE VIDEOS")
        print("=" * 60)
        
        if not video_urls:
            print("No YouTube URLs provided. Skipping...")
            return
        
        # TODO: Implement YouTube transcript extraction
        print("YouTube ingestion to be implemented with yt-dlp")
        print(f"Videos to ingest: {len(video_urls)}")
    
    def ingest_pdfs(self, pdf_paths: List[str]):
        """Ingest PDF files"""
        print("\n" + "=" * 60)
        print("INGESTING PDF FILES")
        print("=" * 60)
        
        if not pdf_paths:
            print("No PDFs provided. Skipping...")
            return
        
        # TODO: Implement PDF extraction
        print("PDF ingestion to be implemented with PyPDF2")
        print(f"PDFs to ingest: {len(pdf_paths)}")
    
    def print_summary(self):
        """Print ingestion summary"""
        counts = self.mongo.count_documents()
        
        print("\n" + "=" * 60)
        print("INGESTION SUMMARY")
        print("=" * 60)
        print(f"Webpages ingested: {counts['webpages']}")
        print(f"Videos ingested:   {counts['videos']}")
        print(f"Slides ingested:   {counts['slides']}")
        print(f"Total URLs visited: {len(self.visited_urls)}")
        
        print("\n" + "=" * 60)
        print("ALL INGESTED URLs (Required for M2)")
        print("=" * 60)
        for doc_type, url in self.mongo.get_all_urls():
            print(f"[{doc_type:8s}] {url}")


if __name__ == "__main__":
    # Create ingestion instance
    ingestion = CourseIngestion()
    
    # Clear previous data (comment out if you want to keep existing data)
    # ingestion.mongo.clear_all()
    
    # Ingest website
    ingestion.run_website_ingestion()
    
    # YouTube videos (add if you have them)
    youtube_urls = [
        # Add YouTube video URLs here
    ]
    ingestion.ingest_youtube_videos(youtube_urls)
    
    # PDF slides (add paths here)
    pdf_files = [
        # Add PDF file paths here, e.g., "/data/slides/lecture1.pdf"
    ]
    ingestion.ingest_pdfs(pdf_files)
    
    # Print summary
    ingestion.print_summary()
