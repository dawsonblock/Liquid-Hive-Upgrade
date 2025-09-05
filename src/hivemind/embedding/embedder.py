"""Smart embedder with multi-provider support and deterministic fallbacks."""

import os
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    DETERMINISTIC_HASH = "deterministic_hash"

# Configuration
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
DEFAULT_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
OPENAI_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_EMBED_MODEL", "text-embedding-v1")
SENTENCE_MODEL = os.getenv("SENTENCE_EMBED_MODEL", "all-MiniLM-L6-v2")

# Provider availability cache
_provider_cache = {}

def _check_openai_available() -> bool:
    """Check if OpenAI is available."""
    if "openai" in _provider_cache:
        return _provider_cache["openai"]
    
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        available = bool(api_key and len(api_key) > 10)
        _provider_cache["openai"] = available
        
        if available:
            logger.info("OpenAI embeddings available")
        else:
            logger.warning("OpenAI API key not configured")
        
        return available
        
    except ImportError:
        _provider_cache["openai"] = False
        logger.warning("OpenAI library not installed")
        return False

def _check_deepseek_available() -> bool:
    """Check if DeepSeek is available."""
    if "deepseek" in _provider_cache:
        return _provider_cache["deepseek"]
    
    try:
        # DeepSeek uses OpenAI-compatible API
        import openai
        api_key = os.getenv("DEEPSEEK_API_KEY")
        available = bool(api_key and len(api_key) > 10)
        _provider_cache["deepseek"] = available
        
        if available:
            logger.info("DeepSeek embeddings available")
        else:
            logger.warning("DeepSeek API key not configured")
        
        return available
        
    except ImportError:
        _provider_cache["deepseek"] = False
        logger.warning("OpenAI library not available for DeepSeek")
        return False

def _check_sentence_transformers_available() -> bool:
    """Check if Sentence Transformers is available."""
    if "sentence_transformers" in _provider_cache:
        return _provider_cache["sentence_transformers"]
    
    try:
        import sentence_transformers
        _provider_cache["sentence_transformers"] = True
        logger.info("Sentence Transformers available")
        return True
        
    except ImportError:
        _provider_cache["sentence_transformers"] = False
        logger.warning("Sentence Transformers not installed")
        return False

def _embed_with_openai(text: str) -> List[float]:
    """Generate embedding using OpenAI."""
    try:
        import openai
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.embeddings.create(
            model=OPENAI_MODEL,
            input=text,
            encoding_format="float"
        )
        
        embedding = response.data[0].embedding
        
        # Validate dimension
        if len(embedding) != EMBED_DIM:
            logger.warning("OpenAI embedding dimension mismatch",
                          expected=EMBED_DIM,
                          actual=len(embedding))
            # Pad or truncate to expected dimension
            if len(embedding) < EMBED_DIM:
                embedding.extend([0.0] * (EMBED_DIM - len(embedding)))
            else:
                embedding = embedding[:EMBED_DIM]
        
        logger.debug("OpenAI embedding generated", text_length=len(text))
        return embedding
        
    except Exception as e:
        logger.error("OpenAI embedding failed", error=str(e))
        raise

def _embed_with_deepseek(text: str) -> List[float]:
    """Generate embedding using DeepSeek."""
    try:
        import openai
        
        # DeepSeek uses OpenAI-compatible API
        client = openai.OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        
        response = client.embeddings.create(
            model=DEEPSEEK_MODEL,
            input=text
        )
        
        embedding = response.data[0].embedding
        
        # Validate and adjust dimension if needed
        if len(embedding) != EMBED_DIM:
            logger.warning("DeepSeek embedding dimension mismatch",
                          expected=EMBED_DIM,
                          actual=len(embedding))
            if len(embedding) < EMBED_DIM:
                embedding.extend([0.0] * (EMBED_DIM - len(embedding)))
            else:
                embedding = embedding[:EMBED_DIM]
        
        logger.debug("DeepSeek embedding generated", text_length=len(text))
        return embedding
        
    except Exception as e:
        logger.error("DeepSeek embedding failed", error=str(e))
        raise

