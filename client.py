import requests
import json

def chat_with_api(message, history=None):
    """
    Send a chat message to the API and get the response
    
    Args:
        message (str): The user's message
        history (list, optional): Chat history
    
    Returns:
        str: The API's response
    """
    if history is None:
        history = []
    
    url = "http://localhost:8000/chat"
    payload = {
        "message": message,
        "history": history
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()["response"]
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return "Error communicating with the API"

if __name__ == "__main__":
    print("Chat with Said Madi. Type 'exit' to quit.")
    print("-" * 50)
    
    chat_history = []
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        
        # Format history for the API
        formatted_history = []
        for i in range(0, len(chat_history), 2):
            if i < len(chat_history):
                formatted_history.append({"role": "user", "content": chat_history[i]})
            if i+1 < len(chat_history):
                formatted_history.append({"role": "assistant", "content": chat_history[i+1]})
        
        response = chat_with_api(user_input, formatted_history)
        print(f"\nSaid: {response}")
        
        # Update history
        chat_history.append(user_input)
        chat_history.append(response)