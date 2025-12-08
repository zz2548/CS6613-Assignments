from pymongo import MongoClient
from datetime import datetime
from typing import Dict, List, Any

class MongoHelper:
    def __init__(self, host='mongo', port=27017, database='erica_tutor'):
        self.client = MongoClient(host, port)
        self.db = self.client[database]
        
    def insert_webpage(self, url: str, title: str, content: str, metadata: Dict = None):
        """Insert webpage data"""
        doc = {
            'url': url,
            'title': title,
            'content': content,
            'type': 'webpage',
            'metadata': metadata or {},
            'ingested_at': datetime.now()
        }
        return self.db.webpages.insert_one(doc)
    
    def insert_slide(self, url: str, filename: str, content: str, metadata: Dict = None):
        """Insert slide/PDF data"""
        doc = {
            'url': url,
            'filename': filename,
            'content': content,
            'type': 'slide',
            'metadata': metadata or {},
            'ingested_at': datetime.now()
        }
        return self.db.slides.insert_one(doc)
    
    def get_all_urls(self):
        """Get all ingested URLs for documentation"""
        urls = []
        for doc in self.db.webpages.find({}, {'url': 1}):
            urls.append(('webpage', doc['url']))
        for doc in self.db.slides.find({}, {'url': 1, 'filename': 1}):
            urls.append(('slide', doc.get('url', doc['filename'])))
        return urls
    
    def count_documents(self):
        """Get count of documents in each collection"""
        return {
            'webpages': self.db.webpages.count_documents({}),
            'slides': self.db.slides.count_documents({})
        }
    
    def clear_all(self):
        """Clear all collections"""
        self.db.webpages.delete_many({})
        self.db.slides.delete_many({})
        print("All collections cleared!")