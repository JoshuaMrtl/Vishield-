Write-Host "Recherche de ffmpeg..." -ForegroundColor Cyan

# Cherche ffmpeg.exe dans le dossier WinGet
$ffmpegExe = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" `
    -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($null -eq $ffmpegExe) {
    Write-Host "ffmpeg.exe introuvable. Assure-toi qu'il est bien installe avec la commande : winget install ffmpeg --source winget" -ForegroundColor Red
    exit 1
}

$ffmpegBinPath = $ffmpegExe.DirectoryName
Write-Host "ffmpeg trouve : $ffmpegBinPath" -ForegroundColor Green

# Verifie si le chemin est deja dans le PATH
$currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")

if ($currentPath -like "*$ffmpegBinPath*") {
    Write-Host "Le chemin est deja dans le PATH, rien a faire." -ForegroundColor Yellow
} else {
    # Ajoute au PATH utilisateur de facon permanente
    [System.Environment]::SetEnvironmentVariable(
        "Path",
        $currentPath + ";$ffmpegBinPath",
        "User"
    )
    Write-Host "Chemin ajoute au PATH avec succes !" -ForegroundColor Green
}

# Recharge le PATH dans la session courante
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "Machine")

# Verification finale
Write-Host "`nVerification..." -ForegroundColor Cyan
ffmpeg -version | Select-Object -First 1

Write-Host "`nTermine ! ffmpeg est pret a l'emploi." -ForegroundColor Green