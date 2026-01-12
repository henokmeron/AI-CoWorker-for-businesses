# Fly.io Secrets Setup Script
# Run this to set all required environment variables for your Fly.io deployment

Write-Host "🚀 Setting up Fly.io secrets for ai-coworker-for-businesses..." -ForegroundColor Green
Write-Host ""

# REQUIRED SECRETS - App won't start without these
Write-Host "Setting REQUIRED secrets..." -ForegroundColor Yellow

# OPENAI_API_KEY - YOU MUST PROVIDE YOUR ACTUAL KEY
$OPENAI_KEY = Read-Host "Enter your OpenAI API Key (starts with sk-)"
if ($OPENAI_KEY) {
    flyctl secrets set "OPENAI_API_KEY=$OPENAI_KEY" -a ai-coworker-for-businesses
    Write-Host "✅ OPENAI_API_KEY set" -ForegroundColor Green
} else {
    Write-Host "❌ OPENAI_API_KEY not provided - app will not start!" -ForegroundColor Red
}

# API_KEY
flyctl secrets set "API_KEY=ai-coworker-secret-key-2024" -a ai-coworker-for-businesses
Write-Host "✅ API_KEY set" -ForegroundColor Green

# SECRET_KEY
flyctl secrets set "SECRET_KEY=your-super-secret-key-change-this-in-production-2024" -a ai-coworker-for-businesses
Write-Host "✅ SECRET_KEY set" -ForegroundColor Green

# RECOMMENDED SECRETS
Write-Host ""
Write-Host "Setting RECOMMENDED secrets..." -ForegroundColor Yellow

flyctl secrets set "CHROMA_PERSIST_DIR=/app/data/chromadb" -a ai-coworker-for-businesses
Write-Host "✅ CHROMA_PERSIST_DIR set" -ForegroundColor Green

flyctl secrets set "DATA_DIR=/app/data" -a ai-coworker-for-businesses
Write-Host "✅ DATA_DIR set" -ForegroundColor Green

flyctl secrets set "UPLOAD_DIR=/app/data/businesses" -a ai-coworker-for-businesses
Write-Host "✅ UPLOAD_DIR set" -ForegroundColor Green

flyctl secrets set "VECTOR_DB_TYPE=chromadb" -a ai-coworker-for-businesses
Write-Host "✅ VECTOR_DB_TYPE set" -ForegroundColor Green

Write-Host ""
Write-Host "✅ All secrets set!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Verify secrets: flyctl secrets list -a ai-coworker-for-businesses" -ForegroundColor White
Write-Host "2. Deploy/Restart: flyctl apps restart -a ai-coworker-for-businesses" -ForegroundColor White
Write-Host "3. Check logs: flyctl logs -a ai-coworker-for-businesses" -ForegroundColor White
