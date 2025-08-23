"""
LLM1 Agent - User interface with RAG memory integration
Handles user interactions and provides context-aware responses using RAG system
"""
import logging
from typing import List, Dict, Optional, Any
import uuid
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from shared.config import config
from shared.llm_providers import LLMProviderManager, LLMProvider
from shared.rag_system import RAGSystem, Document, SearchResult

logger = logging.getLogger(__name__)


class UserQuery(BaseModel):
    message: str
    session_id: Optional[str] = None
    include_context: bool = True
    max_context_results: int = 5


class AgentResponse(BaseModel):
    response: str
    session_id: str
    context_used: List[Dict[str, Any]]
    provider_used: str
    model_used: str


@dataclass
class ConversationSession:
    session_id: str
    messages: List[Dict[str, str]]
    context_history: List[SearchResult]


class LLM1Agent:
    """LLM1 Agent with RAG integration"""
    
    def __init__(self):
        self.llm_manager = LLMProviderManager()
        self.rag_system = RAGSystem()
        self.sessions: Dict[str, ConversationSession] = {}
        self.app = FastAPI(title="LLM1 Agent API", version="1.0.0")
        self._setup_routes()
    
    async def initialize(self):
        """Initialize all components"""
        await self.rag_system.initialize()
        logger.info("LLM1 Agent initialized")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.rag_system.shutdown()
        logger.info("LLM1 Agent shutdown")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/chat", response_model=AgentResponse)
        async def chat(query: UserQuery):
            return await self.process_user_query(query)
        
        @self.app.post("/index_document")
        async def index_document(doc_data: Dict[str, Any]):
            """Index a document in the RAG system"""
            try:
                document = Document(
                    content=doc_data["content"],
                    metadata=doc_data.get("metadata", {}),
                    doc_id=doc_data.get("doc_id", str(uuid.uuid4()))
                )
                await self.rag_system.index_document(document)
                return {"status": "success", "doc_id": document.doc_id}
            except Exception as e:
                logger.error(f"Failed to index document: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                # Check RAG system components
                rag_healthy = True  # Simplified check
                
                # Check LLM providers
                provider_health = await self.llm_manager.health_check_all()
                
                return {
                    "status": "healthy",
                    "rag_system": rag_healthy,
                    "llm_providers": provider_health
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=500, detail="Health check failed")
        
        @self.app.get("/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get conversation session"""
            if session_id not in self.sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.sessions[session_id]
            return {
                "session_id": session.session_id,
                "message_count": len(session.messages),
                "messages": session.messages[-10:]  # Return last 10 messages
            }
    
    def _get_or_create_session(self, session_id: Optional[str]) -> ConversationSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        new_session_id = session_id or str(uuid.uuid4())
        session = ConversationSession(
            session_id=new_session_id,
            messages=[],
            context_history=[]
        )
        self.sessions[new_session_id] = session
        return session
    
    def _build_context_prompt(self, user_message: str, search_results: List[SearchResult]) -> str:
        """Build prompt with context from RAG system"""
        
        if not search_results:
            return f"""You are LLM1, the user interface agent for the ATLAS multi-agent system.
            
User message: {user_message}

Please provide a helpful response. If you need to create tasks or issues, mention that you can work with LLM2 to handle that."""
        
        context = self.rag_system.format_context(search_results)
        
        return f"""You are LLM1, the user interface agent for the ATLAS multi-agent system.
You have access to relevant context from the knowledge base to help answer the user's query.

Relevant Context:
{context}

User message: {user_message}

Please provide a helpful response based on the context above. If you need to create tasks or issues, mention that you can work with LLM2 to handle that. If the user's query requires actions beyond information retrieval, explain how the system would handle that through other agents."""
    
    async def process_user_query(self, query: UserQuery) -> AgentResponse:
        """Process user query with RAG context"""
        try:
            # Get or create conversation session
            session = self._get_or_create_session(query.session_id)
            
            # Add user message to session
            session.messages.append({"role": "user", "content": query.message})
            
            # Search for relevant context if requested
            search_results = []
            if query.include_context:
                search_results = await self.rag_system.search_relevant_context(
                    query.message, 
                    limit=query.max_context_results
                )
                session.context_history.extend(search_results)
            
            # Build prompt with context
            prompt = self._build_context_prompt(query.message, search_results)
            
            # Generate response using LLM provider
            llm_response = await self.llm_manager.generate(
                prompt,
                preferred_provider=LLMProvider.OPENAI,  # Prefer OpenAI for user interface
                allow_fallback=True,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Add assistant response to session
            session.messages.append({"role": "assistant", "content": llm_response.content})
            
            # Format context for response
            context_data = [
                {
                    "content": result.chunk.content,
                    "score": result.score,
                    "doc_id": result.chunk.doc_id,
                    "chunk_id": result.chunk.chunk_id
                }
                for result in search_results
            ]
            
            return AgentResponse(
                response=llm_response.content,
                session_id=session.session_id,
                context_used=context_data,
                provider_used=llm_response.provider.value,
                model_used=llm_response.model
            )
            
        except Exception as e:
            logger.error(f"Failed to process user query: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
    
    async def run_server(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the FastAPI server"""
        config_obj = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config_obj)
        await server.serve()


# Entry point for running the agent
if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = LLM1Agent()
        await agent.initialize()
        try:
            await agent.run_server()
        finally:
            await agent.shutdown()
    
    asyncio.run(main())