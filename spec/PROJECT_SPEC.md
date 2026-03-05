# Project Specification - Twitter to WeChat Auto Publishing System

**项目名称**：Twitter → WeChat 自动发布系统  
**Spec版本**：v1.0  
**最后更新**：2025-11-25  
**开发模式**：Spec-Driven Development

---

## 📋 目录

1. [项目概述](#项目概述)
2. [数据结构定义](#数据结构定义)
3. [模块规范](#模块规范)
4. [接口定义](#接口定义)
5. [错误处理规范](#错误处理规范)
6. [配置规范](#配置规范)
7. [日志规范](#日志规范)
8. [测试规范](#测试规范)
9. [代码风格](#代码风格)

---

## 📌 项目概述

### 核心目标
自动化完成：Twitter内容爬取 → 翻译 → 微信公众号发布

### 关键约束
- **用户友好**：编程小白可用，配置简单
- **稳定可靠**：7x24小时运行，异常自动恢复
- **安全合规**：模拟真人行为，避免平台封禁
- **可维护性**：代码清晰，日志完善

---

## 🗂️ 数据结构定义

### 1. Tweet（推文对象）

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Tweet:
    """Twitter推文数据结构"""
    
    # 基础信息
    tweet_id: str              # 推文唯一ID
    username: str              # 用户名
    user_display_name: str     # 用户显示名称
    
    # 内容
    text: str                  # 推文文本（原始英文）
    created_at: datetime       # 发布时间
    
    # 媒体
    image_urls: List[str]      # 图片URL列表
    local_image_paths: List[str] = None  # 本地下载路径
    
    # 元数据
    retweet_count: int = 0     # 转发数
    like_count: int = 0        # 点赞数
    
    # 处理状态
    scraped_at: datetime = None      # 爬取时间
    translated: bool = False          # 是否已翻译
    published: bool = False           # 是否已发布
    published_at: datetime = None     # 发布时间
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "tweet_id": self.tweet_id,
            "username": self.username,
            "user_display_name": self.user_display_name,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
            "image_urls": self.image_urls,
            "local_image_paths": self.local_image_paths,
            "retweet_count": self.retweet_count,
            "like_count": self.like_count,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "translated": self.translated,
            "published": self.published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Tweet':
        """从字典创建对象"""
        # 实现字典到对象的转换
        pass
```

### 2. TranslatedContent（翻译内容）

```python
@dataclass
class TranslatedContent:
    """翻译后的内容"""
    
    tweet_id: str              # 对应的推文ID
    title: str                 # 生成的标题（≤20字）
    content: str               # 翻译后的正文
    translated_at: datetime    # 翻译时间
    
    # 质量元数据
    word_count: int            # 字数
    model_used: str            # 使用的模型（如gpt-4）
    
    def validate(self) -> bool:
        """验证翻译内容是否符合要求"""
        if len(self.title) > 20:
            return False
        if not self.content or len(self.content) < 10:
            return False
        return True
```

### 3. PublishResult（发布结果）

```python
@dataclass
class PublishResult:
    """发布结果"""
    
    tweet_id: str              # 推文ID
    success: bool              # 是否成功
    published_at: datetime     # 发布时间
    
    # 错误信息（如果失败）
    error_message: str = None
    error_type: str = None     # 错误类型（如LOGIN_EXPIRED）
    
    # 元数据
    retry_count: int = 0       # 重试次数
    screenshot_path: str = None  # 错误截图路径
```

### 4. ScraperConfig（爬虫配置）

```python
@dataclass
class ScraperConfig:
    """爬虫配置"""
    
    target_username: str
    headless: bool = False
    timeout: int = 30000       # 超时时间（毫秒）
    max_retries: int = 3
    random_delay_min: int = 2  # 随机延迟最小值（秒）
    random_delay_max: int = 5  # 随机延迟最大值（秒）
```

---

## 🔧 模块规范

## Module 1: TwitterScraper (twitter_scraper.py)

### 职责
- 访问指定Twitter账号主页
- 爬取最新推文（文本+图片）
- 实现反反爬措施
- 下载图片到本地

### 类定义

```python
class TwitterScraper:
    """Twitter内容爬虫"""
    
    def __init__(self, config: ScraperConfig):
        """
        初始化爬虫
        
        Args:
            config: 爬虫配置对象
        """
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
        
    async def initialize(self):
        """
        初始化Playwright浏览器
        
        - 设置User-Agent
        - 配置浏览器参数
        - 应用stealth模式
        """
        pass
    
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
            
        实现要点：
        1. 访问 https://x.com/{username}
        2. 等待页面加载完成（检测article元素）
        3. 提取推文信息：
           - tweet ID（从URL或data-testid提取）
           - 文本内容
           - 图片URL
           - 发布时间
           - 互动数据
        4. 如果提供since_id，过滤掉旧推文
        5. 下载图片并保存本地路径
        """
        pass
    
    async def download_images(self, tweet: Tweet) -> List[str]:
        """
        下载推文中的图片
        
        Args:
            tweet: 包含image_urls的推文对象
            
        Returns:
            本地图片路径列表
            
        保存路径格式：
        data/images/{username}/{tweet_id}/image_0.jpg
        data/images/{username}/{tweet_id}/image_1.jpg
        
        实现要点：
        1. 创建目录结构
        2. 使用aiohttp异步下载
        3. 保持原图质量（下载高清版本）
        4. 处理下载失败（重试机制）
        """
        pass
    
    async def _simulate_human_behavior(self):
        """
        模拟人类浏览行为
        
        - 随机鼠标移动
        - 随机滚动（缓慢、自然）
        - 随机停顿
        """
        pass
    
    async def _random_delay(self, min_sec: float = None, max_sec: float = None):
        """随机延迟"""
        import random, asyncio
        min_sec = min_sec or self.config.random_delay_min
        max_sec = max_sec or self.config.random_delay_max
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()


class ScraperException(Exception):
    """爬虫异常"""
    pass
```

### 反反爬实现细节

```python
# Playwright初始化参数
browser_args = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
]

# User-Agent池（轮换使用）
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # ... 更多
]

# 修改navigator.webdriver
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
""")
```

---

## Module 2: Translator (translator.py)

### 职责
- 调用OpenAI API翻译推文
- 生成吸引人的标题
- 确保翻译质量

### 类定义

```python
class Translator:
    """内容翻译器"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", config: dict = None):
        """
        初始化翻译器
        
        Args:
            api_key: OpenAI API密钥
            model: 使用的模型
            config: 翻译配置（包含prompt模板等）
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.config = config or {}
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """
        加载翻译提示词模板
        
        从config/translation_prompt.txt读取
        如果不存在，使用默认模板
        """
        pass
    
    async def translate_tweet(self, tweet: Tweet) -> TranslatedContent:
        """
        翻译推文
        
        Args:
            tweet: 待翻译的推文对象
            
        Returns:
            翻译后的内容对象
            
        Raises:
            TranslationException: 翻译失败时抛出
            
        实现要点：
        1. 构建prompt（插入推文文本）
        2. 调用OpenAI API
        3. 解析JSON响应
        4. 验证结果（标题长度、内容完整性）
        5. 如果验证失败，重试或调整
        """
        pass
    
    def _build_prompt(self, tweet_text: str) -> str:
        """
        构建翻译提示词
        
        替换模板中的 {tweet_text} 占位符
        """
        return self.prompt_template.replace("{tweet_text}", tweet_text)
    
    async def _call_openai_api(self, prompt: str) -> dict:
        """
        调用OpenAI API
        
        Returns:
            解析后的JSON响应 {"title": "...", "content": "..."}
        """
        pass
    
    def validate_translation(self, content: TranslatedContent) -> tuple[bool, str]:
        """
        验证翻译结果
        
        Returns:
            (是否有效, 错误信息)
            
        验证规则：
        - 标题不超过20字
        - 正文至少10字
        - 无乱码或格式错误
        """
        pass


class TranslationException(Exception):
    """翻译异常"""
    pass
```

### 提示词模板规范

**文件路径**：`config/translation_prompt.txt`

```text
你是一位专业的宏观经济分析师和金融翻译专家。请将以下英文推文翻译成中文。

【翻译要求】
1. 风格：{style}
2. 术语处理：
   - Fed → 美联储
   - Treasury → 美国财政部/美债
   - GDP → 国内生产总值（首次出现）或GDP
   - CPI → 消费者物价指数（首次出现）或CPI
   - 保持专业准确性
3. 语气：保持客观中立，忠实原文观点
4. 标题：提炼核心观点，20字以内，吸引眼球但不夸张
5. 正文：完整翻译，段落清晰

【原文】
{tweet_text}

【输出格式】
请严格按照JSON格式回复（不要包含其他内容）：
```json
{
  "title": "这里是标题",
  "content": "这里是正文"
}
```
```

---

## Module 3: WeChatPublisher (wechat_publisher.py)

### 职责
- 登录微信公众号后台
- 自动发布图文消息
- 模拟真人操作
- 处理登录态异常

### 类定义

```python
class WeChatPublisher:
    """微信公众号发布器"""
    
    # URL常量
    LOGIN_URL = "https://mp.weixin.qq.com/"
    
    # 选择器常量（根据实际页面调整）
    SELECTOR_LOGIN_QRCODE = "img.qrcode_login_img"
    SELECTOR_MENU_ITEM = "text=图文消息"  # 或使用更精确的选择器
    SELECTOR_IMAGE_UPLOAD = "text=选择或拖拽图片到此处"
    SELECTOR_LOCAL_UPLOAD = "text=本地上传"
    SELECTOR_TITLE_INPUT = 'input[placeholder*="标题"]'
    SELECTOR_CONTENT_EDITOR = ".editor-content"  # 内容编辑区
    SELECTOR_PUBLISH_BUTTON = "button:has-text('发布')"
    
    def __init__(self, config: dict, headless: bool = False):
        """
        初始化发布器
        
        Args:
            config: 微信配置（包含state_file路径等）
            headless: 是否无头模式
        """
        self.config = config
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.state_file = config.get("state_file", "config/wechat_state.json")
    
    async def initialize(self):
        """初始化浏览器"""
        pass
    
    async def login(self, manual: bool = True) -> bool:
        """
        登录微信公众号
        
        Args:
            manual: 是否手动扫码登录（首次必须为True）
            
        Returns:
            是否登录成功
            
        实现要点：
        1. 访问登录页
        2. 如果有保存的state，尝试加载
        3. 如果manual=True或state无效：
           - 显示二维码
           - 等待用户扫码（最多3分钟）
           - 检测登录成功（URL变化或特定元素出现）
        4. 保存登录态到state_file
        """
        pass
    
    async def check_login_status(self) -> bool:
        """
        检查当前登录状态
        
        Returns:
            是否已登录
            
        实现：
        访问后台首页，检查是否需要重新登录
        """
        pass
    
    async def publish_article(
        self, 
        title: str, 
        content: str, 
        images: List[str],
        publish_now: bool = True
    ) -> PublishResult:
        """
        发布图文消息
        
        Args:
            title: 文章标题
            content: 文章正文
            images: 本地图片路径列表
            publish_now: True=立即发布，False=保存草稿
            
        Returns:
            发布结果对象
            
        Raises:
            PublishException: 发布失败时抛出
            
        实现流程（严格按照截图）：
        1. 检查登录状态
        2. 点击左侧菜单"图文消息"
        3. 等待新页面加载
        4. 上传图片：
           a. hover到"选择或拖拽图片到此处"
           b. 等待下拉菜单出现
           c. 点击"本地上传"
           d. 使用page.set_input_files()选择文件
           e. 等待上传完成
        5. 填写标题（模拟打字）
        6. 填写正文（模拟打字）
        7. 点击"发布"或"保存草稿"
        8. 等待发布成功提示
        9. 截图保存（成功或失败都截图）
        """
        pass
    
    async def _click_with_human_simulation(self, selector: str):
        """
        模拟真人点击
        
        1. 移动鼠标到元素附近
        2. 微调到元素中心（加随机偏移）
        3. 短暂停顿
        4. 点击
        5. 随机延迟
        """
        element = await self.page.wait_for_selector(selector)
        box = await element.bounding_box()
        
        # 随机偏移
        import random
        offset_x = random.uniform(-5, 5)
        offset_y = random.uniform(-5, 5)
        
        # 移动鼠标
        await self.page.mouse.move(
            box['x'] + box['width'] / 2 + offset_x,
            box['y'] + box['height'] / 2 + offset_y,
            steps=random.randint(10, 30)  # 分步移动
        )
        
        await self._random_delay(0.3, 0.8)
        await element.click()
        await self._random_delay(1, 2)
    
    async def _type_with_human_speed(self, selector: str, text: str):
        """
        模拟人类打字速度
        
        逐字输入，每个字随机延迟50-150ms
        """
        element = await self.page.wait_for_selector(selector)
        await element.click()
        
        import random
        for char in text:
            await element.type(char, delay=random.randint(50, 150))
    
    async def _upload_images(self, image_paths: List[str]):
        """
        上传图片列表
        
        按照真人操作流程
        """
        pass
    
    async def _random_delay(self, min_sec: float, max_sec: float):
        """随机延迟"""
        import random, asyncio
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def save_state(self):
        """保存登录态"""
        state = await self.context.storage_state()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    async def load_state(self) -> bool:
        """加载登录态"""
        if not os.path.exists(self.state_file):
            return False
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            # 使用state创建新的context
            return True
        except:
            return False
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()


class PublishException(Exception):
    """发布异常"""
    pass
```

---

## Module 4: TaskScheduler (scheduler.py)

### 职责
- 定时触发爬取任务
- 协调各模块执行完整流程
- 处理多条推文的间隔发布

### 类定义

```python
class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化调度器
        
        加载配置并初始化各模块
        """
        self.config = self._load_config(config_path)
        self.scraper = None
        self.translator = None
        self.publisher = None
        self.notifier = Notifier(self.config['notification'], self.config['logging'])
        self.published_tweets = self._load_published_tweets()
    
    def _load_config(self, path: str) -> dict:
        """加载YAML配置"""
        pass
    
    def _load_published_tweets(self) -> set:
        """
        加载已发布推文ID集合
        
        从config/published_tweets.json读取
        """
        pass
    
    def _save_published_tweet(self, tweet_id: str):
        """保存已发布推文ID"""
        pass
    
    async def initialize_modules(self):
        """初始化各模块"""
        # 初始化scraper
        scraper_config = ScraperConfig(
            target_username=self.config['twitter']['target_username'],
            headless=self.config['runtime']['headless'],
            max_retries=self.config['runtime']['max_retries']
        )
        self.scraper = TwitterScraper(scraper_config)
        await self.scraper.initialize()
        
        # 初始化translator
        self.translator = Translator(
            api_key=os.getenv('OPENAI_API_KEY'),
            model=self.config['openai']['model'],
            config=self.config['translation']
        )
        
        # 初始化publisher
        self.publisher = WeChatPublisher(
            config=self.config['wechat'],
            headless=self.config['runtime']['headless']
        )
        await self.publisher.initialize()
    
    async def run_pipeline(self):
        """
        执行完整流程
        
        1. 爬取新推文
        2. 过滤已发布
        3. 翻译内容
        4. 间隔发布到微信
        
        异常处理：
        - 每个步骤失败都记录日志
        - 部分失败不影响其他推文
        """
        try:
            self.notifier.log('INFO', '开始执行爬取任务...')
            
            # 1. 爬取推文
            username = self.config['twitter']['target_username']
            tweets = await self.scraper.scrape_tweets(username, max_count=10)
            self.notifier.log('INFO', f'爬取到 {len(tweets)} 条推文')
            
            # 2. 过滤已发布
            new_tweets = [t for t in tweets if t.tweet_id not in self.published_tweets]
            if not new_tweets:
                self.notifier.log('INFO', '没有新推文需要发布')
                return
            
            self.notifier.log('INFO', f'发现 {len(new_tweets)} 条新推文')
            
            # 3. 逐条处理
            for i, tweet in enumerate(new_tweets, 1):
                try:
                    # 翻译
                    self.notifier.log('INFO', f'[{i}/{len(new_tweets)}] 正在翻译推文 {tweet.tweet_id}...')
                    translated = await self.translator.translate_tweet(tweet)
                    
                    # 发布
                    self.notifier.log('INFO', f'[{i}/{len(new_tweets)}] 正在发布到微信...')
                    result = await self.publisher.publish_article(
                        title=translated.title,
                        content=translated.content,
                        images=tweet.local_image_paths or []
                    )
                    
                    if result.success:
                        self.notifier.log('INFO', f'✅ 发布成功: {translated.title}')
                        self._save_published_tweet(tweet.tweet_id)
                    else:
                        self.notifier.log('ERROR', f'❌ 发布失败: {result.error_message}')
                        self.notifier.notify_desktop('发布失败', f'推文 {tweet.tweet_id[:10]}... 发布失败')
                    
                    # 如果还有更多推文，等待随机间隔
                    if i < len(new_tweets):
                        delay = random.randint(
                            self.config['wechat']['publish_interval_min'] * 60,
                            self.config['wechat']['publish_interval_max'] * 60
                        )
                        self.notifier.log('INFO', f'等待 {delay}秒 后发布下一条...')
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    self.notifier.log('ERROR', f'处理推文 {tweet.tweet_id} 时出错: {str(e)}')
                    self.notifier.notify_desktop('处理错误', f'推文处理失败，请查看日志')
                    continue  # 继续处理下一条
        
        except Exception as e:
            self.notifier.log('CRITICAL', f'执行流程时发生严重错误: {str(e)}')
            self.notifier.notify_desktop('严重错误', '系统运行异常，请查看日志')
    
    def schedule_tasks(self):
        """
        安排定时任务
        
        使用schedule库，每15-30分钟随机间隔执行
        """
        import schedule
        
        def run_with_random_interval():
            """执行任务并安排下次运行"""
            # 执行任务
            asyncio.run(self.run_pipeline())
            
            # 计算下次运行时间（15-30分钟随机）
            next_run_minutes = random.randint(
                self.config['twitter']['scrape_interval_min'],
                self.config['twitter']['scrape_interval_max']
            )
            self.notifier.log('INFO', f'下次运行时间: {next_run_minutes}分钟后')
            
            # 清除旧任务，安排新任务
            schedule.clear()
            schedule.every(next_run_minutes).minutes.do(run_with_random_interval)
        
        # 首次立即执行
        schedule.every(0).seconds.do(run_with_random_interval)
        
        # 持续运行
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    async def cleanup(self):
        """清理资源"""
        if self.scraper:
            await self.scraper.close()
        if self.publisher:
            await self.publisher.close()
```

---

## Module 5: Notifier (notifier.py)

### 职责
- 统一的日志记录
- Windows桌面通知
- 日志文件管理

### 类定义

```python
import logging
from logging.handlers import TimedRotatingFileHandler
from win10toast import ToastNotifier
from pathlib import Path

class Notifier:
    """通知与日志管理器"""
    
    def __init__(self, notification_config: dict, logging_config: dict):
        """
        初始化通知器
        
        Args:
            notification_config: 通知配置
            logging_config: 日志配置
        """
        self.notification_config = notification_config
        self.logging_config = logging_config
        self.toaster = ToastNotifier()
        self._setup_logging()
    
    def _setup_logging(self):
        """
        配置日志系统
        
        - 控制台输出（彩色）
        - 文件输出（按天分割）
        """
        log_level = getattr(logging, self.logging_config.get('level', 'INFO'))
        
        # 创建logger
        self.logger = logging.getLogger('TwitterToWeChat')
        self.logger.setLevel(log_level)
        
        # 创建logs目录
        Path('logs').mkdir(exist_ok=True)
        
        # 文件handler（按天分割）
        file_handler = TimedRotatingFileHandler(
            filename='logs/app.log',
            when='midnight',
            interval=1,
            backupCount=30,  # 保留30天
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台handler（彩色）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 使用colorlog实现彩色输出
        try:
            from colorlog import ColoredFormatter
            console_formatter = ColoredFormatter(
                '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(console_formatter)
        except ImportError:
            console_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log(self, level: str, message: str):
        """
        记录日志
        
        Args:
            level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            message: 日志消息
        """
        log_func = getattr(self.logger, level.lower())
        log_func(message)
    
    def notify_desktop(self, title: str, message: str, duration: int = 10):
        """
        发送Windows桌面通知
        
        Args:
            title: 通知标题
            message: 通知内容
            duration: 显示时长（秒）
        """
        if not self.notification_config.get('desktop_enabled', True):
            return
        
        try:
            self.toaster.show_toast(
                title=title,
                msg=message,
                duration=duration,
                icon_path=None,  # 可以设置自定义图标
                threaded=True
            )
        except Exception as e:
            self.logger.error(f'桌面通知发送失败: {str(e)}')
```

---

## Module 6: ConfigManager (config_manager.py)

### 职责
- 加载和验证配置文件
- 管理环境变量
- 提供配置访问接口

### 类定义

```python
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        load_dotenv()  # 加载.env文件
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> dict:
        """加载YAML配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 替换环境变量占位符
        config = self._replace_env_vars(config)
        return config
    
    def _replace_env_vars(self, obj):
        """
        递归替换配置中的环境变量占位符
        
        ${VAR_NAME} → os.getenv('VAR_NAME')
        """
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_name = obj[2:-1]
            return os.getenv(var_name, '')
        else:
            return obj
    
    def _validate_config(self):
        """
        验证配置完整性
        
        检查必需的配置项是否存在
        """
        required_keys = [
            'twitter.target_username',
            'openai.api_key',
            'wechat.login_url',
        ]
        
        for key in required_keys:
            if not self._get_nested(self.config, key):
                raise ValueError(f'缺少必需配置项: {key}')
    
    def _get_nested(self, d: dict, key: str):
        """获取嵌套字典的值"""
        keys = key.split('.')
        for k in keys:
            d = d.get(k)
            if d is None:
                return None
        return d
    
    def get(self, key: str, default=None):
        """
        获取配置值
        
        Args:
            key: 配置键（支持点分隔的嵌套键，如 'twitter.target_username'）
            default: 默认值
        """
        value = self._get_nested(self.config, key)
        return value if value is not None else default
```

---

## 📄 配置文件模板

### config/config.yaml

```yaml
# Twitter配置
twitter:
  target_username: "neilksethi"
  scrape_interval_min: 15
  scrape_interval_max: 30

# OpenAI配置
openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

# 翻译配置
translation:
  prompt_template_file: "config/translation_prompt.txt"
  style: "专业、严谨，适合国内金融从业者阅读"

# 微信公众号配置
wechat:
  login_url: "https://mp.weixin.qq.com/"
  state_file: "config/wechat_state.json"
  publish_interval_min: 3
  publish_interval_max: 10

# 运行模式
runtime:
  headless: false
  screenshot_on_error: true
  max_retries: 3

# 通知配置
notification:
  desktop_enabled: true

# 日志配置
logging:
  level: "INFO"
  file_rotation: "daily"
  max_log_size_mb: 10
```

---

## 🚨 错误处理规范

### 异常层次结构

```python
class AppException(Exception):
    """应用基础异常"""
    pass

class ScraperException(AppException):
    """爬虫异常"""
    pass

class TranslationException(AppException):
    """翻译异常"""
    pass

class PublishException(AppException):
    """发布异常"""
    pass

class ConfigException(AppException):
    """配置异常"""
    pass
```

### 错误处理策略

| 错误类型 | 处理策略 | 通知级别 |
|---------|---------|---------|
| 网络超时 | 重试3次，间隔递增 | WARNING |
| 爬取失败 | 记录日志，跳过本次 | ERROR |
| 翻译API失败 | 重试2次，失败则跳过 | ERROR |
| 登录过期 | 通知用户，暂停任务 | CRITICAL + Desktop |
| 发布失败 | 截图，记录详情，跳过 | ERROR + Desktop |
| 配置错误 | 立即退出 | CRITICAL |

### 重试机制

```python
async def retry_on_failure(func, max_retries=3, backoff_factor=2):
    """
    失败重试装饰器
    
    Args:
        func: 异步函数
        max_retries: 最大重试次数
        backoff_factor: 退避因子（每次重试延迟倍数）
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = backoff_factor ** attempt
            await asyncio.sleep(delay)
```

---

## 📊 日志规范

### 日志级别使用

- **DEBUG**：详细的调试信息（仅开发时使用）
- **INFO**：正常流程信息
  - 任务开始/结束
  - 爬取到X条推文
  - 翻译完成
  - 发布成功
- **WARNING**：警告信息
  - 重试操作
  - 配置项缺失但有默认值
- **ERROR**：错误信息
  - 爬取失败
  - 翻译失败
  - 发布失败
- **CRITICAL**：严重错误
  - 登录过期
  - 系统崩溃

### 日志格式示例

```
2025-11-25 02:30:15 - INFO - 开始执行爬取任务...
2025-11-25 02:30:20 - INFO - 爬取到 5 条推文
2025-11-25 02:30:21 - INFO - 发现 2 条新推文
2025-11-25 02:30:22 - INFO - [1/2] 正在翻译推文 1859234567890...
2025-11-25 02:30:25 - INFO - [1/2] 正在发布到微信...
2025-11-25 02:30:35 - INFO - ✅ 发布成功: 美联储释放鸽派信号，市场反弹
2025-11-25 02:30:36 - INFO - 等待 240秒 后发布下一条...
```

---

## 🧪 测试规范

### 单元测试

每个模块都应有对应的测试文件：

```python
# tests/test_scraper.py
import pytest
from src.twitter_scraper import TwitterScraper, ScraperConfig

@pytest.mark.asyncio
async def test_scrape_tweets():
    """测试爬取推文功能"""
    config = ScraperConfig(target_username="neilksethi", headless=True)
    scraper = TwitterScraper(config)
    await scraper.initialize()
    
    tweets = await scraper.scrape_tweets("neilksethi", max_count=5)
    
    assert len(tweets) > 0
    assert tweets[0].tweet_id is not None
    assert len(tweets[0].text) > 0
    
    await scraper.close()
```

### 集成测试

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_pipeline():
    """测试完整流程"""
    # 1. 爬取
    # 2. 翻译
    # 3. 发布（使用mock）
    pass
```

---

## 💻 代码风格

### Python风格指南

遵循 **PEP 8** 规范：

- 使用4空格缩进
- 行长度不超过100字符
- 类名使用 `PascalCase`
- 函数名使用 `snake_case`
- 常量使用 `UPPER_SNAKE_CASE`

### 文档字符串

所有公共函数和类都必须有文档字符串：

```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数简短描述（一行）
    
    详细描述（可选，多行）
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ExceptionType: 何时抛出此异常
    """
    pass
```

### 类型注解

所有函数参数和返回值都应有类型注解：

```python
from typing import List, Optional, Dict

async def scrape_tweets(
    username: str, 
    since_id: Optional[str] = None,
    max_count: int = 10
) -> List[Tweet]:
    pass
```

---

## 📁 项目结构检查清单

创建项目时需要的所有文件和目录：

```
✅ weisili/
  ✅ .env
  ✅ .gitignore
  ✅ README.md
  ✅ requirements.txt
  ✅ main.py
  ✅ config/
    ✅ config.yaml
    ✅ translation_prompt.txt
    ✅ published_tweets.json (空JSON数组)
    ✅ wechat_state.json (首次运行后生成)
  ✅ data/
    ✅ images/ (自动创建子目录)
  ✅ logs/ (自动创建)
  ✅ screenshots/ (自动创建)
  ✅ src/
    ✅ __init__.py
    ✅ config_manager.py
    ✅ twitter_scraper.py
    ✅ translator.py
    ✅ wechat_publisher.py
    ✅ scheduler.py
    ✅ notifier.py
    ✅ utils.py
  ✅ spec/
    ✅ PROJECT_SPEC.md (本文档)
  ✅ tests/
    ✅ __init__.py
    ✅ test_scraper.py
    ✅ test_translator.py
    ✅ test_publisher.py
```

---

## 🎯 开发检查清单

按以下顺序开发：

### Phase 1: 基础设施
- [ ] 创建项目结构
- [ ] 编写 `config_manager.py`
- [ ] 编写 `notifier.py`
- [ ] 编写 `utils.py`（工具函数）
- [ ] 创建配置文件模板

### Phase 2: 核心模块
- [ ] 实现 `twitter_scraper.py`
  - [ ] 基础爬取功能
  - [ ] 反反爬措施
  - [ ] 图片下载
- [ ] 实现 `translator.py`
  - [ ] OpenAI API调用
  - [ ] 提示词管理
  - [ ] 结果验证

### Phase 3: 发布模块
- [ ] 实现 `wechat_publisher.py`
  - [ ] 登录流程
  - [ ] 图片上传
  - [ ] 内容发布
  - [ ] 真人模拟

### Phase 4: 调度与集成
- [ ] 实现 `scheduler.py`
- [ ] 编写 `main.py`
- [ ] 集成测试

### Phase 5: 完善与优化
- [ ] 编写单元测试
- [ ] 完善错误处理
- [ ] 编写 `README.md`
- [ ] 用户测试与调优

---

## 📝 变更记录

| 版本 | 日期 | 变更内容 |
|-----|------|---------|
| v1.0 | 2025-11-25 | 初始版本，定义核心规范 |

---

**文档结束**

严格按照本规范开发，确保代码质量和可维护性。
