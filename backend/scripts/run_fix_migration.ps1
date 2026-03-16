# Run this script to add account_label column using DATABASE_URL from .env
# Usage: .\scripts\run_fix_migration.ps1

$envPath = Join-Path $PSScriptRoot ".." ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "ERROR: .env not found. Create backend\.env with DATABASE_URL"
    exit 1
}

$content = Get-Content $envPath -Raw
if ($content -match 'DATABASE_URL=(.+)') {
    $url = $matches[1].Trim().Trim('"').Trim("'")
} else {
    Write-Host "ERROR: DATABASE_URL not found in .env"
    exit 1
}

# Extract connection params from URL (postgresql://user:pass@host:port/db)
if ($url -match 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
    $user = $matches[1]
    $pass = $matches[2]
    $host = $matches[3]
    $port = $matches[4]
    $db = $matches[5] -replace '\?.*$',''
    $env:PGPASSWORD = $pass
    $sqlFile = Join-Path $PSScriptRoot "fix_add_account_label.sql"
    Write-Host "Running migration on $db..."
    psql -h $host -p $port -U $user -d $db -f $sqlFile
} else {
    Write-Host "Could not parse DATABASE_URL. Run the SQL manually:"
    Get-Content (Join-Path $PSScriptRoot "fix_add_account_label.sql")
}
