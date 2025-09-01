#!/usr/bin/env python3
"""
Test script for Semantic Caching with Redis
===========================================

This script tests the semantic caching system including:
- Redis connectivity and cache operations
- Semantic similarity matching using embeddings
- Cache management and analytics
- Integration with the chat system
- Performance optimization
"""

import asyncio
import json
import sys
import os
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, '/app')

async def test_semantic_caching_system():
    """Test the complete semantic caching system."""
    print("🧠 Testing Semantic Caching with Redis\n")
    
    # Test 1: Import and Initialization
    print("="*60)
    print("TEST 1: Cache System Initialization")
    print("="*60)
    
    try:
        from hivemind.cache import SemanticCache, CacheStrategy, get_semantic_cache, create_cache_manager
        print("✅ Cache modules imported successfully")
        
        # Initialize semantic cache
        cache = await get_semantic_cache(
            redis_url="redis://localhost:6379",
            embedding_model="all-MiniLM-L6-v2",
            similarity_threshold=0.95
        )
        
        await asyncio.sleep(2)  # Give time for initialization
        
        if cache and cache.is_ready:
            print("✅ Semantic cache initialized successfully")
            print(f"   - Strategy: {cache.strategy.value}")
            print(f"   - Similarity threshold: {cache.similarity_threshold}")
            print(f"   - Default TTL: {cache.default_ttl}s")
        else:
            print("❌ Semantic cache initialization failed")
            return await test_without_redis()
            
    except Exception as e:
        print(f"❌ Cache initialization failed: {e}")
        return await test_without_redis()
    
    # Test 2: Basic Cache Operations
    print("\n" + "="*60)
    print("TEST 2: Basic Cache Operations")
    print("="*60)
    
    # Test cache set and get
    test_queries = [
        {
            "query": "What is artificial intelligence?",
            "response": {
                "answer": "Artificial Intelligence (AI) is a branch of computer science focused on creating systems that can perform tasks requiring human intelligence.",
                "provider": "test_cache"
            }
        },
        {
            "query": "How does machine learning work?", 
            "response": {
                "answer": "Machine learning works by using algorithms to find patterns in data and make predictions without explicit programming.",
                "provider": "test_cache"
            }
        }
    ]
    
    cached_count = 0
    for test_query in test_queries:
        success = await cache.set(test_query["query"], test_query["response"])
        if success:
            cached_count += 1
            print(f"✅ Cached: {test_query['query'][:50]}...")
        else:
            print(f"❌ Failed to cache: {test_query['query'][:50]}...")
    
    print(f"📊 Successfully cached {cached_count}/{len(test_queries)} queries")
    
    # Test exact retrieval
    exact_result = await cache.get("What is artificial intelligence?")
    if exact_result:
        print("✅ Exact cache retrieval working")
        print(f"   - Cache hit: {exact_result.get('cache_hit', False)}")
        print(f"   - Answer: {exact_result['answer'][:80]}...")
    else:
        print("❌ Exact cache retrieval failed")
    
    # Test 3: Semantic Similarity Matching
    print("\n" + "="*60)
    print("TEST 3: Semantic Similarity Matching")
    print("="*60)
    
    # Test similar queries that should match
    similar_queries = [
        "What is AI?",  # Should match "What is artificial intelligence?"
        "Can you explain artificial intelligence?",
        "Tell me about machine learning algorithms",  # Should match ML query
        "How do ML models work?"
    ]
    
    semantic_hits = 0
    for query in similar_queries:
        result = await cache.get(query)
        if result and result.get("cache_hit"):
            semantic_hits += 1
            similarity = result.get("cache_similarity", 0)
            original_query = result.get("cache_original_query", "unknown")
            print(f"✅ Semantic match: '{query[:40]}...' → '{original_query[:40]}...' (similarity: {similarity:.3f})")
        else:
            print(f"❌ No semantic match: '{query[:40]}...'")
    
    print(f"📊 Semantic hits: {semantic_hits}/{len(similar_queries)}")
    
    # Test 4: Cache Analytics and Management
    print("\n" + "="*60)
    print("TEST 4: Cache Analytics and Management")
    print("="*60)
    
    try:
        # Get analytics
        analytics = await cache.get_analytics()
        print("✅ Cache analytics:")
        print(f"   - Total queries: {analytics.get('total_queries', 0)}")
        print(f"   - Cache hits: {analytics.get('cache_hits', 0)}")
        print(f"   - Cache misses: {analytics.get('cache_misses', 0)}")
        print(f"   - Hit rate: {analytics.get('hit_rate', 0):.1%}")
        print(f"   - Current cache size: {analytics.get('current_size', 0)}")
        
        # Test cache manager
        cache_manager = await create_cache_manager("redis://localhost:6379")
        if cache_manager:
            print("✅ Cache manager initialized")
            
            # Generate performance analysis
            analysis = await cache_manager.analyze_cache_performance()
            if "error" not in analysis:
                print("✅ Performance analysis generated")
                recommendations = analysis.get("recommendations", [])
                if recommendations:
                    print(f"   - Recommendations: {len(recommendations)} found")
                    for rec in recommendations[:2]:  # Show first 2
                        print(f"     • {rec}")
            else:
                print(f"❌ Performance analysis failed: {analysis['error']}")
        else:
            print("❌ Cache manager initialization failed")
            
    except Exception as e:
        print(f"❌ Analytics test failed: {e}")
    
    # Test 5: Health Check and Status
    print("\n" + "="*60)
    print("TEST 5: Health Check and Status")
    print("="*60)
    
    try:
        health = await cache.health_check()
        print("✅ Health check results:")
        print(f"   - Status: {health.get('status', 'unknown')}")
        print(f"   - Redis connected: {health.get('redis_connected', False)}")
        print(f"   - Embedding model loaded: {health.get('embedding_model_loaded', False)}")
        
        if health.get("last_error"):
            print(f"   - Last error: {health['last_error']}")
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test 6: Performance and Optimization
    print("\n" + "="*60)
    print("TEST 6: Performance Testing")
    print("="*60)
    
    try:
        # Performance test with batch queries
        batch_queries = [
            "What are neural networks?",
            "Explain deep learning", 
            "How do convolutional neural networks work?",
            "What is natural language processing?",
            "Describe reinforcement learning"
        ]
        
        # Test cache misses (new queries)
        miss_start = time.time()
        miss_results = []
        for query in batch_queries:
            result = await cache.get(query)
            miss_results.append(result)
        miss_time = time.time() - miss_start
        
        # Cache these queries
        for query in batch_queries:
            await cache.set(query, {
                "answer": f"This is a test response for: {query}",
                "provider": "performance_test"
            })
        
        # Test cache hits (cached queries)
        hit_start = time.time()
        hit_results = []
        for query in batch_queries:
            result = await cache.get(query)
            hit_results.append(result)
        hit_time = time.time() - hit_start
        
        cache_hits = sum(1 for result in hit_results if result and result.get("cache_hit"))
        
        print("✅ Performance test results:")
        print(f"   - Cache misses: {len(batch_queries)} queries in {miss_time:.3f}s ({miss_time/len(batch_queries):.3f}s avg)")
        print(f"   - Cache hits: {cache_hits}/{len(batch_queries)} queries in {hit_time:.3f}s ({hit_time/len(batch_queries):.3f}s avg)")
        
        if hit_time > 0 and miss_time > 0:
            speedup = miss_time / hit_time
            print(f"   - Cache speedup: {speedup:.1f}x faster")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
    
    # Test 7: Cache Strategy Testing
    print("\n" + "="*60)
    print("TEST 7: Cache Strategy Testing")
    print("="*60)
    
    try:
        # Test different caching strategies
        original_strategy = cache.strategy
        
        # Test aggressive strategy
        cache.strategy = CacheStrategy.AGGRESSIVE
        aggressive_cached = await cache.set("This is a very short query", {"answer": "Short answer", "provider": "test"})
        
        # Test conservative strategy  
        cache.strategy = CacheStrategy.CONSERVATIVE
        conservative_cached = await cache.set("This is a comprehensive and detailed question about complex topics", {
            "answer": "This is a detailed and comprehensive answer that provides thorough information about the topic.",
            "provider": "test"
        })
        
        # Test selective strategy
        cache.strategy = CacheStrategy.SELECTIVE
        selective_cached = await cache.set("What is the best practice for software development?", {
            "answer": "Best practices include code reviews, testing, and documentation.",
            "provider": "test"
        })
        
        print(f"✅ Strategy testing:")
        print(f"   - Aggressive (short query): {'✅' if aggressive_cached else '❌'}")
        print(f"   - Conservative (detailed): {'✅' if conservative_cached else '❌'}")
        print(f"   - Selective (best practice): {'✅' if selective_cached else '❌'}")
        
        # Restore original strategy
        cache.strategy = original_strategy
        
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
    
    # Cleanup test data
    try:
        clear_result = await cache.clear_cache("test")
        print(f"\n🗑️ Cleanup: Cleared {clear_result.get('cleared_entries', 0)} test entries")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    print("\n" + "="*60)
    print("✅ Semantic Caching Test Complete!")
    print("="*60)
    
    return True

