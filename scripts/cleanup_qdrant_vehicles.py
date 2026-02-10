#!/usr/bin/env python3
"""
Cleanup Script: Remove Vehicle Collection from Qdrant
Phase 0 - Multi-Tenant RaaS Transformation

This script removes the 'vehicles' collection from Qdrant vector database.
NO BACKUP is created as per user confirmation.

DANGER: This operation is IRREVERSIBLE!
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse


def get_qdrant_client():
    """Create and return a Qdrant client."""
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    print(f"Connecting to Qdrant at {host}:{port}...")
    client = QdrantClient(host=host, port=port)
    return client


def list_collections(client):
    """List all collections in Qdrant."""
    try:
        collections = client.get_collections()
        return [col.name for col in collections.collections]
    except Exception as e:
        print(f"Error listing collections: {e}")
        return []


def delete_vehicle_collection(client, collection_name="vehicles"):
    """Delete the vehicle collection from Qdrant."""
    try:
        # Check if collection exists
        collections = list_collections(client)

        if collection_name not in collections:
            print(f"✓ Collection '{collection_name}' does not exist (nothing to delete)")
            return True

        # Get collection info before deletion
        try:
            info = client.get_collection(collection_name)
            vector_count = info.points_count if hasattr(info, 'points_count') else "unknown"
            print(f"\nCollection Info:")
            print(f"  - Name: {collection_name}")
            print(f"  - Vectors: {vector_count}")
        except:
            pass

        # Confirm deletion
        print(f"\n{'='*60}")
        print(f"WARNING: You are about to delete collection '{collection_name}'")
        print(f"This will permanently remove ALL vectors and data.")
        print(f"NO BACKUP will be created.")
        print(f"{'='*60}")

        confirmation = input("\nType 'DELETE' to confirm: ").strip()

        if confirmation != "DELETE":
            print("Aborted by user.")
            return False

        # Delete the collection
        print(f"\nDeleting collection '{collection_name}'...")
        client.delete_collection(collection_name)
        print(f"✓ Collection '{collection_name}' deleted successfully!")

        return True

    except UnexpectedResponse as e:
        print(f"Error deleting collection: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def verify_cleanup(client, collection_name="vehicles"):
    """Verify that the collection has been deleted."""
    collections = list_collections(client)

    print(f"\n{'='*60}")
    print("Verification:")
    print(f"{'='*60}")

    if collection_name in collections:
        print(f"⚠ WARNING: Collection '{collection_name}' still exists!")
        return False
    else:
        print(f"✓ Collection '{collection_name}' successfully removed")

    print(f"\nRemaining collections ({len(collections)}):")
    if collections:
        for col in collections:
            print(f"  - {col}")
    else:
        print("  (none)")

    return True


def main():
    """Main cleanup function."""
    print("="*60)
    print("Qdrant Cleanup Script - Vehicle Collection Removal")
    print("Phase 0: Multi-Tenant RaaS Transformation")
    print("="*60)
    print()

    try:
        # Connect to Qdrant
        client = get_qdrant_client()
        print("✓ Connected to Qdrant successfully")

        # List current collections
        print("\nCurrent collections:")
        collections = list_collections(client)
        for col in collections:
            print(f"  - {col}")

        if not collections:
            print("  (no collections found)")
            print("\n✓ Nothing to clean up!")
            return 0

        # Delete vehicle collection
        if not delete_vehicle_collection(client, "vehicles"):
            print("\n✗ Cleanup failed or was aborted")
            return 1

        # Verify cleanup
        if not verify_cleanup(client, "vehicles"):
            print("\n⚠ Verification failed!")
            return 1

        print("\n" + "="*60)
        print("Cleanup Summary:")
        print("="*60)
        print("Vehicle collection: DELETED")
        print("Data backup: NONE (as requested)")
        print()
        print("✓ Qdrant cleanup completed successfully!")
        print()
        print("Next Steps:")
        print("1. Complete PostgreSQL cleanup (run cleanup_vehicle_data.sql)")
        print("2. Begin Phase 1: Create abstraction interfaces")
        print("3. Create new multi-tenant schema")
        print("="*60)

        return 0

    except KeyboardInterrupt:
        print("\n\nAborted by user (Ctrl+C)")
        return 1
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
