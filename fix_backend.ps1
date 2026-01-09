# Quick Backend Fix Script for Fly.io
# Run this script to diagnose and fix backend issues

Write-Host "🔍 Checking backend status..." -ForegroundColor Cyan
Write-Host ""

# Check if flyctl is installed
try {
    $flyctlVersion = flyctl version 2>&1
    Write-Host "✅ Fly.io CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Fly.io CLI is not installed!" -ForegroundColor Red
    Write-Host "Install it from: https://fly.io/docs/getting-started/installing-flyctl/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📊 Checking app status..." -ForegroundColor Cyan
flyctl status -a ai-coworker-for-businesses

Write-Host ""
Write-Host "📋 Checking environment variables..." -ForegroundColor Cyan
flyctl secrets list -a ai-coworker-for-businesses

Write-Host ""
Write-Host "📜 Recent logs (last 50 lines)..." -ForegroundColor Cyan
flyctl logs -a ai-coworker-for-businesses --limit 50

Write-Host ""
Write-Host "🔄 Attempting to restart backend..." -ForegroundColor Cyan
flyctl apps restart -a ai-coworker-for-businesses

Write-Host ""
Write-Host "⏳ Waiting 10 seconds for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "🧪 Testing backend health endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://ai-coworker-for-businesses.fly.dev/health" -TimeoutSec 10 -UseBasicParsing
    Write-Host "✅ Backend is now responding! Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Backend is still not responding." -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Check logs: flyctl logs -a ai-coworker-for-businesses" -ForegroundColor White
    Write-Host "2. Check if OPENAI_API_KEY is set: flyctl secrets list -a ai-coworker-for-businesses" -ForegroundColor White
    Write-Host "3. Redeploy: flyctl deploy -a ai-coworker-for-businesses" -ForegroundColor White
}

