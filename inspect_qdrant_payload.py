#!/usr/bin/env python3
"""
Inspect actual payload structure in Qdrant
"""
import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

collection_name = os.getenv("COLLECTION_NAME", "ancient_history")

print("\n" + "=" * 90)
print("🔍 INSPECTING QDRANT PAYLOAD STRUCTURE")
print("=" * 90)

# Get first 5 points to see payload structure
points, _ = client.scroll(
    collection_name=collection_name,
    offset=0,
    limit=5,
    with_payload=True,
    with_vectors=False
)

for i, point in enumerate(points, 1):
    print(f"\n📌 Point {i} (ID: {point.id}):")
    if point.payload:
        print("   Payload keys:", list(point.payload.keys()))
        print("   Payload content:")
        for key, value in point.payload.items():
            if isinstance(value, str):
                preview = value[:80] + "..." if len(value) > 80 else value
            else:
                preview = str(value)[:80]
            print(f"     • {key}: {preview}")
    else:
        print("   ⚠️  NO PAYLOAD!")

print("\n" + "=" * 90)

# Check if this is a different batch with different content
print("\n📊 Checking different batch...")
points, _ = client.scroll(
    collection_name=collection_name,
    offset=5000,
    limit=5,
    with_payload=True,
    with_vectors=False
)

for i, point in enumerate(points, 1):
    print(f"\n📌 Point {i} (ID: {point.id}, offset 5000):")
    if point.payload:
        print("   Payload keys:", list(point.payload.keys()))
        for key, value in point.payload.items():
            if isinstance(value, str):
                preview = value[:80] + "..." if len(value) > 80 else value
            else:
                preview = str(value)[:80]
            print(f"     • {key}: {preview}")
    else:
        print("   ⚠️  NO PAYLOAD!")

print("\n" + "=" * 90)
