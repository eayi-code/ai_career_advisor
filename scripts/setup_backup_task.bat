@echo off
chcp 65001 >nul
echo ========================================
echo   配置数据库自动备份定时任务
echo ========================================
echo.

:: 备份目录
set BACKUP_DIR=D:\ai_career_advisor\backups

:: 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: 创建每日备份任务（每天凌晨2点）
echo [1/2] 创建每日备份任务...
schtasks /create /tn "CareerAdvisor_DailyBackup" /tr "D:\CondaEnvs\career_advisor\python.exe D:\ai_career_advisor\scripts\backup.py" /sc daily /st 02:00 /f
if %errorlevel%==0 (
    echo       ✓ 每日备份任务创建成功（每天凌晨2点）
) else (
    echo       ✗ 任务创建失败，请以管理员权限运行
)

:: 创建每周清理任务（每周日凌晨3点清理7天前的备份）
echo [2/2] 创建清理任务...
schtasks /create /tn "CareerAdvisor_CleanupBackup" /tr "powershell -Command \"Get-ChildItem 'D:\ai_career_advisor\backups\*' | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item -Force\"" /sc weekly /d SUN /st 03:00 /f
if %errorlevel%==0 (
    echo       ✓ 清理任务创建成功（每周日凌晨3点）
) else (
    echo       ✗ 任务创建失败，请以管理员权限运行
)

echo.
echo ========================================
echo   配置完成！
echo ========================================
echo.
echo 备份位置: %BACKUP_DIR%
echo.
echo 已创建的任务：
echo   1. CareerAdvisor_DailyBackup - 每天凌晨2点备份
echo   2. CareerAdvisor_CleanupBackup - 每周日凌晨3点清理旧备份
echo.
echo 查看任务: schtasks /query /tn "CareerAdvisor*"
echo 删除任务: schtasks /delete /tn "CareerAdvisor_DailyBackup" /f
echo.
pause
