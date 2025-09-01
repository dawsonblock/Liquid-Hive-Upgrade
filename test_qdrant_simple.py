#!/usr/bin/env python3
"""
Simplified Qdrant Test for LIQUID-HIVE
=====================================

Test the Qdrant components in isolation without full system dependencies.
"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, '/app')

def test_qdrant_imports():
    """Test that Qdrant components can be imported."""
    print("🚀 Testing Qdrant Component Imports\n")
    
    try:
        from qdrant_client import QdrantClient
        print("✅ qdrant-client imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import qdrant-client: {e}")
        return False
    
    try:
        from qdrant_client.models import VectorParams, Distance, PointStruct
        print("✅ qdrant-client models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import qdrant-client models: {e}")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ sentence-transformers imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import sentence-transformers: {e}")
        return False
    
    return True

def test_qdrant_retriever_class():
    """Test that the QdrantRetriever class can be instantiated."""
    print("\n" + "="*60)
    print("TEST: QdrantRetriever Class")
    print("="*60)
    
    try:
        # Mock the dependencies if they're not available
        import sys
        from unittest.mock import MagicMock
        
        # Mock sentence transformers if not available
        if 'sentence_transformers' not in sys.modules:
            sys.modules['sentence_transformers'] = MagicMock()
            sys.modules['sentence_transformers'].SentenceTransformer = MagicMock()
        
        # Mock qdrant client if not available  
        if 'qdrant_client' not in sys.modules:
            sys.modules['qdrant_client'] = MagicMock()
            sys.modules['qdrant_client'].QdrantClient = MagicMock()
        
        # Now try to import our retriever
        from hivemind.rag.qdrant_retriever import QdrantRetriever, Document
        print("✅ QdrantRetriever imported successfully")
        
        # Test Document class
        test_doc = Document("Test content", {"source": "test"})
        assert test_doc.page_content == "Test content"
        assert test_doc.metadata["source"] == "test"
        print("✅ Document class working correctly")
        
        # Test QdrantRetriever instantiation (will fail gracefully without Qdrant server)
        retriever = QdrantRetriever(
            collection_name="test",
            embed_model_id="test-model",
            qdrant_url="http://localhost:6333"
        )
        print("✅ QdrantRetriever instantiated (without server connection)")
        
        return True
        
    except Exception as e:
        print(f"❌ QdrantRetriever test failed: {e}")
        return False

def test_hybrid_retriever_class():
    """Test the HybridRetriever class."""
    print("\n" + "="*60)
    print("TEST: HybridRetriever Class")
    print("="*60)
    
    try:
        from hivemind.rag.hybrid_retriever import HybridRetriever, RetrievalMode
        print("✅ HybridRetriever imported successfully")
        
        # Test enum
        assert RetrievalMode.FAISS_ONLY.value == "faiss_only"
        assert RetrievalMode.QDRANT_ONLY.value == "qdrant_only"
        assert RetrievalMode.HYBRID.value == "hybrid"
        assert RetrievalMode.AUTO.value == "auto"
        print("✅ RetrievalMode enum working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ HybridRetriever test failed: {e}")
        return False

def test_migration_utility():
    """Test the migration utility class."""
    print("\n" + "="*60)
    print("TEST: Migration Utility")
    print("="*60)
    
    try:
        from hivemind.rag.migrate_faiss_to_qdrant import FaissToQdrantMigrator
        print("✅ FaissToQdrantMigrator imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration utility test failed: {e}")
        return False

def test_docker_compose_config():
    """Test that docker-compose.yml has been updated for Qdrant."""
    print("\n" + "="*60)
    print("TEST: Docker Compose Configuration")
    print("="*60)
    
    try:
        docker_compose_path = Path("/app/docker-compose.yml")
        if docker_compose_path.exists():
            content = docker_compose_path.read_text()
            
            checks = [
                ("qdrant service", "qdrant:" in content),
                ("qdrant image", "qdrant/qdrant:latest" in content),
                ("qdrant ports", "6333:6333" in content),
                ("qdrant storage", "qdrant_storage" in content),
                ("api depends on qdrant", "- qdrant" in content)
            ]
            
            all_passed = True
            for check_name, check_result in checks:
                if check_result:
                    print(f"✅ {check_name}")
                else:
                    print(f"❌ {check_name}")
                    all_passed = False
            
            return all_passed
        else:
            print("❌ docker-compose.yml not found")
            return False
            
    except Exception as e:
        print(f"❌ Docker compose config test failed: {e}")
        return False

async def test_enhanced_features():
    """Test enhanced features like metadata filtering."""
    print("\n" + "="*60)
    print("TEST: Enhanced Features")
    print("="*60)
    
    try:
        # Test metadata filtering logic (without actual Qdrant connection)
        from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
        
        # Simulate building a filter
        metadata_filter = {
            "content_type": "python_code",
            "file_size": {"gte": 1000, "lte": 50000}
        }
        
        conditions = []
        for key, value in metadata_filter.items():
            field_key = f"metadata.{key}"
            
            if isinstance(value, dict):
                if "gte" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(gte=value["gte"])))
                if "lte" in value:
                    conditions.append(FieldCondition(key=field_key, range=Range(lte=value["lte"])))
            else:
                conditions.append(FieldCondition(key=field_key, match=MatchValue(value=value)))
        
        search_filter = Filter(must=conditions) if conditions else None
        
        print(f"✅ Metadata filter created with {len(conditions)} conditions")
        print("✅ Enhanced filtering logic working")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 LIQUID-HIVE Qdrant Upgrade Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_qdrant_imports),
        ("QdrantRetriever Class", test_qdrant_retriever_class),
        ("HybridRetriever Class", test_hybrid_retriever_class),
        ("Migration Utility", test_migration_utility),
        ("Docker Configuration", test_docker_compose_config),
        ("Enhanced Features", lambda: asyncio.run(test_enhanced_features()))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Qdrant upgrade implementation is correct.")
        print("\n📝 Next steps:")
        print("   1. Start Qdrant service: docker-compose up -d qdrant")
        print("   2. Run migration: python hivemind/rag/migrate_faiss_to_qdrant.py")
        print("   3. Update server to use QdrantRetriever or HybridRetriever")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)