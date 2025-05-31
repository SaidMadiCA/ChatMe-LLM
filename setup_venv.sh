#!/bin/bash

# Create a virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy example environment file if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env to add your API keys"
fi

echo ""
echo "Setup complete! Virtual environment is created and activated."
echo ""
echo "To activate the virtual environment in the future, run:"
echo "source venv/bin/activate"
echo ""
echo "To run the application with Gradio UI:"
echo "python main.py"
echo ""
echo "Or to run with just FastAPI (without Gradio):"
echo "uvicorn main:app --reload"
echo ""