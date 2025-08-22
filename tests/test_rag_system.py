"""
Unit tests for RAG system components (MEM-01)
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from agents.shared.rag_system import (
    TextChunker, EmbeddingGenerator, VectorStore, SemanticCache, 
    RAGSystem, Document, DocumentChunk
)


class TestTextChunker:
    """Test text chunking functionality"""
    
    def setup_method(self):
        self.chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    
    def test_chunk_recursive_basic(self):
        """Test basic text chunking"""
        text = "This is a test document. It has multiple sentences. Each sentence should be processed correctly."
        chunks = self.chunker.chunk_recursive(text)
        assert len(chunks) > 0
        assert all(len(self.chunker.tokenizer.encode(chunk)) <= self.chunker.chunk_size for chunk in chunks)
    
    def test_chunk_document(self):
        """Test document chunking"""
        document = Document(
            content="This is a test document with multiple paragraphs.\n\nSecond paragraph here.",
            metadata={"source": "test"},
            doc_id="test_doc_1"
        )
        
        chunks = self.chunker.chunk_document(document)
        assert len(chunks) > 0
        assert all(chunk.doc_id == "test_doc_1" for chunk in chunks)
        assert all("source" in chunk.metadata for chunk in chunks)


class TestEmbeddingGenerator:
    """Test embedding generation"""
    
    def setup_method(self):
        self.generator = EmbeddingGenerator()
    
    def test_generate_single_embedding(self):
        """Test single text embedding"""
        text = "This is a test sentence."
        embedding = self.generator.generate_embedding(text)
        assert isinstance(embedding, list)
        assert len(embedding) == self.generator.dimension
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """Test batch embedding generation"""
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = self.generator.generate_embeddings_batch(texts)
        assert len(embeddings) == len(texts)
        assert all(len(emb) == self.generator.dimension for emb in embeddings)


@pytest.mark.asyncio
class TestSemanticCache:
    """Test Redis semantic cache"""
    
    def setup_method(self):
        self.cache = SemanticCache()
    
    @patch('agents.shared.rag_system.redis.Redis')
    async def test_cache_operations(self, mock_redis):
        """Test cache get and set operations"""
        mock_redis_instance = AsyncMock()
        mock_redis.return_value = mock_redis_instance
        
        self.cache.redis_client = mock_redis_instance
        
        # Test cache miss
        mock_redis_instance.get.return_value = None
        result = await self.cache.get_cached_result("test query", [0.1, 0.2, 0.3])
        assert result is None
        
        # Test cache set
        mock_redis_instance.setex.return_value = True
        await self.cache.cache_result("test query", [], ttl=3600)
        mock_redis_instance.setex.assert_called_once()


@pytest.mark.asyncio
class TestVectorStore:
    """Test Qdrant vector store operations"""
    
    def setup_method(self):
        self.vector_store = VectorStore()
    
    @patch('agents.shared.rag_system.AsyncQdrantClient')
    async def test_index_chunks(self, mock_qdrant):
        """Test chunk indexing"""
        mock_client = AsyncMock()
        mock_qdrant.return_value = mock_client
        
        self.vector_store.client = mock_client
        
        chunks = [
            DocumentChunk(
                content="Test content 1",
                metadata={"source": "test"},
                doc_id="doc1",
                chunk_id="doc1_chunk_0"
            ),
            DocumentChunk(
                content="Test content 2", 
                metadata={"source": "test"},
                doc_id="doc1",
                chunk_id="doc1_chunk_1"
            )
        ]
        
        await self.vector_store.index_chunks(chunks)
        mock_client.upsert.assert_called_once()
    
    @patch('agents.shared.rag_system.AsyncQdrantClient')
    async def test_search(self, mock_qdrant):
        """Test vector search"""
        mock_client = AsyncMock()
        mock_qdrant.return_value = mock_client
        
        self.vector_store.client = mock_client
        
        # Mock search results
        mock_result = Mock()
        mock_result.payload = {
            "content": "Test content",
            "metadata": {"source": "test"},
            "doc_id": "doc1",
            "chunk_id": "doc1_chunk_0"
        }
        mock_result.score = 0.95
        mock_client.search.return_value = [mock_result]
        
        results = await self.vector_store.search("test query")
        assert len(results) == 1
        assert results[0].score == 0.95
        assert results[0].chunk.content == "Test content"


@pytest.mark.asyncio 
class TestRAGSystem:
    """Test complete RAG system integration"""
    
    @patch('agents.shared.rag_system.AsyncQdrantClient')
    @patch('agents.shared.rag_system.redis.Redis')
    async def test_rag_workflow(self, mock_redis, mock_qdrant):
        """Test complete RAG workflow"""
        # Setup mocks
        mock_qdrant_client = AsyncMock()
        mock_qdrant.return_value = mock_qdrant_client
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        rag_system = RAGSystem()
        rag_system.vector_store.client = mock_qdrant_client
        rag_system.semantic_cache.redis_client = mock_redis_client
        
        # Test document indexing
        document = Document(
            content="This is a test document for RAG system testing.",
            metadata={"source": "test", "category": "unit_test"},
            doc_id="test_doc_rag"
        )
        
        await rag_system.index_document(document)
        mock_qdrant_client.upsert.assert_called()
        
        # Test search with cache miss
        mock_redis_client.get.return_value = None
        mock_result = Mock()
        mock_result.payload = {
            "content": "Relevant test content",
            "metadata": {"source": "test"},
            "doc_id": "test_doc_rag", 
            "chunk_id": "test_doc_rag_chunk_0"
        }
        mock_result.score = 0.92
        mock_qdrant_client.search.return_value = [mock_result]
        
        results = await rag_system.search_relevant_context("test query")
        assert len(results) == 1
        assert results[0].score == 0.92
        
        # Verify cache was called
        mock_redis_client.setex.assert_called()