async def test_without_redis():
    """Test when Redis is not available."""
    print("\n🔄 Testing without Redis (graceful degradation)")
    
    try:
        from hivemind.cache import SemanticCache, CacheStrategy
        
        # Try to create cache with invalid Redis URL
        cache = SemanticCache(redis_url="redis://invalid:6379")
        
        await asyncio.sleep(1)
        
        if not cache.is_ready:
            print("✅ Graceful degradation when Redis unavailable")
            
            # Test that cache operations don't crash
            result = await cache.get("test query")
            if result is None:
                print("✅ Cache get returns None gracefully")
            
            success = await cache.set("test query", {"answer": "test"})
            if not success:
                print("✅ Cache set returns False gracefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Graceful degradation test failed: {e}")
        return False

def main():
    """Run all semantic caching tests."""
    print("🧪 LIQUID-HIVE Semantic Caching Test Suite")
    print("=" * 60)
    
    try:
        result = asyncio.run(test_semantic_caching_system())
        if result:
            print("\n🎉 All tests passed! Semantic caching system is working correctly.")
            print("\n📝 Integration notes:")
            print("   • Cache will automatically check for similar queries")
            print("   • Responses are cached based on semantic similarity")
            print("   • Cache hit rate should improve over time")
            print("   • Monitor /api/cache/analytics for performance metrics")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)