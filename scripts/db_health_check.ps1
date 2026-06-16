<#
.SYNOPSIS
    EdmontonLens -- Local Database Health Check (PowerShell, Windows + WSL).

.DESCRIPTION
    Checks PostgreSQL (or SQLite fallback), MySQL, and SQL Server.
    For every table in the schema: prints the row count and most recent
    ingested_at timestamp. Flags empty tables ([WARN] EMPTY) and tables whose
    newest row is older than 48 hours ([WARN] STALE).

    Reads connection strings from the environment or the project .env file.

.OUTPUTS
    Exit code 0 if all checks pass, 1 if any warning/failure occurs.
#>

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$EnvFile   = Join-Path $RootDir '.env'

$Tables = @(
    'transit_routes',
    'transit_stops',
    'transit_performance',
    'transit_stop_delays',
    'parks',
    'waste_schedules',
    'neighbourhoods',
    'neighbourhood_kpis',
    'delay_predictions'
)

$StaleHours = 48
$ExitCode   = 0

function Get-EnvVar {
    param([string]$Name)
    $val = [System.Environment]::GetEnvironmentVariable($Name)
    if (-not $val -and (Test-Path $EnvFile)) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^${Name}=" } | Select-Object -First 1
        if ($line) { $val = ($line -split '=', 2)[1] }
    }
    return $val
}

$DatabaseUrl        = Get-EnvVar 'DATABASE_URL'
if (-not $DatabaseUrl) { $DatabaseUrl = 'sqlite:///./data/edmonton_lens.db' }
$MysqlUrl           = Get-EnvVar 'MYSQL_DATABASE_URL'
$SqlServerUrl       = Get-EnvVar 'SQLSERVER_DATABASE_URL'

function Test-Staleness {
    param([string]$Ts)
    if (-not $Ts -or $Ts -eq 'NULL') { return $false }
    $parsed = $null
    if ([DateTime]::TryParse($Ts, [ref]$parsed)) {
        return [math]::Floor(((Get-Date) - $parsed).TotalHours) -gt $StaleHours
    }
    return $false
}

function Write-TableRow {
    param([string]$Table, [string]$Count, [string]$LastTs)
    $status = '[OK]'
    if (-not $Count -or [int]$Count -eq 0) {
        $status = '[WARN] EMPTY'; $script:ExitCode = 1
    } elseif (Test-Staleness $LastTs) {
        $parsed = $null; [DateTime]::TryParse($LastTs, [ref]$parsed) | Out-Null
        $h = [math]::Floor(((Get-Date) - $parsed).TotalHours)
        $status = "[WARN] STALE ($h h)"; $script:ExitCode = 1
    }
    $display = if ($LastTs) { $LastTs } else { 'none' }
    '  {0,-22} rows={1,-7} last_ingested={2,-26} {3}' -f $Table, $Count, $display, $status |
        Write-Host
}

# ============================================================================
# PostgreSQL / SQLite
# ============================================================================
Write-Host ''
Write-Host 'EdmontonLens DB Health Check'
Write-Host ('=' * 70)
Write-Host "[PostgreSQL / SQLite]  $(($DatabaseUrl -split '://')[0])://***"
Write-Host ('-' * 70)

function Invoke-PgQuery {
    param([string]$Sql)
    if ($DatabaseUrl.StartsWith('sqlite')) {
        $p = $DatabaseUrl -replace '^sqlite:///', ''
        if ($p.StartsWith('./')) { $p = Join-Path $RootDir ($p.Substring(2)) }
        return (& sqlite3 $p $Sql 2>$null)
    }
    return (& psql $DatabaseUrl -tAc $Sql 2>$null)
}

foreach ($t in $Tables) {
    $c  = (Invoke-PgQuery "SELECT COUNT(*) FROM $t;") -replace '\s',''
    $ts = (Invoke-PgQuery "SELECT MAX(ingested_at) FROM $t;") -replace '\s+$',''
    Write-TableRow $t ($c ?? '0') ($ts ?? '')
}

# ============================================================================
# MySQL
# ============================================================================
Write-Host ''
Write-Host '[MySQL]'
Write-Host ('-' * 70)

if (-not $MysqlUrl) {
    Write-Host '  MYSQL_DATABASE_URL not set -- skipping MySQL checks.'
} else {
    # Parse mysql+pymysql://user:pass@host:port/db
    if ($MysqlUrl -match '://([^:]+):([^@]+)@([^:/]+):?(\d+)?/([^?]+)') {
        $mu = $Matches[1]; $mp = $Matches[2]; $mh = $Matches[3]
        $mport = if ($Matches[4]) { $Matches[4] } else { '3306' }
        $mdb = $Matches[5]
    }
    $mysqlOk = $false
    try {
        & mysql -h $mh -P $mport -u $mu "-p$mp" $mdb -sNe 'SELECT 1' 2>$null | Out-Null
        $mysqlOk = $true
    } catch { }

    if ($mysqlOk) {
        foreach ($t in $Tables) {
            $c  = (& mysql -h $mh -P $mport -u $mu "-p$mp" $mdb -sNe "SELECT COUNT(*) FROM ``$t``;" 2>$null) -replace '\s',''
            $ts = (& mysql -h $mh -P $mport -u $mu "-p$mp" $mdb -sNe "SELECT MAX(ingested_at) FROM ``$t``;" 2>$null) -replace '\s+$',''
            Write-TableRow $t ($c ?? '0') ($ts ?? '')
        }
    } else {
        Write-Host "  Could not connect to MySQL at ${mh}:${mport} -- is docker compose up?"
        $ExitCode = 1
    }
}

# ============================================================================
# SQL Server
# ============================================================================
Write-Host ''
Write-Host '[SQL Server]'
Write-Host ('-' * 70)

if (-not $SqlServerUrl) {
    Write-Host '  SQLSERVER_DATABASE_URL not set -- skipping SQL Server checks.'
} else {
    $ssHost = 'localhost'; $ssPort = '1433'; $ssPass = 'EdmontonLens123!'
    if ($SqlServerUrl -match '@([^:,]+)[,:](\d+)/') {
        $ssHost = $Matches[1]; $ssPort = $Matches[2]
    }
    $ssOk = $false
    try {
        & sqlcmd -S "$ssHost,$ssPort" -U sa -P $ssPass -Q 'SELECT 1' -h -1 2>$null | Out-Null
        $ssOk = $true
    } catch { }

    if ($ssOk) {
        foreach ($t in $Tables) {
            $c  = (& sqlcmd -S "$ssHost,$ssPort" -U sa -P $ssPass -d edmonton_lens `
                   -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM [$t]" -h -1 -W 2>$null |
                   Select-Object -First 1) -replace '\s',''
            $ts = (& sqlcmd -S "$ssHost,$ssPort" -U sa -P $ssPass -d edmonton_lens `
                   -Q "SET NOCOUNT ON; SELECT CONVERT(VARCHAR,MAX(ingested_at),120) FROM [$t]" -h -1 -W 2>$null |
                   Select-Object -First 1) -replace '\s+$',''
            Write-TableRow $t ($c ?? '0') ($ts ?? '')
        }
    } else {
        Write-Host "  Could not connect to SQL Server at ${ssHost}:${ssPort} -- is docker compose up?"
        $ExitCode = 1
    }
}

Write-Host ''
Write-Host ('=' * 70)
if ($ExitCode -eq 0) {
    Write-Host 'All checks passed.'
} else {
    Write-Host 'One or more checks raised warnings.'
}
exit $ExitCode
