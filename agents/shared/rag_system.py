"""
RAG (Retrieval-Augmented Generation) system for LLM1 (MEM-01)
Implements text chunking, embedding generation, vector storage in Qdrant, and semantic search.
"""
import hashlib
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import asyncio
import json

import redis.asyncio as redis
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
import tiktoken

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class Document:
    content: str
    metadata: Dict[str, Any]
    doc_id: str


@dataclass
class DocumentChunk:
    content: str
    metadata: Dict[str, Any]
    doc_id: str
    chunk_id: str
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    chunk: DocumentChunk
    score: float


class TextChunker:
    """Handles text chunking strategies"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_recursive(self, text: str, separators: List[str] = None) -> List[str]:
        """Recursive text chunking that preserves context"""
        if separators is None:
            separators = ["\n\n", "\n", ". ", " "]
        
        chunks = []
        current_chunk = ""
        
        def _split_text(text: str, sep_index: int = 0) -> List[str]:
            if sep_index >= len(separators):
                return [text]
            
            separator = separators[sep_index]
            splits = text.split(separator)
            
            result = []
            for split in splits:
                if len(self.tokenizer.encode(split)) <= self.chunk_size:
                    result.append(split)
                else:
                    result.extend(_split_text(split, sep_index + 1))
            
            return result
        
        splits = _split_text(text)
        
        for split in splits:
            if len(self.tokenizer.encode(current_chunk + split)) <= self.chunk_size:
                current_chunk += split
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_document(self, document: Document) -> List[DocumentChunk]:
        """Convert document into chunks"""
        text_chunks = self.chunk_recursive(document.content)
        chunks = []
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{document.doc_id}_chunk_{i}"
            chunk = DocumentChunk(
                content=chunk_text,
                metadata={**document.metadata, "chunk_index": i},
                doc_id=document.doc_id,
                chunk_id=chunk_id
            )
            chunks.append(chunk)
        
        return chunks


class EmbeddingGenerator:
    """Generates embeddings for text chunks"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        return self.model.encode(text).tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]


class SemanticCache:
    """Redis-based semantic cache for similar queries"""
    
    def __init__(self):
        self.redis_client = None
        self.similarity_threshold = config.SEMANTIC_SIMILARITY_THRESHOLD
    
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        return f"semantic_cache:{hashlib.md5(query.encode()).hexdigest()}"
    
    async def get_cached_result(self, query: str, query_embedding: List[float]) -> Optional[List[SearchResult]]:
        """Get cached result for semantically similar query"""
        # For now, use exact match. In production, implement semantic similarity search
        cache_key = self._generate_cache_key(query)
        cached_data = await self.redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode cached data for key: {cache_key}")
        
        return None
    
    async def cache_result(self, query: str, result: List[SearchResult], ttl: int = None):
        """Cache search result"""
        cache_key = self._generate_cache_key(query)
        ttl = ttl or config.REDIS_TTL
        
        # Convert SearchResult objects to dict for JSON serialization
        serializable_result = [
            {
                "chunk": {
                    "content": r.chunk.content,
                    "metadata": r.chunk.metadata,
                    "doc_id": r.chunk.doc_id,
                    "chunk_id": r.chunk.chunk_id
                },
                "score": r.score
            }
            for r in result
        ]
        
        await self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(serializable_result)
        )


class VectorStore:
    """Qdrant vector database interface"""
    
    def __init__(self):
        self.client = None
        self.collection_name = config.QDRANT_COLLECTION_NAME
        self.embedding_generator = EmbeddingGenerator()
    
    async def connect(self):
        """Connect to Qdrant"""
        self.client = AsyncQdrantClient(
            host=config.QDRANT_HOST,
            port=config.QDRANT_PORT
        )
        await self._ensure_collection_exists()
    
    async def disconnect(self):
        """Disconnect from Qdrant"""
        if self.client:
            await self.client.close()
    
    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            await self.client.get_collection(self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_generator.dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
    
    async def index_chunks(self, chunks: List[DocumentChunk]):
        """Index document chunks in vector store"""
        if not chunks:
            return
        
        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_generator.generate_embeddings_batch(texts)
        
        # Create points for Qdrant
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload={
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id
                }
            )
            points.append(point)
        
        # Insert into Qdrant
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Indexed {len(chunks)} chunks")
    
    async def search(self, query: str, limit: int = 5, score_threshold: float = 0.7) -> List[SearchResult]:
        """Search for relevant chunks"""
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Search in Qdrant
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Convert to SearchResult objects
        search_results = []
        for result in results:
            chunk = DocumentChunk(
                content=result.payload["content"],
                metadata=result.payload["metadata"],
                doc_id=result.payload["doc_id"],
                chunk_id=result.payload["chunk_id"]
            )
            search_result = SearchResult(chunk=chunk, score=result.score)
            search_results.append(search_result)
        
        return search_results


class RAGSystem:
    """Main RAG system that orchestrates all components"""
    
    def __init__(self):
        self.chunker = TextChunker()
        self.vector_store = VectorStore()
        self.semantic_cache = SemanticCache()
    
    async def initialize(self):
        """Initialize all components"""
        await self.vector_store.connect()
        await self.semantic_cache.connect()
        logger.info("RAG system initialized")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.vector_store.disconnect()
        await self.semantic_cache.disconnect()
        logger.info("RAG system shutdown")
    
    async def index_document(self, document: Document):
        """Index a document in the RAG system"""
        # Chunk the document
        chunks = self.chunker.chunk_document(document)
        
        # Index chunks in vector store
        await self.vector_store.index_chunks(chunks)
        
        logger.info(f"Indexed document {document.doc_id} with {len(chunks)} chunks")
    
    async def search_relevant_context(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search for relevant context given a query"""
        # Check semantic cache first
        query_embedding = self.vector_store.embedding_generator.generate_embedding(query)
        cached_result = await self.semantic_cache.get_cached_result(query, query_embedding)
        
        if cached_result:
            logger.info("Returning cached result")
            return cached_result
        
        # Search in vector store
        results = await self.vector_store.search(query, limit=limit)
        
        # Cache the result
        await self.semantic_cache.cache_result(query, results)
        
        return results
    
    def format_context(self, search_results: List[SearchResult]) -> str:
        """Format search results into context string for LLM"""
        if not search_results:
            return "No relevant context found."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"Context {i} (score: {result.score:.3f}):\n{result.chunk.content}\n"
            )
        
        return "\n".join(context_parts)