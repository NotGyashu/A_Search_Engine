#!/bin/bash
# Setup script for AI Search Engine Backend
# This demonstrates professional project setup practices

echo "🚀 Setting up AI Search Engine Backend Environment"
echo "================================================"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "⚠️  requirements.txt not found. Creating it..."
fi

# Step 1: Create virtual environment if it doesn't exist
if [ ! -d "ai_search_env" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv ai_search_env
    echo "✅ Virtual environment created: ai_search_env/"
else
    echo "✅ Virtual environment already exists"
fi

# Step 2: Activate virtual environment and install packages
echo "🔧 Activating virtual environment and installing packages..."

# Use absolute path to ensure we find the right python/pip
ENV_PATH="$(pwd)/ai_search_env"
PYTHON_PATH="$ENV_PATH/bin/python"
PIP_PATH="$ENV_PATH/bin/pip"

# Activate and install
source ai_search_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
$PIP_PATH install --upgrade pip

# Step 3: Install required packages
echo "📚 Installing AI/ML dependencies..."
echo "   - sentence-transformers (for embeddings)"
echo "   - faiss-cpu (for vector search)"
echo "   - beautifulsoup4 (for HTML processing)"
echo "   - numpy (for numerical operations)"
echo "   - scikit-learn (for ML utilities)"

$PIP_PATH install sentence-transformers faiss-cpu beautifulsoup4 numpy scikit-learn

# Step 4: Verify installation
echo "🧪 Verifying installation..."
$PYTHON_PATH -c "
import sentence_transformers
import faiss
import bs4
import numpy
import sklearn
print('✅ All packages installed successfully!')
print(f'📍 Python version: {__import__(\"sys\").version.split()[0]}')
print(f'📍 Virtual env: {__import__(\"sys\").prefix}')
"

echo ""
echo "🎉 Setup complete! To activate this environment in the future:"
echo "   source ai_search_env/bin/activate"
echo ""
echo "💡 This setup demonstrates:"
echo "   - Virtual environment management"
echo "   - Dependency isolation"
echo "   - Reproducible development environments"
echo "   - Professional Python project structure"
