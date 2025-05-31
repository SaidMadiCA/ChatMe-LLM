from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from pypdf import PdfReader
import uvicorn
from typing import Optional

# Load environment variables
load_dotenv(override=True)

app = FastAPI(title="Personal Chat API", description="API for chatting with me using GPT-4o-mini")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserDetails(BaseModel):
    email: EmailStr
    name: str = Field(default="Name not provided")
    notes: str = Field(default="not provided")

class Question(BaseModel):
    question: str

class ChatMessage(BaseModel):
    message: str
    history: list = []

class ChatResponse(BaseModel):
    response: str

# Push notification function
def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

# Tool functions
def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

# Tool definitions
record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

class Me:
    def __init__(self):
        self.openai = OpenAI()
        self.name = "Said Madi"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history=None):
        if history is None:
            history = []
            
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content

# Initialize Me class
me = Me()

# API Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    response = me.chat(chat_message.message, chat_message.history)
    return {"response": response}

@app.post("/record-details")
async def record_details_endpoint(user_details: UserDetails, background_tasks: BackgroundTasks):
    background_tasks.add_task(record_user_details, user_details.email, user_details.name, user_details.notes)
    return {"status": "success", "message": "User details recorded"}

@app.post("/record-question")
async def record_question_endpoint(question: Question, background_tasks: BackgroundTasks):
    background_tasks.add_task(record_unknown_question, question.question)
    return {"status": "success", "message": "Question recorded"}

@app.get("/")
async def root():
    return {"message": f"Welcome to {me.name}'s chat API"}

# For standalone execution with Gradio UI
if __name__ == "__main__":
    import gradio as gr
    
    # Define Gradio interface using FastAPI backend
    with gr.Blocks(title=f"Chat with {me.name}") as interface:
        chatbot = gr.Chatbot(type="messages")
        msg = gr.Textbox(label="Message")
        clear = gr.Button("Clear")
        
        def respond(message, chat_history):
            # Format history for API
            formatted_history = []
            for msg in chat_history:
                formatted_history.append(msg)
                
            # Get response
            response = me.chat(message, formatted_history)
            
            # Add to chat history in messages format
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})
            
            return "", chat_history
        
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: None, None, chatbot, queue=False)
        
        # Launch Gradio with FastAPI backend
        interface.launch(server_name="0.0.0.0", server_port=8000, share=True)
    
    # If running without Gradio, use Uvicorn to start the FastAPI app
    # uvicorn.run(app, host="0.0.0.0", port=8000)