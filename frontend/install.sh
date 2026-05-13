#!/bin/bash
# Frontend Dependency Installation Script

echo "================================"
echo "API Optimizer - Frontend Setup"
echo "================================"
echo ""

# Check Node.js installation
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js $NODE_VERSION found"
echo ""

# Check npm installation
echo "Checking npm..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "✅ npm $NPM_VERSION found"
echo ""

# Navigate to frontend directory
echo "Navigating to frontend directory..."
cd "$(dirname "$0")" || exit 1
echo "✅ Current directory: $(pwd)"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
echo ""

npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "================================"
    echo "Setup Complete!"
    echo "================================"
    echo ""
    echo "To start the development server, run:"
    echo "  npm run dev"
    echo ""
    echo "Frontend will be available at:"
    echo "  http://localhost:3000"
    echo ""
    echo "Make sure the backend is running at:"
    echo "  http://localhost:8000"
    echo ""
else
    echo ""
    echo "❌ Failed to install dependencies"
    echo "Please check the error message above"
    exit 1
fi
