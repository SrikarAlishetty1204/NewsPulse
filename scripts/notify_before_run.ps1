# Windows notification 30 minutes before the scheduled NewsPulse run.
# Shows free RAM against MIN_FREE_RAM_GB; stays quiet if today's run already finished.
$root = Split-Path -Parent $PSScriptRoot

$lastRunFile = Join-Path $root "logs\last_run.txt"
if ((Test-Path $lastRunFile) -and ((Get-Content $lastRunFile).Trim() -eq (Get-Date -Format "yyyy-MM-dd"))) {
    exit
}

$neededGb = 6
$setting = Select-String -Path (Join-Path $root ".env") -Pattern "^MIN_FREE_RAM_GB=(.+)"
if ($setting) {
    $neededGb = $setting.Matches[0].Groups[1].Value.Trim()
}
$freeGb = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)

$title = "NewsPulse runs in 30 minutes"
$body = "Please close heavy apps to free memory. Free RAM now: $freeGb GB, needs $neededGb GB."

[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$toast = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$texts = $toast.GetElementsByTagName("text")
$texts.Item(0).AppendChild($toast.CreateTextNode($title)) | Out-Null
$texts.Item(1).AppendChild($toast.CreateTextNode($body)) | Out-Null

# Shown under PowerShell's name; a script has no registered app identity of its own
$appId = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show([Windows.UI.Notifications.ToastNotification]::new($toast))
