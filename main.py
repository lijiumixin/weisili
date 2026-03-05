"""
Twitter to WeChat Auto Publishing System
主程序入口

使用方法:
    测试模式（首次运行）: python main.py --mode test
    生产模式: python main.py --mode production
"""

import sys
import argparse
import asyncio
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.scheduler import TaskScheduler
from src.wechat_publisher import WeChatPublisher


async def first_time_login_twitter():
    """首次运行：登录Twitter"""
    print("\n" + "=" * 60)
    print("🔐 首次登录 Twitter")
    print("=" * 60)
    
    from src.twitter_scraper import TwitterScraper, ScraperConfig
    
    config = ScraperConfig(
        target_username="test", # 仅用于初始化，不重要
        headless=False
    )
    
    scraper = TwitterScraper(config)
    
    try:
        await scraper.login()
            
    finally:
        await scraper.close()

async def first_time_login():
    """首次运行：登录微信公众号"""
    print("\n" + "=" * 60)
    print("🔐 首次登录微信公众号")
    print("=" * 60)
    
    from src.config_manager import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.get_all()
    
    publisher = WeChatPublisher(
        config=config['wechat'],
        headless=False  # 首次登录必须显示浏览器
    )
    
    await publisher.initialize()
    
    try:
        logged_in = await publisher.login(manual=True, timeout=180)
        
        if logged_in:
            print("\n✅ 登录成功！登录态已保存")
            print("现在可以使用 --mode production 运行系统了")
        else:
            print("\n❌ 登录失败或超时")
            
    finally:
        await publisher.close()


async def first_time_login_xiaohongshu():
    """首次运行：登录小红书创作者平台"""
    print("\n" + "=" * 60)
    print("🔐 首次登录小红书创作者平台")
    print("=" * 60)
    
    from src.config_manager import ConfigManager
    from src.xiaohongshu_publisher import XiaohongshuPublisher
    
    config_manager = ConfigManager()
    config = config_manager.get_all()
    
    publisher = XiaohongshuPublisher(
        config=config['xiaohongshu'],
        headless=False  # 首次登录必须显示浏览器
    )
    
    await publisher.initialize()
    
    try:
        logged_in = await publisher.login(manual=True, timeout=180)
        
        if logged_in:
            print("\n✅ 登录成功！登录态已保存")
            print("现在可以使用 --mode test 测试小红书发布了")
        else:
            print("\n❌ 登录失败或超时")
            
    finally:
        await publisher.close()



async def test_mode():
    """测试模式：执行一次完整流程"""
    print("\n" + "=" * 60)
    print("🧪 测试模式 - 执行一次完整流程")
    print("=" * 60)
    
    scheduler = TaskScheduler()
    await scheduler.initialize_modules()
    
    try:
        # 直接执行流程，如果登录失效会在发布时报错
        await scheduler.run_pipeline()
        
        print("\n✅ 测试完成")
        
    finally:
        await scheduler.cleanup()


def production_mode():
    """生产模式：启动定时任务"""
    print("\n" + "=" * 60)
    print("🚀 生产模式 - 启动定时任务")
    print("=" * 60)
    print("提示: 按 Ctrl+C 停止程序\n")
    
    scheduler = TaskScheduler()
    
    # 初始化模块
    asyncio.run(scheduler.initialize_modules())
    
    try:
        # 启动定时任务（会一直运行）
        scheduler.schedule_tasks()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  收到停止信号，正在关闭...")
        asyncio.run(scheduler.cleanup())
        print("✅ 程序已安全退出")
    
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        asyncio.run(scheduler.cleanup())


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Twitter to WeChat & Xiaohongshu Auto Publishing System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  首次登录微信:       python main.py --login
  首次登录小红书:     python main.py --login-xiaohongshu
  首次登录Twitter:    python main.py --login-twitter
  测试运行一次:       python main.py --mode test
  正式运行:           python main.py --mode production
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['test', 'production'],
        help='运行模式: test=测试执行一次, production=定时运行'
    )
    
    parser.add_argument(
        '--login',
        action='store_true',
        help='首次登录微信公众号'
    )
    
    parser.add_argument(
        '--login-xiaohongshu',
        action='store_true',
        help='首次登录小红书创作者平台'
    )
    
    parser.add_argument(
        '--login-twitter',
        action='store_true',
        help='首次登录Twitter'
    )
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if not args.mode and not args.login and not args.login_twitter and not args.login_xiaohongshu:
        parser.print_help()
        sys.exit(0)
    
    # 执行对应模式
    if args.login:
        asyncio.run(first_time_login())
    
    elif args.login_xiaohongshu:
        asyncio.run(first_time_login_xiaohongshu())
    
    elif args.login_twitter:
        asyncio.run(first_time_login_twitter())
    
    elif args.mode == 'test':
        asyncio.run(test_mode())
    
    elif args.mode == 'production':
        production_mode()


if __name__ == "__main__":
    # 显示系统启动信息
    print("=" * 60)
    print("🚀 Twitter to WeChat 自动发布系统 v1.0")
    print("=" * 60)
    
    main()
