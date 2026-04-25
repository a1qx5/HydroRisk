# HydroRisk Git Helper Script
# Save this as: git-sync.ps1
# Usage: .\git-sync.ps1

Write-Host "🔄 Syncing HydroRisk with remote..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Fetch latest
Write-Host "1️⃣  Fetching latest from remote..." -ForegroundColor Yellow
git fetch HydroRisk

# Step 2: Check if diverged
$ahead = (git rev-list --count "HydroRisk/master..HEAD" 2>$null | Where-Object {$_ -match '\d+'}) -replace '\D+', ''
$behind = (git rev-list --count "HEAD..HydroRisk/master" 2>$null | Where-Object {$_ -match '\d+'}) -replace '\D+', ''

if ([string]::IsNullOrWhiteSpace($ahead)) { $ahead = 0 }
if ([string]::IsNullOrWhiteSpace($behind)) { $behind = 0 }

Write-Host ""
Write-Host "📊 Branch Status:"
Write-Host "   Ahead:  $ahead commit(s)"
Write-Host "   Behind: $behind commit(s)"
Write-Host ""

if ($ahead -gt 0 -and $behind -gt 0) {
    Write-Host "⚠️  DIVERGED! Rebasing..." -ForegroundColor Red
    git pull --rebase HydroRisk master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Rebase failed. Fix conflicts and run: git rebase --continue" -ForegroundColor Red
        exit 1
    }
} elseif ($behind -gt 0) {
    Write-Host "📥 Pulling remote updates..." -ForegroundColor Yellow
    git pull HydroRisk master
} else {
    Write-Host "✅ Already up to date!" -ForegroundColor Green
}

# Step 3: Push if ahead
$ahead = (git rev-list --count "HydroRisk/master..HEAD" 2>$null | Where-Object {$_ -match '\d+'}) -replace '\D+', ''
if ([string]::IsNullOrWhiteSpace($ahead)) { $ahead = 0 }

if ($ahead -gt 0) {
    Write-Host ""
    Write-Host "📤 Pushing $ahead commit(s) to remote..." -ForegroundColor Cyan
    git push HydroRisk master
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Push successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Push failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✨ All done!" -ForegroundColor Green

