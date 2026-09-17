$ErrorActionPreference = 'Stop'
$agencyEnvPath = Join-Path $PSScriptRoot 'sandbox.env'
if (Test-Path $agencyEnvPath) { throw 'sandbox.env already exists; keeping existing values.' }
$agencyRandom = New-Object byte[] 32
$agencyGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $agencyGenerator.GetBytes($agencyRandom) } finally { $agencyGenerator.Dispose() }
$agencyKey = -join ($agencyRandom | ForEach-Object { $_.ToString('x2') })
$agencyTemplate = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'sandbox.env.example'))
$agencyText = $agencyTemplate -replace '(?m)^SECRET_KEY=\s*$', ('SECRET_KEY=' + $agencyKey)
[IO.File]::WriteAllText($agencyEnvPath, $agencyText, (New-Object System.Text.UTF8Encoding($false)))
$agencyKey = $null
$agencyText = $null
Write-Host 'Created local sandbox.env. Delivery remains disabled. No credentials were printed.'
