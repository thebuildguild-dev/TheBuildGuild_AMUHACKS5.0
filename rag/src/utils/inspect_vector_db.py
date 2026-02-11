import os
from src.clients.qdrant_client import get_qdrant_client
from src.services.vector_service import DEFAULT_COLLECTION_NAME
import json

def inspect_vector_db():
    print(f"Connecting to Qdrant...")
    client = get_qdrant_client()
    collection_name = DEFAULT_COLLECTION_NAME
    
    try:
        info = client.get_collection(collection_name)
        print(f"\nCollection: {collection_name}")
        print(f"Status: {info.status}")
        print(f"Points count: {info.points_count}")
        
        print("\n--- Recent Points ---")
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        for p in points:
            print(f"\nID: {p.id}")
            payload = p.payload
            print(f"Filename: {payload.get('filename', 'N/A')}")
            print(f"SHA256: {payload.get('document_sha256', 'N/A')}")
            print(f"Stats: Chunk {payload.get('chunk_number')}, Pages {payload.get('page_start')}-{payload.get('page_end')}")
            text_preview = payload.get('text', '')[:100].replace('\n', ' ')
            print(f"Text: {text_preview}...")
            
            papers = payload.get('papers', [])
            if papers:
                print(f"Metadata (Papers):")
                print(json.dumps(papers, indent=2))
            else:
                print("Metadata: None")
            
    except Exception as e:
        print(f"Error inspecting DB: {e}")

if __name__ == "__main__":
    inspect_vector_db()
