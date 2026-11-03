# Joins the board's own WiFi network, runs one test command, then always rejoins
# the home network and removes the temporary profile.
# Usage: powershell -ExecutionPolicy Bypass -File on_board_network.ps1 -Ssid XIAO-AV -Test "py -I ..."
param(
  [string]$Ssid,
  [string]$Test,
  [string]$Password = "xiaoav123",
  [string]$HomeSsid = "Foot5"
)

function Wait-WifiIp([string]$prefix, [int]$seconds) {
  $end = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $end) {
    $ip = (Get-NetIPAddress -InterfaceAlias "Wi-Fi" -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
    if ($ip -like "$prefix*") { return $ip }
    Start-Sleep -Milliseconds 500
  }
  return $null
}

$profilePath = Join-Path $PSScriptRoot "$Ssid.xml"
@"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>$Ssid</name>
  <SSIDConfig><SSID><name>$Ssid</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>manual</connectionMode>
  <MSM><security>
    <authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
    <sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>$Password</keyMaterial></sharedKey>
  </security></MSM>
</WLANProfile>
"@ | Out-File -Encoding ascii $profilePath

try {
  netsh wlan add profile filename="$profilePath" user=current | Out-Null
  $ip = $null
  for ($i = 0; $i -lt 4 -and -not $ip; $i++) {
    netsh wlan connect name="$Ssid" | Out-Null
    $ip = Wait-WifiIp "192.168.4." 15
  }
  if (-not $ip) { Write-Output "Could not join $Ssid"; return }
  Write-Output "PC joined $Ssid as $ip"
  $iface = netsh wlan show interfaces | Select-String "Channel|Receive rate|Transmit rate|Signal|Radio type"
  $iface | ForEach-Object { Write-Output ("  " + $_.Line.Trim()) }
  Invoke-Expression $Test
}
finally {
  netsh wlan connect name="$HomeSsid" | Out-Null
  $back = Wait-WifiIp "192.168.1." 40
  netsh wlan delete profile name="$Ssid" | Out-Null
  Remove-Item $profilePath -ErrorAction SilentlyContinue
  if ($back) { Write-Output "PC back on $HomeSsid as $back" } else { Write-Output "WARNING: not back on $HomeSsid yet - Windows should auto-reconnect" }
}
