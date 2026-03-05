"""
内容翻译模块
使用OpenAI API将推文翻译成中文
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from openai import OpenAI

from .utils import Tweet, TranslatedContent, TranslationException


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
        template_file = self.config.get('prompt_template_file', 'config/translation_prompt.txt')
        template_path = Path(template_file)
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # 默认模板
            return """你是一位拥有20年经验的资深宏观交易大师，深谙全球市场脉搏。请将以下英文推文翻译并改写成中文。

【人设要求】
1. 身份：资深交易员，老练、犀利。
2. 语气：口语化，像是在和朋友聊天。
3. 风格：拒绝翻译腔，要用"人话"解释市场。

【翻译要求】
1. 标题（重中之重！）：
   * 必须是"震惊体"或"悬念体"，参考小红书/公众号爆款。
   * 必须包含至少1个Emoji。
   * 必须在20字以内！
   * ❌ 拒绝：美联储暗示鸽派立场
   * ✅ 必须是：🚨美联储终于认怂！市场狂欢💸
   * ✅ 必须是：📉衰退警报拉响！别接飞刀🚫
2. 正文：
   * 核心翻译：准确传达原意，但用词要接地气。
   * 大师解读：如果原文涉及复杂概念，请用简单易懂的语言补充解释。
   * 排版：适当分段。

【原文】
{tweet_text}

【输出格式】
请严格按照JSON格式回复：
{{
  "title": "标题",
  "content": "正文"
}}
"""
    
    async def translate_tweet(self, tweet: Tweet) -> TranslatedContent:
        """
        翻译推文
        
        Args:
            tweet: 待翻译的推文对象
            
        Returns:
            翻译后的内容对象
            
        Raises:
            TranslationException: 翻译失败时抛出
        """
        try:
            print(f"🌐 开始翻译推文 {tweet.tweet_id}...")
            
            # 构建基础文本prompt
            text_prompt = self._build_prompt(tweet.text)
            
            # 尝试1: 多模态翻译（如果有图片）
            if tweet.image_urls:
                try:
                    print(f"  🖼️  包含 {len(tweet.image_urls)} 张图片，尝试多模态翻译...")
                    result = await self._translate_with_images(text_prompt, tweet.image_urls)
                    title = result['title']
                    if len(title) > 20:
                        print(f"  ⚠️  标题过长({len(title)}字)，自动截取到20字")
                        title = title[:20]
                    
                    translated = TranslatedContent(
                        tweet_id=tweet.tweet_id,
                        title=title,
                        content=result['content'],
                        translated_at=datetime.now(),
                        word_count=len(result['content']),
                        model_used=self.model + " (multimodal)"
                    )
                    
                    if not translated.content or len(translated.content) < 10:
                        raise TranslationException("翻译内容过短")
                    
                    print(f"✅ 多模态翻译完成: {translated.title}")
                    return translated
                    
                except Exception as e:
                    print(f"  ⚠️  多模态翻译失败: {str(e)}")
                    print(f"  🔄 降级为纯文本翻译...")
            
            # 尝试2: 纯文本翻译（降级或无图片）
            try:
                result = await self._translate_text_only(text_prompt)
                title = result['title']
                if len(title) > 20:
                    print(f"  ⚠️  标题过长({len(title)}字)，自动截取到20字")
                    title = title[:20]
                
                translated = TranslatedContent(
                    tweet_id=tweet.tweet_id,
                    title=title,
                    content=result['content'],
                    translated_at=datetime.now(),
                    word_count=len(result['content']),
                    model_used=self.model + " (text-only)"
                )
                
                if not translated.content or len(translated.content) < 10:
                    raise TranslationException("翻译内容过短")
                
                print(f"✅ 翻译完成: {translated.title}")
                return translated
                
            except Exception as e:
                print(f"  ❌ 纯文本翻译也失败: {str(e)}")
                raise TranslationException(f"翻译失败（多模态和纯文本均失败）: {str(e)}")
            
        except Exception as e:
            raise TranslationException(f"翻译失败: {str(e)}")
    
    async def _translate_with_images(self, text_prompt: str, image_urls: List[str]) -> Dict[str, str]:
        """多模态翻译（文本+图片）"""
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的宏观经济分析师和翻译专家。请严格按照JSON格式返回翻译结果。"
            }
        ]
        
        user_content = []
        user_content.append({"type": "text", "text": text_prompt})
        
        for url in image_urls:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": "low"
                }
            })
        
        messages.append({"role": "user", "content": user_content})
        return await self._call_openai_api_multimodal(messages)
    
    async def _translate_text_only(self, text_prompt: str) -> Dict[str, str]:
        """纯文本翻译（无图片）"""
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的宏观经济分析师和翻译专家。请严格按照JSON格式返回翻译结果。"
            },
            {
                "role": "user",
                "content": text_prompt
            }
        ]
        return await self._call_openai_api_multimodal(messages)

    
    def _build_prompt(self, tweet_text: str) -> str:
        """
        构建翻译提示词
        
        替换模板中的占位符
        """
        style = self.config.get('style', '专业、严谨')
        
        # 如果使用默认模板，我们在这里注入更严格的要求
        if not self.config.get('prompt_template_file') or not Path(self.config['prompt_template_file']).exists():
             return f"""你是一位拥有20年经验的资深宏观交易大师，深谙全球市场脉搏。请将以下英文推文翻译并改写成中文。

