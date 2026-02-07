#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import sys

sys.path.insert(0, '/Users/shivendratewari/github/Vedic-Sanskrit-Tutor')

load_dotenv()
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)
info = client.get_collection(os.getenv("COLLECTION_NAME", "ancient_history"))
print(f"Total points: {info.points_count:,}")
