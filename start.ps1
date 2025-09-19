# start.ps1 (نسخه جدید با ترتیب اجرا)

Write-Host "Supervisor: Starting Reporter Bot (The Launcher)..."
$ReporterJob = Start-Job -ScriptBlock { & "C:\Program Files\Python311\python.exe" "C:\app\streamer.py" }

# 15 ثانیه صبر می‌کنیم تا متاتریدر به طور کامل راه‌اندازی شود
Write-Host "Supervisor: Waiting 15 seconds for MetaTrader terminal to initialize..."
Start-Sleep -Seconds 15

Write-Host "Supervisor: Starting Streamer Bot (The Connector)..."
$StreamerJob = Start-Job -ScriptBlock { & "C:\Program Files\Python311\python.exe" "C:\app\reporter.py" }

Write-Host "Supervisor: All jobs started. Monitoring..."
# حلقه اصلی برای نمایش مداوم لاگ‌ها و زنده نگه داشتن کانتینر
while ($true) {
    # دریافت و نمایش خروجی از هر دو جاب
    Receive-Job -Job $StreamerJob
    Receive-Job -Job $ReporterJob
    
    
    # بررسی وضعیت جاب‌ها
    if ($ReporterJob.State -eq 'Failed' -or $StreamerJob.State -eq 'Failed') {
        Write-Host "Supervisor: One of the jobs has failed. Check logs above for errors."
        # می‌توانید در اینجا منطق ری‌استارت کردن جاب‌ها را نیز اضافه کنید
    }
    
    Start-Sleep -Seconds 2
}