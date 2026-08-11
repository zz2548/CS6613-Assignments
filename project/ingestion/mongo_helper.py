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

    def insert_video(self, url: str, video_id: str, content: str, segments: List = None, metadata: Dict = None):
        """Insert video transcript data. 'segments' holds the raw timecoded
        transcript (list of {'text', 'start', 'duration'} dicts) so
        downstream citation can reference an exact timecode, the same way
        insert_slide's 'span' references a page."""
        doc = {
            'url': url,
            'video_id': video_id,
            'content': content,
            'segments': segments or [],
            'type': 'video',
            'metadata': metadata or {},
            'ingested_at': datetime.now()
        }
        return self.db.videos.insert_one(doc)

    def get_all_urls(self):
        """Get all ingested URLs for documentation"""
        urls = []
        for doc in self.db.webpages.find({}, {'url': 1}):
            urls.append(('webpage', doc['url']))
        for doc in self.db.slides.find({}, {'url': 1, 'filename': 1}):
            urls.append(('slide', doc.get('url', doc['filename'])))
        for doc in self.db.videos.find({}, {'url': 1, 'video_id': 1}):
            urls.append(('video', doc.get('url', doc.get('video_id'))))
        return urls

    def count_documents(self):
        """Get count of documents in each collection"""
        return {
            'webpages': self.db.webpages.count_documents({}),
            'slides': self.db.slides.count_documents({}),
            'videos': self.db.videos.count_documents({})
        }

    def clear_all(self):
        """Clear all collections"""
        self.db.webpages.delete_many({})
        self.db.slides.delete_many({})
        self.db.videos.delete_many({})
        print("All collections cleared!")