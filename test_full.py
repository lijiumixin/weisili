"""
完整测试 - 包含图片
测试Twitter爬取、翻译和发布全流程
"""

import asyncio
from src.scheduler import TaskScheduler

async def main():
    print("=" * 60)
    print("🧪 完整流程测试（包含图片）")
    print("=" * 60)
    
    scheduler = TaskScheduler()
    await scheduler.initialize_modules()
    
    try:
        # 检查微信登录状态
        print("\n检查登录状态...")
        logged_in = await scheduler.publisher.check_login_status()
        
        if not logged_in:
            print("❌ 微信未登录，请先运行: python main.py --login")
            return
        
        print("✅ 微信已登录")
        
        # 执行完整流程
        print("\n开始执行完整流程...")
        await scheduler.run_pipeline()
        
        print("\n" + "=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)
        print("\n请检查：")
        print("1. 微信公众号后台 - 图文草稿")
        print("2. logs/app.log - 详细日志")
        print("3. screenshots/ - 截图记录")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await scheduler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
