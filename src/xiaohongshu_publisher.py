"""
小红书发布模块
使用 Playwright 模拟真人操作发布内容到小红书创作者平台
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


class XiaohongshuPublisher:
    """小红书发布器"""
    
    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image"
    
    def __init__(self, config: dict, headless: bool = False):
        self.config = config
        self.headless = headless
        self.state_file = config.get('state_file', 'config/xiaohongshu_state.json')
        self.fixed_tags = config.get('fixed_tags', '#股票 #宏观 #投资 #炒股 #投资观察')
        
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
            await self.page.goto(self.PUBLISH_URL, wait_until='networkidle', timeout=30000)
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
        """登录小红书创作者平台"""
        try:
            print("🔐 开始登录小红书创作者平台...")
            await self.page.goto(self.PUBLISH_URL, wait_until='networkidle')
            
            if manual:
                print("\n👉 请在浏览器中完成登录...")
                try:
                    # 等待URL变化，表示登录成功
                    await self.page.wait_for_url(
                        lambda url: 'publish' in url and 'login' not in url,
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
            return 'publish' in current_url and 'login' not in current_url
        except:
            return False
    
    async def check_login_status(self) -> bool:
        """检查当前登录状态"""
        try:
            await self.page.goto(self.PUBLISH_URL, wait_until='networkidle', timeout=30000)
            return await self._is_logged_in()
        except:
            return False
    
    async def publish_article(
        self, 
        title: str, 
        content: str, 
        images: List[str],
        publish_now: bool = True
    ) -> PublishResult:
        """发布图文消息（新版简化流程）"""
        tweet_id = f"publish_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            print(f"📤 开始发布文章到小红书: {title}")
            
            # 1. 导航到发布页面
            await self._navigate_to_publish_page()
            
            # 2. 上传图片（直接到上传框）
            if images:
                await self._upload_images_new(images)
            
            # 3. 填写标题
            await self._fill_title(title)
            
            # 4. 填写正文（包含固定标签）
            await self._fill_content_new(content)
            
            # 5. 发布
            if publish_now:
                await self._click_publish()
            
            await self._random_delay(2, 3)
            screenshot_path = await self._take_screenshot("success_xhs")
            
            print(f"✅ 小红书发布成功: {title}")
            
            return PublishResult(
                tweet_id=tweet_id,
                success=True,
                published_at=datetime.now(),
                screenshot_path=screenshot_path
            )
            
        except Exception as e:
            screenshot_path = await self._take_screenshot("error_xhs")
            print(f"❌ 小红书发布失败: {str(e)}")
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
    
    async def _navigate_to_publish_page(self):
        """导航到发布页面"""
        try:
            print("  📍 导航到发布页面...")
            await self.page.goto(self.PUBLISH_URL, wait_until='networkidle', timeout=30000)
            await self._random_delay(1, 2)
            print("  ✅ 发布页面已加载")
        except Exception as e:
            raise PublishException(f"导航到发布页面失败: {e}")
    
    async def _upload_images_new(self, image_paths: List[str]):
        """上传图片（新版流程 - 直接上传到大框）"""
        if not image_paths:
            print("  ℹ️  没有图片需要上传")
            return
            
        try:
            print(f"  📤 准备上传 {len(image_paths)} 张图片...")
            
            # 将所有图片路径转换为绝对路径
            abs_image_paths = [str(Path(img).absolute()) for img in image_paths if Path(img).exists()]
            
            if not abs_image_paths:
                print("  ⚠️  没有有效的图片文件")
                return
            
            # 模拟人类：稍微停顿一下，观察页面
            await self._random_delay(1, 2)
            
            print(f"  📷 上传 {len(abs_image_paths)} 张图片...")
            
            # 直接定位 file input 并上传
            file_input = self.page.locator('input[type="file"]').first
            
            # 模拟人类：点击前稍微犹豫
            await self._random_delay(0.5, 1)
            
            await file_input.set_input_files(abs_image_paths)
            print(f"  ✅ 已选择 {len(abs_image_paths)} 张图片")
            
            # 等待上传处理（稍微长一点，模拟人类观察上传进度）
            print("  ⏱️  等待上传处理...")
            await self._random_delay(3, 5)
            
        except Exception as e:
            print(f"  ⚠️  图片上传失败: {e}")
            import traceback
            traceback.print_exc()
            raise PublishException(f"图片上传失败: {e}")
    
    async def _fill_title(self, title: str):
        """填写标题"""
        try:
            print(f"  ✍️  填写标题: {title}")
            
            # 基于CodeGen: page.get_by_placeholder("填写标题会有更多赞哦～").fill(...)
            title_input = self.page.get_by_placeholder("填写标题会有更多赞哦～")
            await title_input.click()
            await self._random_delay(0.5, 1)
            await title_input.fill(title)
            
            print("  ✅ 标题填写完成")
            
        except Exception as e:
            raise PublishException(f"填写标题失败: {e}")
    
    async def _fill_content_new(self, content: str):
        """填写正文（新版流程，包含固定标签）"""
        try:
            # 在正文末尾添加固定标签
            content_with_tags = f"{content}\n\n{self.fixed_tags}"
            
            print(f"  ✍️  填写正文 ({len(content_with_tags)}字，含标签)...")
            
            # 等待页面稳定
            await self._random_delay(1, 2)
            
            # 基于CodeGen: page.get_by_role("textbox").nth(1).fill(...)
            # nth(1) 是第二个textbox，即正文编辑区
            content_input = self.page.get_by_role("textbox").nth(1)
            await content_input.click()
            await self._random_delay(0.5, 1)
            await content_input.fill(content_with_tags)
            
            print("  ✅ 正文填写完成（含固定标签）")
            
        except Exception as e:
            print(f"  ⚠️  填写正文出现问题: {e}")
            raise PublishException(f"填写正文失败: {e}")
    
    async def _click_publish(self):
        """点击发布按钮"""
        try:
            print("  🚀 点击发布...")
            
            # 基于CodeGen: page.get_by_role("button", name="发布").click()
            publish_btn = self.page.get_by_role("button", name="发布")
            await publish_btn.click()
            await self._random_delay(2, 3)
            
            print("  ✅ 点击发布完成")
            
        except Exception as e:
            raise PublishException(f"点击发布失败: {e}")
    
    # ==================== 旧版流程方法（保留以备后用）====================
    
    async def _select_text_image_mode_old(self):
        """选择文字配图模式（旧版流程）"""
        try:
            print("  📝 选择文字配图模式...")
            text_image_btn = self.page.get_by_role("button", name="文字配图")
            await text_image_btn.click()
            await self._random_delay(1, 2)
            print("  ✅ 已选择文字配图模式")
        except Exception as e:
            raise PublishException(f"选择文字配图模式失败: {e}")
    
    async def _fill_and_generate_old(self, title: str):
        """填写标题并生成图片（旧版流程）"""
        try:
            print(f"  ✍️  填写标题并生成图片: {title}")
            textbox = self.page.get_by_role("textbox")
            await textbox.click()
            await self._random_delay(0.5, 1)
            await textbox.fill(title)
            await self._random_delay(1, 2)
            
            generate_btn = self.page.locator(".edit-text-button")
            await generate_btn.click()
            
            print("  ⏱️  等待图片生成...")
            await self._random_delay(3, 5)
            print("  ✅ 图片生成完成")
        except Exception as e:
            raise PublishException(f"填写标题并生成图片失败: {e}")
    
    async def _click_next_step_old(self):
        """点击下一步（旧版流程）"""
        try:
            print("  ➡️  点击下一步...")
            next_btn = self.page.get_by_role("button", name="下一步")
            await next_btn.click()
            await self._random_delay(2, 3)
            print("  ✅ 已进入编辑页面")
        except Exception as e:
            raise PublishException(f"点击下一步失败: {e}")
    
    async def _upload_images_old(self, image_paths: List[str]):
        """上传图片列表（旧版流程 - 使用expect_file_chooser）"""
        if not image_paths:
            print("  ℹ️  没有图片需要上传")
            return
            
        try:
            print(f"  📤 准备上传 {len(image_paths)} 张图片...")
            
            abs_image_paths = [str(Path(img).absolute()) for img in image_paths if Path(img).exists()]
            
            if not abs_image_paths:
                print("  ⚠️  没有有效的图片文件")
                return
            
            print(f"  📷 上传 {len(abs_image_paths)} 张图片...")
            
            add_btn = self.page.locator("div").filter(has_text=re.compile(r"^添加$")).first
            
            async with self.page.expect_file_chooser() as fc_info:
                await add_btn.click()
                print("    ✓ 已点击添加按钮")
            
            file_chooser = await fc_info.value
            await self._random_delay(0.5, 1)
            await file_chooser.set_files(abs_image_paths)
            
            print(f"  ✅ 已选择 {len(abs_image_paths)} 张图片")
            print("  ⏱️  等待上传处理...")
            await self._random_delay(5, 8)
            
        except Exception as e:
            print(f"  ⚠️  图片上传过程出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def _fill_content_old(self, content: str):
        """填写正文（旧版流程 - 使用contenteditable）"""
        try:
            content_with_tags = f"{content}\n\n{self.fixed_tags}"
            print(f"  ✍️  填写正文 ({len(content_with_tags)}字，含标签)...")
            
            await self._random_delay(2, 3)
            
            try:
                content_editor = self.page.locator('[contenteditable="true"]').first
                await content_editor.click()
                await self._random_delay(0.5, 1)
                
                await self.page.keyboard.press("Control+A")
                await self._random_delay(0.2, 0.3)
                await self.page.keyboard.type(content_with_tags, delay=30)
                
                print("  ✅ 正文填写完成（含固定标签）")
                
            except Exception as e:
                print(f"  ⚠️  正文填写出现问题，但继续流程: {e}")
            
        except Exception as e:
            print(f"  ⚠️  填写正文警告: {e}")
    
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
