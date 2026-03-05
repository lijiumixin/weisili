# Twitter to WeChat 自动发布系统 - 配置脚本
# 使用方法：在PowerShell中运行此脚本

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Twitter to WeChat 自动发布系统" -ForegroundColor Cyan
Write-Host "配置向导" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 检查.env文件是否存在
if (Test-Path ".env") {
    Write-Host "✅ .env 文件已存在" -ForegroundColor Green
    $overwrite = Read-Host "是否要重新配置？(y/n)"
    if ($overwrite -ne 'y') {
        Write-Host "跳过配置。" -ForegroundColor Yellow
        exit
    }
}

# 请求输入API密钥
Write-Host ""
Write-Host "请输入你的 OpenAI API 密钥：" -ForegroundColor Yellow
Write-Host "提示：密钥格式类似 sk-xxxxxxxxxxxxxxxx" -ForegroundColor Gray
$apiKey = Read-Host "API密钥"

# 创建.env文件
$envContent = "# OpenAI API配置`nOPENAI_API_KEY=$apiKey`n"
Set-Content -Path ".env" -Value $envContent -Encoding UTF8

Write-Host ""
Write-Host "✅ .env 文件创建成功！" -ForegroundColor Green
Write-Host ""

# 验证配置
Write-Host "正在验证配置..." -ForegroundColor Yellow
python -c "from src.config_manager import ConfigManager; config = ConfigManager(); print('✅ 配置验证成功！')"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "配置完成！接下来的步骤：" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. 首次登录微信公众号：" -ForegroundColor White
    Write-Host "   python main.py --login" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. 测试运行一次：" -ForegroundColor White
    Write-Host "   python main.py --mode test" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "3. 正式运行（定时任务）：" -ForegroundColor White
    Write-Host "   python main.py --mode production" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "⚠️  配置验证失败，请检查API密钥是否正确。" -ForegroundColor Red
}
