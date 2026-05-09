
#!/bin/bash
# Make sure Python environment is ready
export PYTHONUNBUFFERED=1

# Run the Autoblog workflow
# Check for virtual environment
if [ -d "venv" ]; then
    echo "Using virtual environment..."
    venv/bin/python main.py "$@"
else
    echo "Using system python..."
    python main.py "$@"
fi

