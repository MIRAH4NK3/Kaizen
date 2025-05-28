#!/bin/bash

# 🚀 Kaizen Voice Recorder - Quick Setup Script
# This script helps prepare your app for deployment

echo "🎤 Kaizen Voice Recorder - Deployment Preparation"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo ""
print_info "This script will help you prepare for deployment..."
echo ""

# Check if we're in the right directory
if [ ! -f "backend/server.py" ] || [ ! -f "frontend/package.json" ]; then
    print_error "Please run this script from the app root directory"
    exit 1
fi

print_status "Found backend and frontend directories"

# Step 1: Environment Variables Check
echo ""
echo "📋 Step 1: Environment Variables Check"
echo "======================================"

if [ -f "backend/.env" ]; then
    print_status "Backend .env file exists"
    
    # Check for required AWS variables
    if grep -q "AWS_ACCESS_KEY_ID" backend/.env && grep -q "AWS_SECRET_ACCESS_KEY" backend/.env; then
        print_status "AWS credentials found in backend/.env"
    else
        print_warning "AWS credentials missing in backend/.env"
    fi
else
    print_error "Backend .env file missing"
fi

if [ -f "frontend/.env" ]; then
    print_status "Frontend .env file exists"
else
    print_warning "Frontend .env file missing - you'll need to set REACT_APP_BACKEND_URL for deployment"
fi

# Step 2: Dependencies Check
echo ""
echo "📦 Step 2: Dependencies Check"
echo "============================="

print_info "Checking Python dependencies..."
if [ -f "backend/requirements.txt" ]; then
    print_status "requirements.txt found ($(wc -l < backend/requirements.txt) packages)"
else
    print_error "requirements.txt missing"
fi

print_info "Checking Node.js dependencies..."
cd frontend
if [ -f "package.json" ]; then
    print_status "package.json found"
    if [ -d "node_modules" ]; then
        print_status "node_modules directory exists"
    else
        print_warning "node_modules not found - run 'yarn install' in frontend directory"
    fi
else
    print_error "package.json missing"
fi
cd ..

# Step 3: Build Test
echo ""
echo "🔨 Step 3: Build Test"
echo "===================="

print_info "Testing frontend build..."
cd frontend
if npm run build > /dev/null 2>&1; then
    print_status "Frontend builds successfully"
    rm -rf build  # Clean up test build
else
    print_error "Frontend build failed - check for errors"
fi
cd ..

# Step 4: Git Repository Setup
echo ""
echo "📚 Step 4: Git Repository Setup"
echo "==============================="

if [ -d ".git" ]; then
    print_status "Git repository already initialized"
    
    # Check if there are uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "You have uncommitted changes"
        echo "  Run: git add . && git commit -m 'Deploy Kaizen Voice Recorder'"
    else
        print_status "No uncommitted changes"
    fi
    
    # Check if remote is set
    if git remote -v | grep -q origin; then
        print_status "Git remote 'origin' is configured"
        echo "  Remote: $(git remote get-url origin)"
    else
        print_warning "No git remote configured"
        echo "  You'll need to add a remote: git remote add origin <your-repo-url>"
    fi
else
    print_warning "Git repository not initialized"
    echo "  Run: git init"
fi

# Step 5: Generate Deployment Files
echo ""
echo "📝 Step 5: Generate Deployment Files"
echo "===================================="

# Create netlify.toml for frontend
if [ ! -f "netlify.toml" ]; then
    cat > netlify.toml << EOF
[build]
  base = "frontend"
  publish = "frontend/build"
  command = "npm run build"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/api/*"
  to = "https://your-backend-url.railway.app/api/:splat"
  status = 200

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
EOF
    print_status "Created netlify.toml for Netlify deployment"
else
    print_status "netlify.toml already exists"
fi

# Create railway.toml for backend
if [ ! -f "railway.toml" ]; then
    cat > railway.toml << EOF
[build]
  builder = "nixpacks"

[deploy]
  startCommand = "uvicorn server:app --host 0.0.0.0 --port \$PORT"
  healthcheckPath = "/api/health"
  healthcheckTimeout = 300
  restartPolicyType = "on_failure"
EOF
    print_status "Created railway.toml for Railway deployment"
else
    print_status "railway.toml already exists"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << EOF
# Environment files
.env
*.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/

# Build outputs
frontend/build/
frontend/dist/

# Logs
*.log
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.coverage
.pytest_cache/

# Temporary files
*.tmp
*.temp
EOF
    print_status "Created .gitignore file"
else
    print_status ".gitignore already exists"
fi

# Step 6: Deployment Checklist
echo ""
echo "📋 Step 6: Deployment Checklist"
echo "==============================="

echo ""
print_info "REQUIRED FOR DEPLOYMENT:"
echo "  🏗️  MongoDB Atlas account → https://www.mongodb.com/cloud/atlas/register"
echo "  🚂 Railway account → https://railway.app/"
echo "  🌐 Netlify account → https://netlify.com/"
echo "  📁 GitHub repository with your code"

echo ""
print_info "DEPLOYMENT STEPS:"
echo "  1. Create MongoDB Atlas cluster (FREE)"
echo "  2. Push code to GitHub"
echo "  3. Deploy backend on Railway"
echo "  4. Deploy frontend on Netlify"
echo "  5. Update environment variables"
echo "  6. Test the deployment"

echo ""
print_info "HELPFUL LINKS:"
echo "  📖 Full Guide: ./DEPLOYMENT_GUIDE.md"
echo "  🔧 Railway Docs: https://docs.railway.app/"
echo "  🌐 Netlify Docs: https://docs.netlify.com/"

echo ""
print_status "Setup preparation complete!"
print_info "Next: Follow the DEPLOYMENT_GUIDE.md for detailed deployment steps"

# Step 7: Create environment template
echo ""
echo "📄 Step 7: Environment Template"
echo "==============================="

if [ ! -f ".env.template" ]; then
    cat > .env.template << EOF
# Backend Environment Variables (.env)
# Copy this to backend/.env and fill in your values

MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/kaizen_tracker?retryWrites=true&w=majority
DB_NAME=kaizen_tracker

# AWS Configuration (Already configured)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=eu-central-1
S3_BUCKET_NAME=kaizen-voice-recordings

# Frontend Environment Variables (frontend/.env)
# Update with your deployed backend URL
REACT_APP_BACKEND_URL=https://your-backend-url.railway.app
EOF
    print_status "Created .env.template for reference"
else
    print_status ".env.template already exists"
fi

echo ""
echo "🎉 All done! Your Kaizen Voice Recorder is ready for deployment!"
echo "   Follow the DEPLOYMENT_GUIDE.md for step-by-step instructions."
echo ""