# ParikshaMitra — One-click WSL deploy launcher
# Right-click -> "Run with PowerShell"

Write-Host ""
Write-Host "  ParikshaMitra Deployment Launcher" -ForegroundColor Cyan
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host ""

$winSrc = "C:\Users\Georgian\OneDrive\Desktop\ParikshaMitra\deploy-auto.sh"
$wslSrc = "/mnt/c/Users/Georgian/OneDrive/Desktop/ParikshaMitra/deploy-auto.sh"
$wslTmp = "/tmp/pm-deploy.sh"

Write-Host "  Copying script to WSL temp (fixes CRLF on OneDrive mount)..." -ForegroundColor White

# Copy to /tmp on WSL's own Linux filesystem, strip CRLF there, then run
wsl bash -c "cp '$wslSrc' '$wslTmp' && sed -i 's/\r//' '$wslTmp' && chmod +x '$wslTmp' && bash '$wslTmp'"

Write-Host ""
Write-Host "  Done! Press any key to close." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
