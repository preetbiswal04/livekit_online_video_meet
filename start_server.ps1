# # Read .env file
# $envContent = Get-Content .env
# foreach ($line in $envContent) {
#     if ($line -match '^([^#=]+)=(.*)$') {
#         $name = $matches[1]
#         $value = $matches[2]
#         [System.Environment]::SetEnvironmentVariable($name, $value)
#     }
# }

# # Run LiveKit Server
# docker stop livekit-server 2>$null
# docker rm -f livekit-server 2>$null
# docker run -d --name livekit-server `
#     -p 7880:7880 `
#     -p 7881:7881 `
#     -p 7882:7882/udp `
#     -e LIVEKIT_KEYS="$($env:LIVEKIT_API_KEY): $($env:LIVEKIT_API_SECRET)" `
#     -e LIVEKIT_NODE_IP="192.168.100.80" `
#     livekit/livekit-server:latest --dev --node-ip 192.168.100.80

# Write-Host "Waiting for server to initialize..."
# Start-Sleep -Seconds 3
# docker logs livekit-server

# Load .env variables
$envContent = Get-Content .env
foreach ($line in $envContent) {
    if ($line -match '^([^#=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [System.Environment]::SetEnvironmentVariable($name, $value)
    }
}
# Start Backend (Token Generator)
Write-Host "Starting Flask Backend..." -ForegroundColor Cyan
Start-Process python -ArgumentList "backend.py" -NoNewWindow
# Start Transcription Agent (AI Worker)
Write-Host "Starting Transcription Agent..." -ForegroundColor Cyan
python transcription_agent.py dev
