"""
小红书发布流程诊断脚本
用于检查页面元素和选择器是否正确
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def diagnose_xiaohongshu():
    print("🔍 开始诊断小红书发布页面...")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    # 加载登录态
    state_file = Path("config/xiaohongshu_state.json")
    if state_file.exists():
        context = await browser.new_context(
            storage_state=str(state_file),
            viewport={'width': 1920, 'height': 1080}
        )
        print("✅ 已加载登录态")
    else:
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        print("⚠️  未找到登录态文件")
    
    page = await context.new_page()
    
    # 导航到发布页面
    url = "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image"
    print(f"\n📍 访问: {url}")
    await page.goto(url, wait_until='networkidle', timeout=30000)
    await asyncio.sleep(2)
    
    print("\n" + "="*60)
    print("诊断结果：")
    print("="*60)
    
    # 1. 检查页面标题
    title = await page.title()
    print(f"\n1. 页面标题: {title}")
    
    # 2. 检查 "上传图文" 按钮
    print("\n2. 检查 '上传图文' 按钮:")
    try:
        # 尝试找到所有包含"上传图文"的元素
        upload_texts = page.get_by_text("上传图文")
        count = await upload_texts.count()
        print(f"   找到 {count} 个 '上传图文' 元素")
        
        if count > 0:
            for i in range(count):
                elem = upload_texts.nth(i)
                is_visible = await elem.is_visible()
                print(f"   - 第 {i} 个: 可见={is_visible}")
        else:
            print("   ❌ 未找到任何 '上传图文' 元素")
            
            # 尝试其他可能的文本
            print("\n   尝试查找其他可能的按钮文本：")
            alternatives = ["图文", "发布图文", "新建图文", "上传", "创作"]
            for alt in alternatives:
                alt_count = await page.get_by_text(alt).count()
                if alt_count > 0:
                    print(f"   - 找到 '{alt}': {alt_count} 个")
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
    
    # 3. 检查所有按钮
    print("\n3. 检查页面上的所有按钮:")
    try:
        buttons = page.get_by_role("button")
        button_count = await buttons.count()
        print(f"   找到 {button_count} 个按钮")
        
        if button_count > 0:
            print("   按钮列表:")
            for i in range(min(button_count, 10)):  # 只显示前10个
                btn = buttons.nth(i)
                text = await btn.inner_text() if await btn.is_visible() else "(不可见)"
                print(f"   - 按钮 {i}: {text}")
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
    
    # 4. 截图保存
    screenshot_path = "screenshots/xiaohongshu_diagnosis.png"
    Path("screenshots").mkdir(exist_ok=True)
    await page.screenshot(path=screenshot_path)
    print(f"\n4. 截图已保存: {screenshot_path}")
    
    print("\n" + "="*60)
    print("⏸️  浏览器将保持打开，请您查看页面并按 Ctrl+C 退出")
    print("="*60)
    
    # 等待用户手动检查
    try:
        await asyncio.sleep(300)  # 等待5分钟
    except KeyboardInterrupt:
        print("\n✅ 诊断完成")
    
    await context.close()
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(diagnose_xiaohongshu())
