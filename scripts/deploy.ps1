param(
    [string]$Tag = "latest",
    [string]$HealthUrl = "http://localhost:8000/"
)

$ErrorActionPreference = "Stop"

$Image = "ghcr.io/brcsln/logsense:$Tag"
$Container = "logsense-deploy"
$Backup = "logsense-backup"

Write-Host "Deploying LogSense: $Image"

# Download the requested image before changing anything
docker pull $Image
if ($LASTEXITCODE -ne 0) {
    throw "Failed to pull image."
}

# Avoid overwriting an existing backup
$ExistingContainers = @(docker ps -a --format "{{.Names}}")

if ($Backup -in $ExistingContainers) {
    throw "Backup container already exists. Review it before redeploying."
}

# Preserve the existing container for rollback
$HadPrevious = ($Container -in $ExistingContainers)

if ($HadPrevious) {
    docker stop $Container | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to stop current container." }

    docker rename $Container $Backup
    if ($LASTEXITCODE -ne 0) {
        docker start $Container | Out-Null
        throw "Failed to preserve current container."
    }
}

$Healthy = $false

try {
    docker run -d --name $Container -p 8000:8000 $Image
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start new container."
    }

    for ($Attempt = 1; $Attempt -le 10; $Attempt++) {
        try {
            $Response = Invoke-WebRequest `
                -Uri $HealthUrl `
                -UseBasicParsing `
                -TimeoutSec 5 `
                -ErrorAction Stop

            if ($Response.StatusCode -eq 200) {
                $Healthy = $true
                break
            }
        }
        catch {
            Write-Host "Health check attempt $Attempt failed."
        }

        Start-Sleep -Seconds 2
    }

    if (-not $Healthy) {
        throw "Health check failed."
    }

    Write-Host "Deployment successful! HTTP 200 OK."
    if ($HadPrevious) {
        Write-Host "Previous container preserved as $Backup."
    }
}
catch {
    Write-Host "Deployment failed. Attempting rollback..."

    docker rm -f $Container 2>$null | Out-Null

    if ($HadPrevious) {
        docker rename $Backup $Container
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback failed: could not restore container name."
        }

        docker start $Container | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback failed: previous container did not start."
        }

        Write-Host "Previous container restarted. Verify its health."
    }

    throw "Deployment failed; check the container state."
}