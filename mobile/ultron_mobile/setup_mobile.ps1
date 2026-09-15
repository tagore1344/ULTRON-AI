$ErrorActionPreference = 'Stop'

Write-Host "=== TAG Mobile Native Setup ===" -ForegroundColor Cyan

if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw "Flutter SDK was not found on PATH. Install Flutter first, then rerun this script."
}

Write-Host "Generating Android/iOS platform projects..." -ForegroundColor Yellow
flutter create --platforms=android,ios .

$manifest = Join-Path $PSScriptRoot "android\app\src\main\AndroidManifest.xml"
if (Test-Path $manifest) {
    $xml = Get-Content $manifest -Raw
    $permissions = @"
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.BLUETOOTH" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
"@
    if ($xml -notmatch 'android\.permission\.RECORD_AUDIO') {
        $xml = $xml -replace '(<manifest[^>]*>)', ('$1' + "`r`n" + $permissions.TrimEnd())
    }
    if ($xml -notmatch 'android\.speech\.RecognitionService') {
        $queries = @"
    <queries>
        <intent>
            <action android:name="android.speech.RecognitionService" />
        </intent>
    </queries>
"@
        $xml = $xml -replace '(</manifest>)', ($queries.TrimEnd() + "`r`n$1")
    }
    Set-Content -Path $manifest -Value $xml -Encoding UTF8
    Write-Host "Android microphone/network permissions configured." -ForegroundColor Green
}

$plist = Join-Path $PSScriptRoot "ios\Runner\Info.plist"
if (Test-Path $plist) {
    $xml = Get-Content $plist -Raw
    if ($xml -notmatch 'NSSpeechRecognitionUsageDescription') {
        $insert = @"
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>TAG uses speech recognition to understand your voice commands.</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>TAG uses the microphone for voice conversations.</string>
"@
        $xml = $xml -replace '(</dict>)', ($insert.TrimEnd() + "`r`n$1")
        Set-Content -Path $plist -Value $xml -Encoding UTF8
    }
    Write-Host "iOS speech/microphone permissions configured." -ForegroundColor Green
}

Write-Host "Installing Flutter dependencies..." -ForegroundColor Yellow
flutter pub get

Write-Host "" 
Write-Host "TAG Mobile setup complete." -ForegroundColor Green
Write-Host "Run: flutter run" -ForegroundColor Cyan
