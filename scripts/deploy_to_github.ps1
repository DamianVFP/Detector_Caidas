#!/usr/bin/env pwsh
<#
Script para publicar Vigilante Digital v2.0 a GitHub

Uso:
    .\scripts\deploy_to_github.ps1 -Message "Release v2.0: EventLogger optimization"

Requisitos:
    - Git instalado y configurado
    - Credenciales de GitHub configuradas (PAT o SSH)
    - Cambios en main.py, config.py, outputs/event_logger.py, etc. NO commiteados

Flujo:
    1. Commit de cambios v2.0
    2. Tag de versión
    3. Push a origin (main branch + tags)
    4. Listar cambios
#>

param(
    [string]$Message = "Release v2.0: EventLogger optimization + 99% reduction in Firestore writes",
    [string]$Tag = "v2.0.0",
    [switch]$DryRun = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host @"
Script para publicar VigilanteDigital v2.0 a GitHub

Opciones:
    -Message <string>   Mensaje de commit (default: Release v2.0: ...)
    -Tag <string>       Etiqueta de versión (default: v2.0.0)
    -DryRun            Simulación sin cambios reales
    -Help               Mostrar esta ayuda

Ejemplos:
    .\scripts\deploy_to_github.ps1
    .\scripts\deploy_to_github.ps1 -Tag v2.0.1 -DryRun
    .\scripts\deploy_to_github.ps1 -Message "Fix: EventLogger state machine" -Tag v2.0.1
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# Colores para output
$ColorSuccess = 'Green'
$ColorError = 'Red'
$ColorWarning = 'Yellow'
$ColorInfo = 'Cyan'

function Write-Header {
    param([string]$Text)
    Write-Host "`n$('='*70)" -ForegroundColor $ColorInfo
    Write-Host $Text -ForegroundColor $ColorInfo
    Write-Host "=$('='*68)" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor $ColorSuccess
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor $ColorError
}

function Write-Warning-Custom {
    param([string]$Text)
    Write-Host "⚠ $Text" -ForegroundColor $ColorWarning
}

try {
    Write-Header "Publicando VigilanteDigital v2.0 a GitHub"
    Write-Host "Directorio: $(Get-Location)" -ForegroundColor $ColorInfo
    Write-Host "Mensaje: $Message" -ForegroundColor $ColorInfo
    Write-Host "Tag: $Tag" -ForegroundColor $ColorInfo
    Write-Host "Modo: $(if ($DryRun) { 'DRY RUN (sin cambios)' } else { 'EJECUCIÓN REAL' })" -ForegroundColor $(if ($DryRun) { $ColorWarning } else { $ColorSuccess })

    # 1. Verificar que estamos en un repo git
    Write-Host "`n1. Verificando repositorio git..." -ForegroundColor $ColorInfo
    if (!(Test-Path ".git")) {
        throw "No es un repositorio git (no existe .git/)"
    }
    Write-Success "Repositorio git encontrado"

    # 2. Verificar cambios no commiteados
    Write-Host "`n2. Verificando cambios..." -ForegroundColor $ColorInfo
    $status = git status --short
    if (-not $status) {
        Write-Warning-Custom "No hay cambios para commitear"
        $proceed = Read-Host "¿Continuar de todas formas? (s/N)"
        if ($proceed -ne 's') {
            Write-Host "Operación cancelada"
            exit 0
        }
    } else {
        Write-Host "Cambios detectados:" -ForegroundColor $ColorInfo
        Write-Host $status
    }

    # 3. Verificar rama (debería ser main o master)
    Write-Host "`n3. Verificando rama..." -ForegroundColor $ColorInfo
    $currentBranch = git rev-parse --abbrev-ref HEAD
    Write-Host "Rama actual: $currentBranch" -ForegroundColor $ColorInfo
    if ($currentBranch -notlike "*main*" -and $currentBranch -notlike "*master*") {
        Write-Warning-Custom "Estás en rama '$currentBranch' (no main/master)"
        $proceed = Read-Host "¿Continuar de todas formas? (s/N)"
        if ($proceed -ne 's') {
            exit 0
        }
    }

    # 4. Ver archivos que serían commiteados
    Write-Host "`n4. Archivos a commitear:" -ForegroundColor $ColorInfo
    $files = git diff --name-only --cached
    if (-not $files) {
        $files = git diff --name-only
    }
    if ($files) {
        foreach ($file in $files) {
            Write-Host "  • $file"
        }
    } else {
        Write-Host "  (ninguno en staging, se commiteará todo)" -ForegroundColor $ColorWarning
    }

    if ($DryRun) {
        Write-Host "`n5. DRY RUN - Simulando operaciones..." -ForegroundColor $ColorWarning
        Write-Host "  git add -A" -ForegroundColor $ColorInfo
        Write-Host "  git commit -m `"$Message`"" -ForegroundColor $ColorInfo
        Write-Host "  git tag -a $Tag -m `"$Message`"" -ForegroundColor $ColorInfo
        Write-Host "  git push origin $currentBranch" -ForegroundColor $ColorInfo
        Write-Host "  git push origin $Tag" -ForegroundColor $ColorInfo
        Write-Success "DRY RUN completado sin cambios reales"
        Write-Host "`nPara ejecutar REALMENTE, usa: .\scripts\deploy_to_github.ps1 -Message `"..`" (sin -DryRun)" -ForegroundColor $ColorWarning
        exit 0
    }

    # 5. COMMIT
    Write-Host "`n5. Commiteando cambios..." -ForegroundColor $ColorInfo
    & git add -A
    & git commit -m $Message
    Write-Success "Cambios commiteados"

    # 6. TAG
    Write-Host "`n6. Creando tag..." -ForegroundColor $ColorInfo
    & git tag -a $Tag -m $Message
    Write-Success "Tag '$Tag' creado"

    # 7. PUSH
    Write-Host "`n7. Publicando a GitHub..." -ForegroundColor $ColorInfo
    & git push origin $currentBranch
    Write-Success "Branch publicado"
    
    & git push origin $Tag
    Write-Success "Tag publicado"

    # 8. Resumen
    Write-Header "Publicación Completada ✓"
    Write-Host "Versión: $Tag" -ForegroundColor $ColorSuccess
    Write-Host "Mensaje: $Message" -ForegroundColor $ColorSuccess
    Write-Host "`nVerifica en GitHub: https://github.com/tu_usuario/VigilanteDigital/releases/tag/$Tag" -ForegroundColor $ColorInfo
    Write-Host ""

} catch {
    Write-Error-Custom "Error: $_"
    Write-Host "Stacktrace: $($_.ScriptStackTrace)" -ForegroundColor $ColorError
    exit 1
}
