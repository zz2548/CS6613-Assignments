#!/usr/bin/env python3
"""Test MongoDB and Ollama connections"""

from mongo_helper import MongoHelper
import requests

def test_mongodb():
    """Test MongoDB connection"""
    print("Testing MongoDB connection...")
    try:
        mongo = MongoHelper()
        counts = mongo.count_documents()
        print("MongoDB connected successfully!")
        print(f"  Current counts: {counts}")
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False

def test_ollama():
    """Test Ollama connection"""
    print("\nTesting Ollama connection...")
    try:
        response = requests.get("http://ollama:11434/api/tags")
        if response.status_code == 200:
            models = response.json()
            print("Ollama connected successfully!")
            print(f"  Available models: {[m['name'] for m in models.get('models', [])]}")
            return True
        else:
            print(f"Ollama returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ollama connection failed: {e}")
        return False

if __name__ == "__main__":
    mongodb_ok = test_mongodb()
    ollama_ok = test_ollama()
    
    if mongodb_ok and ollama_ok:
        print("\nAll systems ready!")
    else:
        print("\nSome systems failed - check configuration")
