import os
import numpy as np
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pypdf import PdfReader
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import Distance, VectorParams, PointStruct

load_dotenv(override=True)

class RAGSystem:
    def __init__(self, 
                 embedding_model: str = "text-embedding-3-small",
                 chunk_size: int = 500,
                 chunk_overlap: int = 100,
                 collection_name: str = "knowledge_base",
                 local_path: str = "./qdrant_data"):
        """
        Initialize the RAG system with Qdrant vector database
        
        Args:
            embedding_model: OpenAI embedding model to use
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
            collection_name: Name of the Qdrant collection to use
            local_path: Path to store the Qdrant database files
        """
        self.client = OpenAI()
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection_name = collection_name
        
        # Get vector dimension for the model
        # text-embedding-3-small has 1536 dimensions
        self.vector_size = 1536
        
        # Initialize Qdrant client using remote server
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is required but not set")
            
        print(f"Connecting to Qdrant server at {qdrant_url}")
        self.qdrant = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Create collection if it doesn't exist
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create the vector collection if it doesn't already exist"""
        collections = self.qdrant.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if self.collection_name not in collection_names:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            print(f"Created new collection: {self.collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text using OpenAI API"""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        # Clean the text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences (basic approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, store current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap for context continuity
                words = current_chunk.split()
                overlap_word_count = min(len(words), self.chunk_overlap // 4)
                current_chunk = " ".join(words[-overlap_word_count:]) + " "
            
            current_chunk += sentence + " "
        
        # Add the last chunk if not empty
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def add_pdf(self, pdf_path: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Process a PDF document and add its contents to the index
        
        Args:
            pdf_path: Path to the PDF file
            metadata: Optional metadata about the document
            
        Returns:
            Number of chunks indexed
        """
        if metadata is None:
            metadata = {"source": pdf_path}
            
        # Extract text from PDF
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
        
        return self.add_text(text, metadata)
    
    def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Process text and add its contents to the index
        
        Args:
            text: Text to process
            metadata: Optional metadata about the text
            
        Returns:
            Number of chunks indexed
        """
        if metadata is None:
            metadata = {"source": "direct_text"}
            
        # Chunk the text
        chunks = self._chunk_text(text)
        
        # Create points for batch upload
        points = []
        
        # Create and add embeddings for each chunk
        for i, chunk in enumerate(chunks):
            # Create embedding
            embedding = self._get_embedding(chunk)
            
            # Store the document with metadata
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = i
            chunk_metadata["content"] = chunk
            chunk_metadata["created_at"] = time.time()
            
            # Create a unique ID for the vector
            point_id = str(uuid.uuid4())
            
            # Add to batch
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=chunk_metadata
                )
            )
        
        # Batch upload to Qdrant
        if points:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using the query
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Search in Qdrant
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        # Format results
        results = []
        for result in search_results:
            # Extract payload and add score
            doc = result.payload.copy()
            doc["score"] = float(result.score)
            results.append(doc)
                
        return results
    
    def query(self, user_query: str, top_k: int = 3, system_prompt: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Perform RAG query: retrieve relevant context and generate an answer
        
        Args:
            user_query: User's question
            top_k: Number of context chunks to retrieve
            system_prompt: Optional system prompt to use
            
        Returns:
            Generated response and retrieved context
        """
        # Get relevant context
        context_docs = self.search(user_query, top_k=top_k)
        
        # Extract text from context documents
        context_texts = [doc["content"] for doc in context_docs]
        context = "\n\n".join(context_texts)
        
        # Create prompt with context
        if not system_prompt:
            system_prompt = "You are a helpful assistant. Answer the question based only on the provided context."
        
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context}"},
            {"role": "user", "content": user_query}
        ]
        
        # Generate response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        
        return response.choices[0].message.content, context_docs
    
    def get_document_count(self) -> int:
        """Get the number of documents in the collection"""
        collection_info = self.qdrant.get_collection(self.collection_name)
        return collection_info.points_count
    
    def clear_collection(self):
        """Clear all documents from the collection"""
        self.qdrant.delete_collection(self.collection_name)
        self._ensure_collection_exists()
        print(f"Collection {self.collection_name} cleared and recreated")