"""
Twitter内容爬虫模块
使用Playwright爬取指定用户的推文和图片
"""

import asyncio
import random
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import aiohttp
import json


from .utils import (
    Tweet, ScraperConfig, ScraperException,
    ensure_dir, format_timestamp
)


# User-Agent池（轮换使用）
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]


class TwitterScraper:
    """Twitter内容爬虫"""
    
    def __init__(self, config: ScraperConfig):
        """
        初始化爬虫
        
        Args:
            config: 爬虫配置对象
        """
        self.config = config
        self.state_file = Path("config/twitter_state.json")
        self.cookies_file = Path("config/cookies.json")
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def initialize(self):
        """初始化Playwright浏览器"""
        self.playwright = await async_playwright().start()
        
        # 浏览器启动参数
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=browser_args
        )
        
        # 尝试加载登录态
        if self.state_file.exists():
            try:
                self.context = await self.browser.new_context(
                    storage_state=str(self.state_file),
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                )
                print("✅ 已加载 Twitter 登录态 (State)")
            except Exception as e:
                print(f"⚠️  加载登录态失败: {e}")
                self.context = None
        
        # 尝试加载 Cookies
        if not self.context and self.cookies_file.exists():
            try:
                self.context = await self.browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080},
                )
                await self._load_cookies_from_file()
                print("✅ 已加载 Twitter Cookies")
            except Exception as e:
                print(f"⚠️  加载 Cookies 失败: {e}")
                if self.context:
                    await self.context.close()
                self.context = None
        
        if not self.context:
            # 创建context with random User-Agent
            self.context = await self.browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1920, 'height': 1080},
            )
        
        self.page = await self.context.new_page()
        
        # 修改navigator.webdriver
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    async def login(self):
        """手动登录并保存状态"""
        if not self.page:
            await self.initialize()
            
        print("🔐 正在打开 Twitter 登录页...")
        await self.page.goto("https://x.com/i/flow/login", wait_until='networkidle')
        
        print("\n👉 请在浏览器中手动登录 Twitter...")
        print("👉 登录成功后，程序会自动检测并保存状态")
        print("⏳ 等待登录 (最长 5 分钟)...")
        
        try:
            # 等待 URL 变为 home
            await self.page.wait_for_url("https://x.com/home", timeout=300000)
            print("✅ 检测到登录成功！")
            
            # 保存状态
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=str(self.state_file))
            print(f"✅ 登录态已保存至: {self.state_file}")
            return True
            
        except Exception as e:
            print(f"❌ 登录超时或失败: {e}")
            return False
    
    async def scrape_tweets(
        self, 
        username: str, 
        since_id: Optional[str] = None,
        max_count: int = 10
    ) -> List[Tweet]:
        """
        爬取指定用户的新推文
        
        Args:
            username: Twitter用户名（不含@）
            since_id: 上次爬取的最后一条tweet ID，只返回比这个ID新的推文
            max_count: 最多爬取数量
            
        Returns:
            推文对象列表，按时间倒序（最新的在前）
            
        Raises:
            ScraperException: 爬取失败时抛出
        """
        if not self.page:
            raise ScraperException("浏览器未初始化，请先调用initialize()")
        
        try:
            url = f"https://x.com/{username}"
            print(f"📍 访问页面: {url}")
            
            # 访问用户主页
            await self.page.goto(url, wait_until='networkidle', timeout=self.config.timeout)
            await self._random_delay(2, 4)
            
            # 模拟人类滚动行为
            await self._simulate_human_behavior()
            
            # 提取推文
            tweets = await self._extract_tweets(username, max_count)
            
            # 如果提供了since_id，过滤旧推文
            if since_id:
                tweets = [t for t in tweets if t.tweet_id > since_id]
            
            print(f"✅ 成功爬取 {len(tweets)} 条推文")
            
            # 下载图片
            for tweet in tweets:
                if tweet.image_urls:
                    tweet.local_image_paths = await self.download_images(tweet)
            
            return tweets
            
        except Exception as e:
            raise ScraperException(f"爬取推文失败: {str(e)}")
    
    async def _extract_tweets(self, username: str, max_count: int) -> List[Tweet]:
        """提取页面中的推文信息"""
        tweets = []
        
        try:
            # 等待推文加载
            await self.page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
            
            # 获取所有推文元素
            tweet_elements = await self.page.query_selector_all('article[data-testid="tweet"]')
            
            if not tweet_elements:
                print("⚠️  警告: 未找到任何推文元素！可能是选择器失效或页面加载不完整。")
                # 尝试截图以便调试
                try:
                    await self.page.screenshot(path="screenshots/debug_scraper_no_tweets.png")
                    print("  已保存调试截图: screenshots/debug_scraper_no_tweets.png")
                except:
                    pass
            
            for element in tweet_elements[:max_count]:
                try:
                    tweet = await self._parse_tweet_element(element, username)
                    if tweet:
                        tweets.append(tweet)
                except Exception as e:
                    print(f"⚠️  解析推文元素失败: {e}")
                    continue
            
            return tweets
            
        except Exception as e:
            print(f"⚠️  提取推文失败: {e}")
            return tweets
    
    async def _parse_tweet_element(self, element, username: str) -> Optional[Tweet]:
        """解析单个推文元素"""
        try:
            # 提取推文文本
            text_elem = await element.query_selector('[data-testid="tweetText"]')
            text = await text_elem.inner_text() if text_elem else ""
            
            # 提取推文链接以获取ID
            link_elem = await element.query_selector('a[href*="/status/"]')
            if not link_elem:
                return None
            
            href = await link_elem.get_attribute('href')
            tweet_id_match = re.search(r'/status/(\d+)', href)
            if not tweet_id_match:
                return None
            
            tweet_id = tweet_id_match.group(1)
            
            # 提取图片URLs
            image_urls = []
            image_elements = await element.query_selector_all('[data-testid="tweetPhoto"] img')
            for img_elem in image_elements:
                src = await img_elem.get_attribute('src')
                if src and 'twimg.com' in src:
                    # 获取原图链接（去掉尺寸参数）
                    original_url = src.split('?')[0] + '?format=jpg&name=large'
                    image_urls.append(original_url)
            
            # 提取用户显示名称
            user_name_elem = await element.query_selector('[data-testid="User-Name"]')
            user_display_name = await user_name_elem.inner_text() if user_name_elem else username
            
            # 提取时间（简化处理，使用当前时间）
            time_elem = await element.query_selector('time')
            date_str = await time_elem.get_attribute('datetime') if time_elem else None
            created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now()
            
            # 创建Tweet对象
            tweet = Tweet(
                tweet_id=tweet_id,
                username=username,
                user_display_name=user_display_name.split('\n')[0] if user_display_name else username,
                text=text,
                created_at=created_at,
                image_urls=image_urls,
                scraped_at=datetime.now()
            )
            
            return tweet
            
        except Exception as e:
            print(f"⚠️  解析推文元素失败: {e}")
            return None
    
    async def download_images(self, tweet: Tweet) -> List[str]:
        """
        下载推文中的图片
        
        Args:
            tweet: 包含image_urls的推文对象
            
        Returns:
            本地图片路径列表
        """
        if not tweet.image_urls:
            return []
        
        # 创建保存目录
        save_dir = Path(f"data/images/{tweet.username}/{tweet.tweet_id}")
        ensure_dir(str(save_dir))
        
        local_paths = []
        
        async with aiohttp.ClientSession() as session:
            for idx, url in enumerate(tweet.image_urls):
                try:
                    # 下载图片
                    async with session.get(url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            
                            # 保存到本地
                            file_path = save_dir / f"image_{idx}.jpg"
                            with open(file_path, 'wb') as f:
                                f.write(image_data)
                            
                            local_paths.append(str(file_path))
                            print(f"  📥 下载图片: {file_path}")
                        else:
                            print(f"  ⚠️  下载失败 (HTTP {response.status}): {url}")
                
                except Exception as e:
                    print(f"  ⚠️  下载图片失败: {e}")
                    continue
        
        return local_paths
    
    async def _simulate_human_behavior(self):
        """
        模拟人类浏览行为
        
        - 随机鼠标移动
        - 随机滚动（缓慢、自然）
        - 随机停顿
        """
        # 随机滚动
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 600)
            await self.page.mouse.wheel(0, scroll_amount)
            await self._random_delay(0.5, 1.5)
        
        # 随机鼠标移动
        await self.page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600),
            steps=random.randint(10, 30)
        )
    
    async def _random_delay(self, min_sec: float = None, max_sec: float = None):
        """随机延迟"""
        min_sec = min_sec if min_sec is not None else self.config.random_delay_min
        max_sec = max_sec if max_sec is not None else self.config.random_delay_max
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def _load_cookies_from_file(self):
        """从文件加载Cookies (支持JSON或Raw String)"""
        if not self.cookies_file.exists():
            return
            
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            cookies = []
            
            # 尝试解析为 JSON
            try:
                json_data = json.loads(content)
                if isinstance(json_data, dict):
                    json_data = json_data.get('cookies', [])
                if isinstance(json_data, list):
                    cookies = json_data
            except json.JSONDecodeError:
                # 解析失败，尝试作为 Raw String 处理 (key=value; key=value)
                print("ℹ️  检测到非 JSON 格式，尝试解析为 Raw Cookie String...")
                raw_items = content.split(';')
                for item in raw_items:
                    if '=' in item:
                        name, value = item.strip().split('=', 1)
                        cookies.append({
                            'name': name,
                            'value': value,
                            'domain': '.x.com',
                            'path': '/',
                            'secure': True
                        })

            if not cookies:
                print("⚠️  Cookies 文件内容为空或格式无法识别")
                return

            # 转换 cookie 格式 (Playwright 需要特定字段)
            formatted_cookies = []
            for cookie in cookies:
                # 必须包含 name, value
                if 'name' in cookie and 'value' in cookie:
                    new_cookie = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.x.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', True),
                        'httpOnly': cookie.get('httpOnly', False),
                        'sameSite': cookie.get('sameSite', 'Lax')
                    }
                    # 移除不支持的字段
                    if 'expirationDate' in cookie:
                        new_cookie['expires'] = cookie['expirationDate']
                    
                    formatted_cookies.append(new_cookie)
            
            if formatted_cookies:
                await self.context.add_cookies(formatted_cookies)
                print(f"✅ 成功注入 {len(formatted_cookies)} 个 Cookies")
            else:
                print("⚠️  没有找到有效的 Cookies")
                
        except Exception as e:
            print(f"❌ 读取 Cookies 文件失败: {e}")
            raise e
    
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# 测试code
if __name__ == "__main__":
    async def test():
        config = ScraperConfig(
            target_username="neilksethi",
            headless=False,
            max_retries=3
        )
        
        scraper = TwitterScraper(config)
        await scraper.initialize()
        
        try:
            tweets = await scraper.scrape_tweets("neilksethi", max_count=3)
            
            for i, tweet in enumerate(tweets, 1):
                print(f"\n--- 推文 {i} ---")
                print(f"ID: {tweet.tweet_id}")
                print(f"文本: {tweet.text[:100]}...")
                print(f"图片数: {len(tweet.image_urls)}")
                print(f"本地路径: {tweet.local_image_paths}")
        
        finally:
            await scraper.close()
    
    asyncio.run(test())
