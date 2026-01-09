# Read .env file
$envContent = Get-Content .env
foreach ($line in $envContent) {
    if ($line -match '^([^#=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [System.Environment]::SetEnvironmentVariable($name, $value)
    }
}

# Run LiveKit Server
docker stop livekit-server 2>$null
docker rm -f livekit-server 2>$null
docker run -d --name livekit-server `
    -p 7880:7880 `
    -p 7881:7881 `
    -p 7882:7882/udp `
    -e LIVEKIT_KEYS="$($env:LIVEKIT_API_KEY): $($env:LIVEKIT_API_SECRET)" `
    livekit/livekit-server:latest --dev --node-ip 192.168.29.73

Write-Host "Waiting for server to initialize..."
Start-Sleep -Seconds 3
docker logs livekit-server
