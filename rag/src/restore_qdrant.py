"""
Qdrant Restore Module
Restores Qdrant snapshots/dumps from backup files
"""
import os
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_DUMP_PATH = os.getenv("QDRANT_DUMP_PATH")


def check_qdrant_health() -> bool:
    """
    Check if Qdrant service is running and accessible
    
    Returns:
        True if Qdrant is healthy, False otherwise
    """
    try:
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"Qdrant is running at {QDRANT_HOST}:{QDRANT_PORT}")
            return True
        else:
            print(f"Qdrant responded with status {response.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f" Cannot connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        print(f"  Error: {e}")
        return False


def list_collections() -> list:
    """
    List all collections in Qdrant
    
    Returns:
        List of collection names
    """
    try:
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections"
        response = requests.get(url)
        
        if response.status_code == 200:
            collections = response.json().get('result', {}).get('collections', [])
            collection_names = [col['name'] for col in collections]
            return collection_names
        else:
            print(f"Failed to list collections: {response.status_code}")
            return []
    
    except Exception as e:
        print(f" Error listing collections: {e}")
        return []


def restore_collection_snapshot(
    snapshot_path: str,
    collection_name: str,
    dry_run: bool = False,
    create_collection: bool = True
) -> bool:
    """
    Restore a collection from a snapshot file
    
    Args:
        snapshot_path: Path to snapshot file
        collection_name: Name of the collection to restore
        dry_run: If True, only validate without actually restoring
        create_collection: If True, create collection if it doesn't exist
    
    Returns:
        True if restore was successful (or would be successful in dry-run)
    """
    print(f"\n{'='*60}")
    print(f"Restoring collection '{collection_name}' from snapshot")
    print(f"{'='*60}")
    print(f"Source: {snapshot_path}")
    print(f"Target: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"Dry-run: {dry_run}")
    print(f"{'='*60}\n")
    
    # Validate snapshot file exists
    if not os.path.exists(snapshot_path):
        print(f" Snapshot file not found: {snapshot_path}")
        return False
    
    file_size = os.path.getsize(snapshot_path)
    print(f"Snapshot file found ({file_size / 1024 / 1024:.2f} MB)")
    
    if dry_run:
        print(f"Dry-run: Would restore '{collection_name}' from {snapshot_path}")
        return True
    
    try:
        # Check if collection exists
        existing_collections = list_collections()
        
        if collection_name in existing_collections:
            print(f"Collection '{collection_name}' already exists")
            print(f"  Snapshot restore will overwrite existing data")
        
        # Upload and restore snapshot via HTTP API
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection_name}/snapshots/upload"
        
        print(f"Uploading snapshot...")
        
        with open(snapshot_path, 'rb') as f:
            files = {'snapshot': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Successfully restored collection '{collection_name}'")
            print(f"  Result: {result}")
            return True
        else:
            print(f" Restore failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    
    except Exception as e:
        print(f" Error during restore: {e}")
        return False


def restore_from_path(
    dump_path: str,
    dry_run: bool = False,
    collection_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restore Qdrant data from a dump path
    Supports both single snapshot files and directories with multiple snapshots
    
    Args:
        dump_path: Path to snapshot file or directory
        dry_run: If True, validate only without restoring
        collection_name: Optional collection name (required for single file)
    
    Returns:
        Dictionary with restore results
    """
    results = {
        'success': False,
        'collections_restored': 0,
        'errors': []
    }
    
    # Check Qdrant health
    if not check_qdrant_health():
        results['errors'].append("Qdrant service not available")
        return results
    
    path = Path(dump_path)
    
    if not path.exists():
        print(f" Path not found: {dump_path}")
        results['errors'].append(f"Path not found: {dump_path}")
        return results
    
    # Single snapshot file
    if path.is_file():
        if not collection_name:
            # Try to infer collection name from filename
            collection_name = path.stem.split('_')[0] if '_' in path.stem else 'amu_pyq'
            print(f"No collection name provided, using: {collection_name}")
        
        success = restore_collection_snapshot(
            snapshot_path=str(path),
            collection_name=collection_name,
            dry_run=dry_run
        )
        
        if success:
            results['success'] = True
            results['collections_restored'] = 1
        else:
            results['errors'].append(f"Failed to restore {path.name}")
    
    # Directory with multiple snapshots
    elif path.is_dir():
        snapshot_files = list(path.glob("*.snapshot")) + list(path.glob("*.zip"))
        
        if not snapshot_files:
            print(f"No snapshot files found in {dump_path}")
            results['errors'].append("No snapshot files found")
            return results
        
        print(f"Found {len(snapshot_files)} snapshot file(s)")
        
        for snapshot_file in snapshot_files:
            # Infer collection name from filename
            inferred_collection = snapshot_file.stem.split('_')[0] if '_' in snapshot_file.stem else 'amu_pyq'
            
            success = restore_collection_snapshot(
                snapshot_path=str(snapshot_file),
                collection_name=collection_name or inferred_collection,
                dry_run=dry_run
            )
            
            if success:
                results['collections_restored'] += 1
            else:
                results['errors'].append(f"Failed to restore {snapshot_file.name}")
        
        results['success'] = results['collections_restored'] > 0
    
    return results


def auto_restore_from_env(dry_run: bool = False) -> bool:
    """
    Automatically restore from QDRANT_DUMP_PATH environment variable if set
    
    Args:
        dry_run: If True, validate only without restoring
    
    Returns:
        True if restore was successful or not needed
    """
    if not QDRANT_DUMP_PATH:
        print("No QDRANT_DUMP_PATH environment variable set, skipping auto-restore")
        return True
    
    print(f"\n{'='*60}")
    print("Auto-restore from QDRANT_DUMP_PATH")
    print(f"{'='*60}")
    print(f"Dump path: {QDRANT_DUMP_PATH}")
    print(f"{'='*60}\n")
    
    results = restore_from_path(
        dump_path=QDRANT_DUMP_PATH,
        dry_run=dry_run
    )
    
    if results['success']:
        print(f"\nAuto-restore completed successfully")
        print(f"  Collections restored: {results['collections_restored']}")
        return True
    else:
        print(f"\n Auto-restore failed")
        print(f"  Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"    - {error}")
        return False


def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """
    Get statistics for a collection
    
    Args:
        collection_name: Name of the collection
    
    Returns:
        Dictionary with collection stats
    """
    try:
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection_name}"
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json().get('result', {})
            stats = {
                'name': collection_name,
                'vectors_count': result.get('vectors_count', 0),
                'points_count': result.get('points_count', 0),
                'status': result.get('status', 'unknown'),
            }
            return stats
        else:
            return {'error': f"Failed to get stats: {response.status_code}"}
    
    except Exception as e:
        return {'error': str(e)}


# CLI entrypoint
def main():
    """Command-line interface for Qdrant restore"""
    parser = argparse.ArgumentParser(
        description="Restore Qdrant collections from snapshot files"
    )
    
    parser.add_argument(
        'command',
        choices=['restore', 'auto-restore', 'list', 'stats'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--path',
        type=str,
        help='Path to snapshot file or directory'
    )
    
    parser.add_argument(
        '--collection',
        type=str,
        help='Collection name (required for single snapshot file)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate only, do not actually restore'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=QDRANT_HOST,
        help=f'Qdrant host (default: {QDRANT_HOST})'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=QDRANT_PORT,
        help=f'Qdrant port (default: {QDRANT_PORT})'
    )
    
    args = parser.parse_args()
    
    # Override host/port if provided
    global QDRANT_HOST, QDRANT_PORT
    QDRANT_HOST = args.host
    QDRANT_PORT = args.port
    
    try:
        if args.command == 'restore':
            if not args.path:
                print(" Error: --path is required for restore command")
                return 1
            
            results = restore_from_path(
                dump_path=args.path,
                dry_run=args.dry_run,
                collection_name=args.collection
            )
            
            if results['success']:
                print(f"\nRestore completed successfully!")
                print(f"  Collections: {results['collections_restored']}")
                return 0
            else:
                print(f"\n Restore failed")
                return 1
        
        elif args.command == 'auto-restore':
            success = auto_restore_from_env(dry_run=args.dry_run)
            return 0 if success else 1
        
        elif args.command == 'list':
            if not check_qdrant_health():
                return 1
            
            collections = list_collections()
            print(f"\nCollections ({len(collections)}):")
            for col in collections:
                print(f"  - {col}")
            return 0
        
        elif args.command == 'stats':
            if not args.collection:
                print(" Error: --collection is required for stats command")
                return 1
            
            if not check_qdrant_health():
                return 1
            
            stats = get_collection_stats(args.collection)
            print(f"\nCollection Stats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            return 0
    
    except Exception as e:
        print(f"\n Command failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
