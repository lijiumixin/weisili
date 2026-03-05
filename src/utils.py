"""
工具函数和数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json


# ==================== 数据结构 ====================

@dataclass
class Tweet:
    """Twitter推文数据结构"""
    
    # 基础信息
    tweet_id: str
    username: str
    user_display_name: str
    
    # 内容
    text: str
    created_at: datetime
    
    # 媒体
    image_urls: List[str] = field(default_factory=list)
    local_image_paths: List[str] = field(default_factory=list)
    
    # 元数据
    retweet_count: int = 0
    like_count: int = 0
    
    # 处理状态
    scraped_at: Optional[datetime] = None
    translated: bool = False
    published: bool = False
    published_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "tweet_id": self.tweet_id,
            "username": self.username,
            "user_display_name": self.user_display_name,
            "text": self.text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
        # 处理日期时间字段
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('scraped_at'), str):
            data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
        if isinstance(data.get('published_at'), str):
            data['published_at'] = datetime.fromisoformat(data['published_at'])
        
        return Tweet(**data)


@dataclass
class TranslatedContent:
    """翻译后的内容"""
    
    tweet_id: str
    title: str
    content: str
    translated_at: datetime
    
    # 质量元数据
    word_count: int = 0
    model_used: str = "unknown"
    
    def validate(self) -> tuple[bool, str]:
        """
        验证翻译内容是否符合要求
        
        Returns:
            (是否有效, 错误信息)
        """
        if len(self.title) > 20:
            return False, f"标题过长（{len(self.title)}字），应不超过20字"
        if not self.content or len(self.content) < 10:
            return False, "正文内容过短"
        return True, ""


@dataclass
class PublishResult:
    """发布结果"""
    
    tweet_id: str
    success: bool
    published_at: datetime
    
    # 错误信息（如果失败）
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # 元数据
    retry_count: int = 0
    screenshot_path: Optional[str] = None


@dataclass
class ScraperConfig:
    """爬虫配置"""
    
    target_username: str
    headless: bool = False
    timeout: int = 30000  # 超时时间（毫秒）
    max_retries: int = 3
    random_delay_min: int = 2  # 随机延迟最小值（秒）
    random_delay_max: int = 5  # 随机延迟最大值（秒）


# ==================== 异常类 ====================

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


# ==================== 工具函数 ====================

def ensure_dir(path: str):
    """确保目录存在"""
    from pathlib import Path
    Path(path).mkdir(parents=True, exist_ok=True)


def load_json(file_path: str, default=None):
    """加载JSON文件"""
    from pathlib import Path
    path = Path(file_path)
    if not path.exists():
        return default if default is not None else {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: str, data: dict, indent: int = 2):
    """保存JSON文件"""
    from pathlib import Path
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def format_timestamp(dt: datetime = None) -> str:
    """格式化时间戳"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# 测试代码
if __name__ == "__main__":
    # 测试Tweet数据结构
    tweet = Tweet(
        tweet_id="123456",
        username="testuser",
        user_display_name="Test User",
        text="This is a test tweet",
        created_at=datetime.now(),
        image_urls=["https://example.com/image.jpg"]
    )
    
    print("Tweet对象:", tweet)
    print("\n转换为字典:", tweet.to_dict())
    
    # 测试TranslatedContent验证
    content = TranslatedContent(
        tweet_id="123456",
        title="这是一个测试标题不超过20字",
        content="这是翻译后的正文内容",
        translated_at=datetime.now()
    )
    
    is_valid, error = content.validate()
    print(f"\n翻译内容验证: {is_valid}, 错误: {error}")
