<#
PowerShell helper to update repository: pull, run optional tests, commit, tag, and push.

Usage examples:
  # Dry run (shows actions)
  .\scripts\update_repo.ps1 -Message "Update docs" -DryRun

  # Real run, commit changes and push
  .\scripts\update_repo.ps1 -Message "v2.0: minor fixes" -Tag v2.0.1

  # Run tests before commit (optional)
  .\scripts\update_repo.ps1 -Message "Tests + docs" -RunTests

Parameters:
  -Message <string> Commit message (required for committing changes)
  -Tag <string> Optional git tag to create and push
  -RunTests Switch to run local test harness (scripts/run_test.py) before commit
  -DryRun Switch: do not actually run git commands; just show them
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Message,
    [string]$Tag = "",
    [switch]$RunTests,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
function Exec { param($cmd) if ($DryRun) { Write-Host "DRYRUN: $cmd" -ForegroundColor Yellow } else { Invoke-Expression $cmd } }

Write-Host "== Update Repo Script ==" -ForegroundColor Cyan

# 1. Ensure .git exists
if (-not (Test-Path -Path .git)) { Write-Error "No se encontró un repositorio git en la carpeta actual."; exit 1 }

# 2. Detect current branch
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "Current branch: $currentBranch"

# 3. Fetch and pull latest
Exec "git fetch origin"
Exec "git pull origin $currentBranch"

# 4. Optional: Run tests
if ($RunTests) {
    Write-Host "Running tests (scripts/run_test.py)" -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "DRYRUN: python scripts/run_test.py --video tests/test_videos/fall_sample_01.mp4 --output test_outputs"
    } else {
        python scripts/run_test.py --video tests/test_videos/fall_sample_01.mp4 --output test_outputs
        if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed (exit code $LASTEXITCODE). Aborting commit."; exit $LASTEXITCODE }
    }
}

# 5. Add & commit
# Check if there are changes
$changes = git status --porcelain
if (-not $changes) {
    Write-Host "No hay cambios para commitear." -ForegroundColor Green
} else {
    Exec "git add -A"
    Exec "git commit -m \"$Message\""
}

# 6. Tag if requested
if ($Tag -ne "") {
    Exec "git tag -a $Tag -m \"$Message\""
}

# 7. Push branch and tags
Exec "git push origin $currentBranch"
if ($Tag -ne "") { Exec "git push origin $Tag" }

Write-Host "== Done ==" -ForegroundColor Green
