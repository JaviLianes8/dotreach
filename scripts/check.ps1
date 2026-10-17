# Local quality gate. Run before every commit. No CI runs in the cloud.
# Every step must succeed: the first non-zero exit code stops the gate and is returned.
$ErrorActionPreference = "Stop"

function Step([string]$Name, [scriptblock]$Command) {
    Write-Host "== $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "check failed at: $Name (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

Step "fetch RFC 6901 for the ground truth tests" { python scripts/fetch_upstream.py }
Step "ruff format" { ruff format --check . }
Step "ruff check" { ruff check . }
Step "mypy" { mypy --strict src tests }
Step "pytest" { python -m pytest }
Write-Host "all checks passed"
