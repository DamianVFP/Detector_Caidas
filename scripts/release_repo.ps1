<#
PowerShell convenience script to create a release: bumps tag, creates annotated tag, pushes tag and branch.

Usage:
  .\scripts\release_repo.ps1 -Tag v2.0.0 -Message "Release v2.0.0"

This script assumes you have committed changes already (or use update_repo.ps1 with -Tag).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [Parameter(Mandatory=$true)][string]$Message,
    [switch]$DryRun
)

function Exec { param($cmd) if ($DryRun) { Write-Host "DRYRUN: $cmd" -ForegroundColor Yellow } else { Invoke-Expression $cmd } }

if (-not (Test-Path -Path .git)) { Write-Error "No se encontró un repositorio git en la carpeta actual."; exit 1 }

$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "Creating release tag $Tag on branch $currentBranch"

Exec "git tag -a $Tag -m \"$Message\""
Exec "git push origin $currentBranch"
Exec "git push origin $Tag"

Write-Host "Release $Tag pushed to origin" -ForegroundColor Green
