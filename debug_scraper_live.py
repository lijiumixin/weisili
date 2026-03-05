
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.twitter_scraper import TwitterScraper, ScraperConfig

async def debug_scraper():
    print("🔍 开始调试爬虫...")
    
    config = ScraperConfig(
        target_username="neilksethi",
        headless=False, # 显示浏览器以便观察
        max_retries=1
    )
    
    scraper = TwitterScraper(config)
    
    try:
        await scraper.initialize()
        print("访问 Twitter...")
        
        # 爬取
        tweets = await scraper.scrape_tweets("neilksethi", max_count=10)
        
        print(f"\n✅ 共抓取到 {len(tweets)} 条推文：")
        print("-" * 60)
        
        for i, tweet in enumerate(tweets, 1):
            print(f"[{i}] ID: {tweet.tweet_id}")
            print(f"    时间: {tweet.created_at}")
            content_preview = tweet.text[:50].replace('\n', ' ')
            print(f"    内容: {content_preview}...")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(debug_scraper())