def _embed_with_sentence_transformers(text: str) -> List[float]:
    """Generate embedding using Sentence Transformers."""
    try:
        from sentence_transformers import SentenceTransformer
        
        # Load model (cached after first use)
        if not hasattr(_embed_with_sentence_transformers, "_model"):
            _embed_with_sentence_transformers._model = SentenceTransformer(SENTENCE_MODEL)
            logger.info("Sentence Transformers model loaded", model=SENTENCE_MODEL)
        
        model = _embed_with_sentence_transformers._model
        
        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        embedding_list = embedding.tolist()
        
        # Adjust dimension if needed
        if len(embedding_list) != EMBED_DIM:
            logger.warning("Sentence Transformers dimension mismatch",
                          expected=EMBED_DIM,
                          actual=len(embedding_list))
            if len(embedding_list) < EMBED_DIM:
                embedding_list.extend([0.0] * (EMBED_DIM - len(embedding_list)))
            else:
                embedding_list = embedding_list[:EMBED_DIM]
        
        logger.debug("Sentence Transformers embedding generated", text_length=len(text))
        return embedding_list
        
    except Exception as e:
        logger.error("Sentence Transformers embedding failed", error=str(e))
        raise

def _embed_deterministic_hash(text: str) -> List[float]:
    """Generate deterministic embedding from text hash."""
    try:
        # Create deterministic hash-based embedding
        text_hash = hashlib.sha256(text.encode("utf-8")).digest()
        
        # Use hash bytes to seed numpy random state
        seed = int.from_bytes(text_hash[:4], "big")
        np.random.seed(seed)
        
        # Generate random normal vector with fixed dimension
        embedding = np.random.normal(0, 1, size=EMBED_DIM)
        
        # Normalize to unit length for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        embedding_list = embedding.astype(float).tolist()
        
        logger.debug("Deterministic hash embedding generated", 
                    text_length=len(text),
                    hash_seed=seed)
        return embedding_list
        
    except Exception as e:
        logger.error("Deterministic embedding failed", error=str(e))
        # Ultra-fallback: return zero vector
        return [0.0] * EMBED_DIM

class SmartEmbedder:
    """Smart embedder that tries multiple providers with fallbacks."""
    
    def __init__(self, preferred_provider: Optional[EmbeddingProvider] = None):
        """Initialize embedder with preferred provider.
        
        Args:
            preferred_provider: Preferred embedding provider
        """
        self.preferred_provider = preferred_provider or EmbeddingProvider(DEFAULT_PROVIDER)
        self.fallback_order = [
            EmbeddingProvider.OPENAI,
            EmbeddingProvider.DEEPSEEK,
            EmbeddingProvider.SENTENCE_TRANSFORMERS,
            EmbeddingProvider.DETERMINISTIC_HASH
        ]
        
        # Statistics
        self.stats = {
            "embeddings_generated": 0,
            "provider_usage": {provider.value: 0 for provider in EmbeddingProvider},
            "failures": {provider.value: 0 for provider in EmbeddingProvider},
            "fallback_activations": 0
        }
        
        logger.info("SmartEmbedder initialized", 
                   preferred=self.preferred_provider.value,
                   dimension=EMBED_DIM)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding with smart provider fallback.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector of length EMBED_DIM
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * EMBED_DIM
        
        # Try preferred provider first
        providers_to_try = [self.preferred_provider]
        
        # Add fallbacks if preferred provider fails
        for provider in self.fallback_order:
            if provider not in providers_to_try:
                providers_to_try.append(provider)
        
        last_error = None
        
        for provider in providers_to_try:
            try:
                # Check provider availability
                if provider == EmbeddingProvider.OPENAI and not _check_openai_available():
                    continue
                elif provider == EmbeddingProvider.DEEPSEEK and not _check_deepseek_available():
                    continue
                elif provider == EmbeddingProvider.SENTENCE_TRANSFORMERS and not _check_sentence_transformers_available():
                    continue
                
                # Generate embedding
                if provider == EmbeddingProvider.OPENAI:
                    embedding = _embed_with_openai(text)
                elif provider == EmbeddingProvider.DEEPSEEK:
                    embedding = _embed_with_deepseek(text)
                elif provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
                    embedding = _embed_with_sentence_transformers(text)
                else:  # DETERMINISTIC_HASH
                    embedding = _embed_deterministic_hash(text)
                
                # Update statistics
                self.stats["embeddings_generated"] += 1
                self.stats["provider_usage"][provider.value] += 1
                
                if provider != self.preferred_provider:
                    self.stats["fallback_activations"] += 1
                    logger.info("Fallback provider used",
                               preferred=self.preferred_provider.value,
                               used=provider.value)
                
                logger.debug("Embedding generated successfully",
                           provider=provider.value,
                           text_length=len(text),
                           embedding_dim=len(embedding))
                
                return embedding
                
            except Exception as e:
                last_error = e
                self.stats["failures"][provider.value] += 1
                logger.warning("Embedding provider failed",
                             provider=provider.value,
                             error=str(e))
                continue
        
        # All providers failed
        logger.error("All embedding providers failed", last_error=str(last_error))
        self.stats["failures"]["total"] = self.stats["failures"].get("total", 0) + 1
        
        # Return deterministic fallback as last resort
        return _embed_deterministic_hash(text)
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            batch_embeddings = []
            for text in batch:
                embedding = self.embed(text)
                batch_embeddings.append(embedding)
            
            embeddings.extend(batch_embeddings)
            
            logger.debug("Batch embedding completed",
                        batch_start=i,
                        batch_size=len(batch),
                        total_progress=f"{i + len(batch)}/{len(texts)}")
        
        return embeddings
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedder statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        total_generated = self.stats["embeddings_generated"]
        total_failures = sum(self.stats["failures"].values())
        
        return {
            **self.stats,
            "success_rate": (
                total_generated / max(total_generated + total_failures, 1)
            ),
            "preferred_provider": self.preferred_provider.value,
            "fallback_rate": (
                self.stats["fallback_activations"] / max(total_generated, 1)
            ),
            "providers_available": {
                provider.value: self._is_provider_available(provider)
                for provider in EmbeddingProvider
            }
        }
    
    def _is_provider_available(self, provider: EmbeddingProvider) -> bool:
        """Check if a provider is available."""
        if provider == EmbeddingProvider.OPENAI:
            return _check_openai_available()
        elif provider == EmbeddingProvider.DEEPSEEK:
            return _check_deepseek_available()
        elif provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            return _check_sentence_transformers_available()
        else:  # DETERMINISTIC_HASH
            return True  # Always available