【人设要求】
1. 身份：资深交易员，老练、犀利。
2. 语气：口语化，像是在和朋友聊天。
3. 风格：拒绝翻译腔，要用"人话"解释市场。
4. 用语：**严格使用中国大陆的金融术语和语言习惯**。
   * ❌ 拒绝台湾/港澳用语（如：联准会、软体、硬体、网路、简讯、讯息、质押、做多/做空(若语境不符)、当冲等若有大陆惯用语请替换）。
   * ✅ 必须是：美联储、软件、硬件、网络、短信、信息、质押(Pledge)、做多/做空(Long/Short)、日内交易等。
   * 确保逻辑符合大陆读者的阅读习惯。

【翻译要求】
1. 标题（绝对红线！）：
   * 必须是"震惊体"或"悬念体"。
   * 必须包含至少1个Emoji。
   * ⚠️ 严禁超过20个字！如果超过，请直接重写，不要截断。
   * ❌ 拒绝：美联储暗示鸽派立场
   * ✅ 必须是：🚨美联储终于认怂！市场狂欢💸
2. 正文：
   * 核心翻译：准确传达原意，但用词要接地气。
   * 结合图片（如果有）：请结合提供的图片理解语境，确保翻译准确。但**不要**在正文中描述图片长什么样（例如"如图所示"、"这张图表显示"），而是直接把图片里的信息融入到分析中。
   * 排版：适当分段。

【原文】
{tweet_text}

【输出格式】
请严格按照JSON格式回复：
{{
  "title": "标题",
  "content": "正文"
}}
"""
        
        prompt = self.prompt_template.replace('{tweet_text}', tweet_text)
        prompt = prompt.replace('{style}', style)
        return prompt
    
    async def _call_openai_api_multimodal(self, messages: List[Dict], max_retries: int = 2) -> Dict[str, str]:
        """
        调用OpenAI API (支持多模态消息结构)
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # 提取内容
                content = response.choices[0].message.content.strip()
                
                # 尝试解析JSON
                content = content.replace('```json', '').replace('```', '').strip()
                
                result = json.loads(content)
                
                if 'title' not in result or 'content' not in result:
                    raise ValueError("响应缺少必需字段")
                
                return result
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    print(f"⚠️  JSON解析失败，重试 ({attempt + 1}/{max_retries})...")
                    continue
                else:
                    raise TranslationException(f"API响应格式错误: {e}\n内容: {content}")
            
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️  API调用失败，重试 ({attempt + 1}/{max_retries})...")
                    continue
                else:
                    raise TranslationException(f"API调用失败: {e}")
        
        raise TranslationException("翻译失败达最大重试次数")

    # 保留旧方法以兼容（虽然内部不再使用）
    async def _call_openai_api(self, prompt: str, max_retries: int = 2) -> Dict[str, str]:
        return await self._call_openai_api_multimodal([
            {"role": "system", "content": "你是一位专业的宏观经济分析师。请严格按照JSON格式返回翻译结果。"},
            {"role": "user", "content": prompt}
        ], max_retries)


# 测试代码
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # 从环境变量读取API密钥
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ 请设置环境变量 OPENAI_API_KEY")
            return
        
        translator = Translator(
            api_key=api_key,
            model="gpt-4",
            config={'style': '专业、严谨，适合国内金融从业者阅读'}
        )
        
        # 测试推文
        test_tweet = Tweet(
            tweet_id="test123",
            username="testuser",
            user_display_name="Test User",
            text="The Fed signaled a more dovish stance as inflation shows signs of cooling. Markets rallied on the news.",
            created_at=datetime.now()
        )
        
        try:
            result = await translator.translate_tweet(test_tweet)
            print(f"\n标题: {result.title}")
            print(f"正文: {result.content}")
            print(f"字数: {result.word_count}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    asyncio.run(test())
