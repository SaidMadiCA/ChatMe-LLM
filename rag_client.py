import requests
import json
from typing import Dict, Any, List
import argparse

def rag_query(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Send a RAG query to the API and get the response with sources
    
    Args:
        query (str): The question to ask
        top_k (int): Number of context passages to retrieve
    
    Returns:
        Dict[str, Any]: The API's response with answer and sources
    """
    url = "http://localhost:8000/rag/query"
    payload = {
        "query": query,
        "top_k": top_k
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {"error": "Error communicating with the API"}

def print_sources(sources: List[Dict[str, Any]]):
    """Print the sources in a readable format"""
    print("\nSources:")
    print("-" * 50)
    for i, source in enumerate(sources, 1):
        print(f"Source {i}:")
        print(f"  From: {source.get('source', 'Unknown')}")
        content = source.get('content', '')
        # Truncate long content for display
        if len(content) > 300:
            content = content[:297] + "..."
        print(f"  Content: {content}")
        print(f"  Score: {source.get('score', 'N/A')}")
        print("-" * 50)

def interactive_mode():
    """Run an interactive RAG query session"""
    print("RAG Query System. Type 'exit' to quit.")
    print("-" * 50)
    
    while True:
        query = input("\nQuestion: ")
        if query.lower() == 'exit':
            break
        
        result = rag_query(query)
        
        if "answer" in result:
            print(f"\nAnswer: {result['answer']}")
            if "sources" in result:
                print_sources(result["sources"])
        else:
            print(f"\nError: {result.get('error', 'Unknown error')}")

def main():
    parser = argparse.ArgumentParser(description="RAG Client")
    parser.add_argument("--query", type=str, help="Single query to run")
    parser.add_argument("--top_k", type=int, default=3, help="Number of sources to retrieve")
    
    args = parser.parse_args()
    
    if args.query:
        # Single query mode
        result = rag_query(args.query, args.top_k)
        if "answer" in result:
            print(f"Answer: {result['answer']}")
            if "sources" in result:
                print_sources(result["sources"])
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        # Interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()