# Global embedder instance
_global_embedder: Optional[SmartEmbedder] = None

def get_embedder() -> SmartEmbedder:
    """Get global embedder instance."""
    global _global_embedder
    
    if _global_embedder is None:
        try:
            preferred = EmbeddingProvider(DEFAULT_PROVIDER)
        except ValueError:
            preferred = EmbeddingProvider.OPENAI
        
        _global_embedder = SmartEmbedder(preferred)
    
    return _global_embedder

def embed_text(text: str) -> List[float]:
    """Convenience function to embed single text.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector
    """
    embedder = get_embedder()
    return embedder.embed(text)

def embed_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Convenience function to embed multiple texts.
    
    Args:
        texts: List of texts to embed
        batch_size: Batch processing size
        
    Returns:
        List of embedding vectors
    """
    embedder = get_embedder()
    return embedder.embed_batch(texts, batch_size)

def get_embedding_dimension() -> int:
    """Get configured embedding dimension.
    
    Returns:
        Embedding vector dimension
    """
    return EMBED_DIM

def get_provider_status() -> Dict[str, Any]:
    """Get status of all embedding providers.
    
    Returns:
        Provider availability and configuration
    """
    embedder = get_embedder()
    
    return {
        "configured_dimension": EMBED_DIM,
        "default_provider": DEFAULT_PROVIDER,
        "models": {
            "openai": OPENAI_MODEL,
            "deepseek": DEEPSEEK_MODEL,
            "sentence_transformers": SENTENCE_MODEL
        },
        "availability": {
            "openai": _check_openai_available(),
            "deepseek": _check_deepseek_available(),
            "sentence_transformers": _check_sentence_transformers_available(),
            "deterministic_hash": True
        },
        "statistics": embedder.get_stats()
    }

def health_check() -> Dict[str, Any]:
    """Health check for embedding system.
    
    Returns:
        Health status and basic functionality test
    """
    try:
        # Test basic embedding generation
        test_text = "This is a health check test."
        embedding = embed_text(test_text)
        
        # Validate result
        if len(embedding) != EMBED_DIM:
            return {
                "status": "unhealthy",
                "error": f"Embedding dimension mismatch: {len(embedding)} != {EMBED_DIM}"
            }
        
        # Check if embedding contains non-zero values
        if all(x == 0.0 for x in embedding):
            return {
                "status": "degraded",
                "warning": "All embedding values are zero"
            }
        
        embedder = get_embedder()
        stats = embedder.get_stats()
        
        return {
            "status": "healthy",
            "test_embedding_generated": True,
            "embedding_dimension": len(embedding),
            "provider_used": "determined_dynamically",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error("Embedding health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }