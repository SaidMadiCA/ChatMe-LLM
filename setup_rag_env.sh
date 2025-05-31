#!/bin/bash

# Create a virtual environment
echo "Creating virtual environment for RAG-enabled app..."
python -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies (including RAG requirements)..."
pip install -r requirements.txt

# Create me/knowledge directory if it doesn't exist
if [ ! -d "me/knowledge" ]; then
    echo "Creating me/knowledge directory for storing documents..."
    mkdir -p me/knowledge
fi

# Copy example environment file if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env to add your API keys"
fi

echo ""
echo "Setup complete! Virtual environment is created and activated."
echo ""
echo "To add documents to your knowledge base, place them in the me/knowledge directory."
echo "Supported formats: PDF and TXT files."
echo ""
echo "To run the RAG-enabled application:"
echo "python main_rag.py"
echo ""
echo "To use the dedicated RAG client:"
echo "python rag_client.py"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "source venv/bin/activate"
echo ""