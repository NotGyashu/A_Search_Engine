#!/bin/bash

# Quick deployment script for zero-cost hosting

echo "🚀 Nebula Search Engine - Zero-Cost Deployment"
echo "=============================================="

# Check if required tools are installed
check_requirements() {
    echo "📋 Checking requirements..."
    
    commands=("git" "docker" "npm" "python3")
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            echo "❌ $cmd is not installed. Please install it first."
            exit 1
        fi
    done
    echo "✅ All requirements met!"
}

# Deploy to Docker (Local testing)
deploy_docker() {
    echo "🐳 Deploying with Docker..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        echo "📝 Creating .env file..."
        cat > .env << EOF
GOOGLE_API_KEY=your_google_api_key_here
REACT_APP_BACKEND_URL=http://localhost:8000
DATABASE_PATH=./data/processed/documents.db
AI_RUNNER_URL=http://ai-runner:8001
EOF
        echo "⚠️  Please edit .env file with your actual API keys"
        return 1
    fi
    
    # Build and start services
    docker-compose up --build -d
    
    echo "✅ Services starting..."
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend: http://localhost:8000"
    echo "🤖 AI Runner: http://localhost:8001"
    echo "📚 API Docs: http://localhost:8000/api/docs"
}

# Deploy Frontend to Vercel
deploy_vercel() {
    echo "🌟 Deploying Frontend to Vercel..."
    
    if ! command -v vercel &> /dev/null; then
        echo "📦 Installing Vercel CLI..."
        npm install -g vercel
    fi
    
    cd ai_search/frontend
    npm install
    npm run build
    
    echo "🚀 Deploying to Vercel..."
    vercel --prod
    
    cd ../..
    echo "✅ Frontend deployed to Vercel!"
}

# Deploy Backend to Railway
deploy_railway() {
    echo "🚂 Deploying Backend to Railway..."
    
    if ! command -v railway &> /dev/null; then
        echo "📦 Installing Railway CLI..."
        npm install -g @railway/cli
    fi
    
    echo "🔑 Please login to Railway..."
    railway login
    
    # Deploy backend
    echo "🔧 Deploying Backend service..."
    cd ai_search/backend
    railway init
    railway up
    cd ../..
    
    # Deploy AI runner
    echo "🤖 Deploying AI Runner service..."
    cd ai_search/ai_runner
    railway init
    railway up
    cd ../..
    
    echo "✅ Backend services deployed to Railway!"
}

# Setup GitHub Actions for Crawler
setup_github_actions() {
    echo "⚙️ Setting up GitHub Actions for Crawler..."
    
    if [ ! -d ".git" ]; then
        echo "📁 Initializing Git repository..."
        git init
        git add .
        git commit -m "Initial commit - Nebula Search Engine"
    fi
    
    echo "📝 GitHub Actions workflow already created at .github/workflows/deploy.yml"
    echo "🔑 Please add these secrets to your GitHub repository:"
    echo "   - GOOGLE_API_KEY"
    echo "   - RAILWAY_TOKEN"
    echo ""
    echo "📄 Go to: https://github.com/your-username/your-repo/settings/secrets/actions"
}

# Full deployment
deploy_all() {
    echo "🌟 Full Zero-Cost Deployment"
    echo "============================="
    
    check_requirements
    
    echo ""
    read -p "Deploy Frontend to Vercel? (y/n): " deploy_frontend
    if [ "$deploy_frontend" = "y" ]; then
        deploy_vercel
    fi
    
    echo ""
    read -p "Deploy Backend to Railway? (y/n): " deploy_backend
    if [ "$deploy_backend" = "y" ]; then
        deploy_railway
    fi
    
    echo ""
    read -p "Setup GitHub Actions for Crawler? (y/n): " setup_actions
    if [ "$setup_actions" = "y" ]; then
        setup_github_actions
    fi
    
    echo ""
    echo "🎉 Deployment setup complete!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Update environment variables in your hosting platforms"
    echo "2. Configure your domain (optional)"
    echo "3. Set up monitoring and alerts"
    echo "4. Test the full flow end-to-end"
    echo ""
    echo "🌐 Your search engine should be live!"
}

# Show usage
show_usage() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  docker     - Deploy locally with Docker"
    echo "  vercel     - Deploy frontend to Vercel"
    echo "  railway    - Deploy backend to Railway"
    echo "  github     - Setup GitHub Actions"
    echo "  all        - Full deployment setup"
    echo "  help       - Show this help message"
    echo ""
    echo "Example: $0 docker"
}

# Main script logic
case "$1" in
    "docker")
        check_requirements
        deploy_docker
        ;;
    "vercel")
        check_requirements
        deploy_vercel
        ;;
    "railway")
        check_requirements
        deploy_railway
        ;;
    "github")
        setup_github_actions
        ;;
    "all")
        deploy_all
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    "")
        deploy_all
        ;;
    *)
        echo "❌ Unknown option: $1"
        show_usage
        exit 1
        ;;
esac
