"""
微信公众号发布模块
使用 Playwright Codegen验证的选择器 + expect_file_chooser 上传文件
"""

import asyncio
import random
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


@dataclass
class PublishResult:
    """发布结果"""
    tweet_id: str
    success: bool
    published_at: datetime
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    screenshot_path: Optional[str] = None


class PublishException(Exception):
    """发布异常"""
    pass


class WeChatPublisher:
    """微信公众号发布器"""
    
    LOGIN_URL = "https://mp.weixin.qq.com/"
    
    def __init__(self, config: dict, headless: bool = False):
        self.config = config
        self.headless = headless
        self.state_file = config.get('state_file', 'config/wechat_state.json')
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def initialize(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        state_loaded = await self._load_state()
        
        if state_loaded:
            print("✅ 加载已保存的登录态")
        else:
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
        
        self.page = await self.context.new_page()
        
        try:
            await self.page.goto(self.LOGIN_URL, wait_until='networkidle', timeout=30000)
        except:
            pass
    
    async def _load_state(self) -> bool:
        """加载保存的登录态"""
        state_path = Path(self.state_file)
        if state_path.exists():
            try:
                self.context = await self.browser.new_context(
                    storage_state=str(state_path),
                    viewport={'width': 1920, 'height': 1080}
                )
                return True
            except:
                return False
        return False
    
    async def save_state(self):
        """保存登录态"""
        if self.context:
            state_path = Path(self.state_file)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=str(state_path))
            print(f"✅ 登录态已保存")
    
    async def login(self, manual: bool = True, timeout: int = 180) -> bool:
        """登录微信公众号"""
        try:
            print("🔐 开始登录微信公众号...")
            await self.page.goto(self.LOGIN_URL, wait_until='networkidle')
            
            if manual:
                print("\n👉 请在浏览器中扫码登录...")
                try:
                    await self.page.wait_for_url(
                        lambda url: 'home' in url or 'cgi-bin' in url,
                        timeout=timeout * 1000
                    )
                    print("✅ 登录成功")
                    await self.save_state()
                    return True
                except:
                    return False
            else:
                return await self._is_logged_in()
        except Exception as e:
            raise PublishException(f"登录失败: {str(e)}")
    
    async def _is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            current_url = self.page.url
            return any(path in current_url for path in ['home', 'cgi-bin/home', 'appmsg'])
        except:
            return False
    
    async def check_login_status(self) -> bool:
        """检查当前登录状态"""
        try:
            await self.page.goto(self.LOGIN_URL, wait_until='networkidle', timeout=30000)
            return await self._is_logged_in()
        except:
            return False
    
    async def publish_article(
        self, 
        title: str, 
        content: str, 
        images: List[str],
        publish_now: bool = False
    ) -> PublishResult:
        """发布图文消息"""
        tweet_id = f"publish_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            print(f"📤 开始发布文章: {title}")
            
            await self._navigate_to_article_editor()
            
            if images:
                await self._upload_images(images)
            
            await self._fill_title(title)
            await self._fill_content(content)
            
            if publish_now:
                await self._click_publish()
            else:
                await self._click_save_draft()
            
            await self._random_delay(2, 3)
            screenshot_path = await self._take_screenshot("success")
            
            print(f"✅ 发布成功: {title}")
            
            return PublishResult(
                tweet_id=tweet_id,
                success=True,
                published_at=datetime.now(),
                screenshot_path=screenshot_path
            )
            
        except Exception as e:
            screenshot_path = await self._take_screenshot("error")
            print(f"❌ 发布失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return PublishResult(
                tweet_id=tweet_id,
                success=False,
                published_at=datetime.now(),
                error_message=str(e),
                error_type=type(e).__name__,
                screenshot_path=screenshot_path
            )
    
    async def _navigate_to_article_editor(self):
        """导航到图文消息(贴图)编辑页"""
        try:
            print("  📍 点击贴图菜单...")
            await self._random_delay(2, 3)
            
            # Using get_by_text which is more robust than nth-child since layout changes
            async with self.context.expect_page() as new_page_info:
                # Based on the user's screenshot, '贴图' is a text button in the creation menu
                # Using get_by_text to specifically find "贴图" exactly.
                await self.page.get_by_text("贴图", exact=True).click()
                print("  ✅ 已点击贴图菜单")
            
            new_page = await new_page_info.value
            self.page = new_page
            print("  ✅ 新标签页已打开")
            
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            print("  ✅ 新页面加载完成")
                
        except Exception as e:
            raise PublishException(f"导航到编辑页失败: {e}")
    
    async def _upload_images(self, image_paths: List[str]):
        """上传图片列表 - 使用expect_file_chooser"""
        if not image_paths:
            print("  ℹ️  没有图片需要上传")
            return
            
        try:
            print(f"  📤 准备上传 {len(image_paths)} 张图片...")
            await self._random_delay(3, 5)
            
            for idx, image_path in enumerate(image_paths, 1):
                if not Path(image_path).exists():
                    print(f"  ⚠️  图片不存在，跳过: {image_path}")
                    continue
                
                print(f"\n  📷 上传第 {idx}/{len(image_paths)} 张图片: {Path(image_path).name}")
                
                try:
                    if idx == 1:
                        # 第1张图片
                        upload_area = self.page.get_by_text("选择或拖拽图片 到此处 本地上传 从图片库选择 微信扫码上传 AI 配图")
                        await upload_area.click()
                        print("    ✓ 已点击上传区域")
                        await self._random_delay(1, 2)
                        
                        local_upload_btn = self.page.locator("#js_content_top label")
                        
                        # 关键：使用expect_file_chooser
                        async with self.page.expect_file_chooser() as fc_info:
                            await local_upload_btn.click()
                            print("    ✓ 已点击'本地上传'")
                        
                        file_chooser = await fc_info.value
                        await self._random_delay(0.5, 1)
                        await file_chooser.set_files(str(Path(image_path).absolute()))
                        print(f"    ✅ 第1张图片已选择")
                        
                    else:
                        # 第2+张图片
                        add_btn = self.page.locator(".image-selector__bottom-add")
                        await add_btn.click()
                        print("    ✓ 已点击 '+' 按钮")
                        await self._random_delay(1, 2)
                        
                        local_upload_btn = self.page.get_by_role("list").locator("label")
                        
                        # 关键：使用expect_file_chooser
                        async with self.page.expect_file_chooser() as fc_info:
                            await local_upload_btn.click()
                            print("    ✓ 已点击'本地上传'（下拉菜单)")
                        
                        file_chooser = await fc_info.value
                        await self._random_delay(0.5, 1)
                        await file_chooser.set_files(str(Path(image_path).absolute()))
                        print(f"    ✅ 第{idx}张图片已选择")
                    
                    print("    ⏱️  等待上传处理...")
                    await self._random_delay(5, 8)
                    
                    if idx < len(image_paths):
                        wait_time = random.randint(2, 4)
                        print(f"    ⏱️  等待 {wait_time} 秒...")
                        await asyncio.sleep(wait_time)
                
                except Exception as e:
                    print(f"    ❌ 上传图片失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
        except Exception as e:
            print(f"  ⚠️  图片上传过程出错: {e}")
    
    async def _fill_title(self, title: str):
        """填写标题"""
        try:
            print(f"  ✍️  填写标题: {title}")
            
            title_input = self.page.get_by_placeholder("请在这里输入标题（选填）")
            await title_input.click()
            await self._random_delay(0.5, 1)
            await title_input.fill(title)
            
            print("  ✅ 标题填写完成")
            
        except Exception as e:
            raise PublishException(f"填写标题失败: {e}")
    
    async def _fill_content(self, content: str):
        """填写正文"""
        try:
            print(f"  ✍️  填写正文 ({len(content)}字)...")
            
            content_editor = self.page.locator("div").filter(
                has_text=re.compile(r"^填写描述信息，让大家了解更多内容$")
            ).nth(1)
            
            await content_editor.click()
            await self._random_delay(0.5, 1)
            await content_editor.fill(content)
            
            print("  ✅ 正文填写完成")
            
        except Exception as e:
            raise PublishException(f"填写正文失败: {e}")
    
    async def _click_publish(self):
        """点击发表按钮"""
        try:
            print("  🚀 点击发表...")
            
            publish_btn = self.page.get_by_role("button", name="发表")
            await publish_btn.click()
            await self._random_delay(2, 3)
            
            print("  ✅ 点击发表完成")
            
        except Exception as e:
            raise PublishException(f"点击发表失败: {e}")
    
    async def _click_save_draft(self):
        """保存为草稿"""
        try:
            print("  💾 保存为草稿...")
            
            draft_button = self.page.get_by_role("button", name="保存为草稿")
            await draft_button.click()
            await self._random_delay(2, 3)
            
            print("  ✅ 草稿保存成功")
            
        except Exception as e:
            raise PublishException(f"保存草稿失败: {e}")
    
    async def _random_delay(self, min_sec: float, max_sec: float):
        """随机延迟"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def _take_screenshot(self, prefix: str = "screenshot") -> str:
        """截图"""
        try:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = screenshots_dir / f"{prefix}_{timestamp}.png"
            await self.page.screenshot(path=str(filepath))
            return str(filepath)
        except:
            return ""
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
