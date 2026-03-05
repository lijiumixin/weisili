"""
任务调度模块
负责定时触发爬取任务并协调各模块执行
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Set
from pathlib import Path
import schedule

from .config_manager import ConfigManager
from .twitter_scraper import TwitterScraper, ScraperConfig
from .translator import Translator
from .wechat_publisher import WeChatPublisher
from .xiaohongshu_publisher import XiaohongshuPublisher
from .notifier import Notifier
from .utils import load_json, save_json


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化调度器
        
        加载配置并初始化各模块
        """
        print("=" * 60)
        print("🚀 Twitter to WeChat 自动发布系统 v1.0")
        print("=" * 60)
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_all()
        
        # 初始化通知器
        self.notifier = Notifier(
            self.config['notification'],
            self.config['logging']
        )
        
        # 模块实例（稍后初始化）
        self.scraper: TwitterScraper = None
        self.translator: Translator = None
        self.publisher: WeChatPublisher = None
        
        # 已发布推文记录
        self.published_tweets: Set[str] = self._load_published_tweets()
        
        self.notifier.log('INFO', '系统初始化完成')
    
    def _load_published_tweets(self) -> Set[str]:
        """
        加载已发布推文ID集合
        
        从config/published_tweets.json读取
        """
        data = load_json('config/published_tweets.json', {'published_tweet_ids': []})
        tweet_ids = data.get('published_tweet_ids', [])
        self.notifier.log('INFO', f'加载已发布推文记录: {len(tweet_ids)} 条')
        return set(tweet_ids)
    
    def _save_published_tweet(self, tweet_id: str):
        """保存已发布推文ID"""
        self.published_tweets.add(tweet_id)
        
        data = {
            'published_tweet_ids': list(self.published_tweets),
            'last_updated': datetime.now().isoformat()
        }
        save_json('config/published_tweets.json', data)
        self.notifier.log('INFO', f'记录已发布推文: {tweet_id}')
    
    def _cleanup_old_images(self, days: int = 7):
        """清理旧图片"""
        try:
            image_dir = Path("data/images")
            if not image_dir.exists():
                return
                
            cutoff = time.time() - (days * 86400)
            deleted_count = 0
            
            for file_path in image_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.png', '.jpeg']:
                    if file_path.stat().st_mtime < cutoff:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception:
                            pass
                            
            # 清理空目录
            # 注意：rglob是生成器，删除目录可能会影响遍历，所以简单处理或忽略
            # 这里为了安全起见，只清理图片，空目录留着也没事
                        
            if deleted_count > 0:
                self.notifier.log('INFO', f'🧹 清理了 {deleted_count} 张旧图片')
                
        except Exception as e:
            self.notifier.log('WARNING', f'清理旧图片失败: {e}')
    
    async def initialize_modules(self):
        """初始化各模块"""
        self.notifier.log('INFO', '正在初始化各模块...')
        
        # 清理旧图片
        self._cleanup_old_images()
        
        # 初始化translator
        import os
        self.translator = Translator(
            api_key=self.config['openai']['api_key'],
            model=self.config['openai']['model'],
            config=self.config['translation']
        )
        self.notifier.log('INFO', '✅ 翻译器初始化完成')
    
    async def run_pipeline(self):
        """
        执行完整流程
        
        1. 爬取新推文
        2. 过滤已发布
        3. 翻译内容
        4. 间隔发布到微信
        """
        self.notifier.log('INFO', '=' * 60)
        self.notifier.log('INFO', f'开始执行爬取任务 [{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]')
        self.notifier.log('INFO', '=' * 60)
        
        try:
            # 0. 重载配置
            try:
                self.config_manager.reload()
                self.config = self.config_manager.get_all()
                # 更新模块配置
                if self.translator:
                    self.translator.config = self.config['translation']
            except Exception as e:
                self.notifier.log('WARNING', f'配置重载失败: {e}')
            
            # 1. 爬取推文
            username = self.config['twitter']['target_username']
            self.notifier.log('INFO', f'正在爬取 @{username} 的推文...')
            
            # 初始化scraper (每次新建，避免跨loop错误)
            scraper_config = ScraperConfig(
                target_username=username,
                headless=self.config['runtime']['headless'],
                max_retries=self.config['runtime']['max_retries']
            )
            self.scraper = TwitterScraper(scraper_config)
            
            tweets = []
            try:
                await self.scraper.initialize()
                tweets = await self.scraper.scrape_tweets(username, max_count=10)
                self.notifier.log('INFO', f'✅ 爬取到 {len(tweets)} 条推文')
            finally:
                await self.scraper.close()
                self.scraper = None
            
            # 2. 过滤已发布
            new_tweets = [t for t in tweets if t.tweet_id not in self.published_tweets]
            
            if not new_tweets:
                self.notifier.log('INFO', '💤 没有新推文需要发布')
                return
            
            self.notifier.log('INFO', f'🆕 发现 {len(new_tweets)} 条新推文')
            
            # 3. 逐条处理
            for i, tweet in enumerate(new_tweets, 1):
                try:
                    self.notifier.log('INFO', f'\n--- 处理推文 [{i}/{len(new_tweets)}] ---')
                    self.notifier.log('INFO', f'ID: {tweet.tweet_id}')
                    self.notifier.log('INFO', f'原文: {tweet.text[:100]}...')
                    
                    # 翻译（带容错）
                    try:
                        self.notifier.log('INFO', '🌐 正在翻译...')
                        translated = await self.translator.translate_tweet(tweet)
                        self.notifier.log('INFO', f'✅ 翻译完成')
                        self.notifier.log('INFO', f'标题: {translated.title}')
                    except Exception as trans_error:
                        self.notifier.log('ERROR', f'❌ 翻译失败，跳过此推文: {str(trans_error)}')
                        self.notifier.notify_desktop(
                            '翻译失败',
                            f'推文 {tweet.tweet_id[:10]}... 翻译失败，已跳过\n{str(trans_error)[:100]}'
                        )
                        continue  # 跳过这条推文，继续处理下一条
                    
                    # 为每条推文创建独立的publisher实例（避免反机器人检测）
                    self.notifier.log('INFO', '🔧 初始化微信发布器...')
                    single_publisher = WeChatPublisher(
                        config=self.config['wechat'],
                        headless=self.config['runtime']['headless']
                    )
                    
                    try:
                        # 初始化（会打开浏览器、加载登录态）
                        await single_publisher.initialize()
                        self.notifier.log('INFO', '✅ 微信发布器就绪')
                        
                        # 发布
                        self.notifier.log('INFO', '📤 正在发布到微信公众号...')
                        result = await single_publisher.publish_article(
                            title=translated.title,
                            content=translated.content,
                            images=tweet.local_image_paths or []
                        )
                        
                        if result.success:
                            self.notifier.log('INFO', f'✅ 发布成功: {translated.title}')
                            self._save_published_tweet(tweet.tweet_id)
                        else:
                            self.notifier.log('ERROR', f'❌ 发布失败: {result.error_message}')
                            self.notifier.notify_desktop(
                                '发布失败',
                                f'推文 {tweet.tweet_id[:10]}... 发布失败\n{result.error_message}'
                            )
                            
                            # 如果是登录过期，通知用户并停止
                            if result.error_type == 'LOGIN_EXPIRED':
                                self.notifier.log('CRITICAL', '⚠️  微信登录已过期，请重新登录')
                                self.notifier.notify_desktop(
                                    '登录已过期',
                                    '请重新运行程序并登录微信公众号'
                                )
                                break
                    
                    finally:
                        # 无论成功失败，都关闭这个publisher实例
                        self.notifier.log('INFO', '🔒 关闭微信发布器...')
                        await single_publisher.close()
                        self.notifier.log('INFO', '✅ 浏览器已关闭')
                    
                    # 小红书发布（如果启用）
                    if self.config.get('xiaohongshu', {}).get('enabled', False):
                        self.notifier.log('INFO', '🔧 初始化小红书发布器...')
                        xhs_publisher = XiaohongshuPublisher(
                            config=self.config['xiaohongshu'],
                            headless=self.config['runtime']['headless']
                        )
                        
                        try:
                            # 初始化
                            await xhs_publisher.initialize()
                            self.notifier.log('INFO', '✅ 小红书发布器就绪')
                            
                            # 发布
                            self.notifier.log('INFO', '📤 正在发布到小红书...')
                            xhs_result = await xhs_publisher.publish_article(
                                title=translated.title,
                                content=translated.content,
                                images=tweet.local_image_paths or []
                            )
                            
                            if xhs_result.success:
                                self.notifier.log('INFO', f'✅ 小红书发布成功: {translated.title}')
                            else:
                                self.notifier.log('ERROR', f'❌ 小红书发布失败: {xhs_result.error_message}')
                                self.notifier.notify_desktop(
                                    '小红书发布失败',
                                    f'推文 {tweet.tweet_id[:10]}... 发布失败\n{xhs_result.error_message}'
                                )
                        
                        except Exception as e:
                            self.notifier.log('ERROR', f'❌ 小红书发布出错: {str(e)}')
                        
                        finally:
                            self.notifier.log('INFO', '🔒 关闭小红书发布器...')
                            await xhs_publisher.close()
                            self.notifier.log('INFO', '✅ 浏览器已关闭')
                    else:
                        self.notifier.log('INFO', 'ℹ️  小红书发布已禁用（通过配置）')
                    
                    # 如果还有更多推文，等待随机间隔（两条推文之间，不是两个平台之间）
                    if i < len(new_tweets):
                        delay_minutes = random.uniform(
                            self.config['wechat']['publish_interval_min'],
                            self.config['wechat']['publish_interval_max']
                        )
                        delay_seconds = delay_minutes * 60
                        
                        self.notifier.log('INFO', f'⏱️  等待 {delay_minutes:.1f} 分钟后发布下一条推文...')
                        await asyncio.sleep(delay_seconds)
                
                except Exception as e:
                    self.notifier.log('ERROR', f'❌ 处理推文 {tweet.tweet_id} 时出错: {str(e)}')
                    self.notifier.notify_desktop(
                        '处理错误',
                        f'推文处理失败，请查看日志\n{str(e)[:100]}'
                    )
                    continue  # 继续处理下一条
            
            self.notifier.log('INFO', '✅ 本次任务执行完成')
        
        except Exception as e:
            self.notifier.log('CRITICAL', f'❌ 执行流程时发生严重错误: {str(e)}')
            self.notifier.notify_desktop(
                '系统错误',
                f'系统运行异常，请查看日志\n{str(e)[:100]}'
            )
    
    def schedule_tasks(self):
        """
        安排定时任务
        
        使用schedule库，每15-30分钟随机间隔执行
        """
        self.notifier.log('INFO', '⏰ 启动定时任务调度器...')
        
        def run_with_random_interval():
            """执行任务并安排下次运行"""
            # 执行任务
            try:
                asyncio.run(self.run_pipeline())
            except Exception as e:
                self.notifier.log('ERROR', f'任务执行出错: {e}')
            
            # 计算下次运行时间（15-30分钟随机）
            next_run_minutes = random.uniform(
                self.config['twitter']['scrape_interval_min'],
                self.config['twitter']['scrape_interval_max']
            )
            
            from datetime import timedelta
            next_run_time = datetime.now() + timedelta(minutes=next_run_minutes)
            
            self.notifier.log('INFO', f'⏰ 下次运行时间: {next_run_minutes:.1f} 分钟后 ({next_run_time.strftime("%H:%M:%S")})')
            
            # 清除旧任务，安排新任务
            schedule.clear()
            schedule.every(next_run_minutes).minutes.do(run_with_random_interval)
        
        # 首次立即执行
        self.notifier.log('INFO', '▶️  首次任务立即执行...')
        schedule.every(0).seconds.do(run_with_random_interval)
        
        # 持续运行
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    async def cleanup(self):
        """清理资源"""
        self.notifier.log('INFO', '正在清理资源...')
        
        if self.scraper:
            await self.scraper.close()
        # 不再需要关闭全局publisher，因为每个独立的publisher都在使用后立即关闭
        # if self.publisher:
        #     await self.publisher.close()
        
        self.notifier.log('INFO', '✅ 资源清理完成')


# 测试代码
if __name__ == "__main__":
    async def test():
        scheduler = TaskScheduler()
        await scheduler.initialize_modules()
        
        try:
            # 测试单次执行
            await scheduler.run_pipeline()
        finally:
            await scheduler.cleanup()
    
    asyncio.run(test())
