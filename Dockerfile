# --- نسخه نهایی با معماری دو اسکریپتی ---

# --- مرحله ۱: Builder ---
# این مرحله تمام فایل‌های مورد نیاز ما را جمع‌آوری می‌کند.
FROM mcr.microsoft.com/windows/servercore:ltsc2022 AS builder
WORKDIR /source

# کپی کردن فایل‌های نصب‌کننده
COPY python-3.11.4-amd64.exe .
COPY meta.zip .

# کپی کردن هر سه اسکریپت
COPY streamer.py .
COPY reporter.py .
COPY start.ps1 .

# --- مرحله ۲: Final Image ---
# ایمیج نهایی و تمیز ما از اینجا شروع می‌شود.
FROM mcr.microsoft.com/windows/servercore:ltsc2022
WORKDIR /app

# کپی کردن و نصب پایتون، سپس حذف نصب‌کننده
COPY --from=builder /source/python-3.11.4-amd64.exe .
RUN .\python-3.11.4-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 && del .\python-3.11.4-amd64.exe

# کپی کردن و استخراج متاتریدر، سپس حذف فایل فشرده
COPY --from=builder /source/meta.zip .
RUN powershell -command "Expand-Archive -Path .\meta.zip -DestinationPath 'C:\Program Files'" && del .\meta.zip
# نصب تمام کتابخانه‌های پایتون مورد نیاز برای هر دو اسکریپت
RUN pip install MetaTrader5 pandas websockets Flask waitress && pip cache purge

# کپی کردن سه اسکریپت نهایی از مرحله builder به ایمیج
COPY --from=builder /source/streamer.py .
COPY --from=builder /source/reporter.py .
COPY --from=builder /source/start.ps1 .

# باز کردن پورت 8080 برای دسترسی به Health Check
EXPOSE 8080

# دستور Health Check (بدون تغییر، چون Health Check در reporter.py است)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ["powershell", "-Command", "try { $resp = Invoke-WebRequest -Uri 'http://localhost:8080/health' -UseBasicParsing; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"]

# --- مهم‌ترین تغییر ---
# دستور نهایی: اجرای اسکریپت مدیر پروسه start.ps1
CMD ["powershell", "-File", "C:\\app\\start.ps1"]