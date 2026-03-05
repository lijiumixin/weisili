"""
测试翻译风格
"""
import asyncio
import os
from datetime import datetime
from src.translator import Translator
from src.utils import Tweet

async def test_translation():
    # 从环境变量读取API密钥
    # 注意：这里假设.env文件已经被加载到环境变量中，或者直接在这里读取
    # 为了保险，我们手动加载一下.env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 请设置环境变量 OPENAI_API_KEY")
        return
    
    print("🚀 初始化翻译器...")
    translator = Translator(
        api_key=api_key,
        model="gpt-4o", # 确保使用gpt-4o
        config={}
    )
    
    # 测试推文1：美联储
    tweet1 = Tweet(
        tweet_id="test1",
        username="neilksethi",
        user_display_name="Neil Sethi",
        text="The Fed signaled a more dovish stance as inflation shows signs of cooling. Markets rallied on the news. This is exactly what we've been waiting for - the pivot is finally on the horizon.",
        created_at=datetime.now()
    )
    
    # 测试推文2：市场观点
    tweet2 = Tweet(
        tweet_id="test2",
        username="neilksethi",
        user_display_name="Neil Sethi",
        text="Goldman Sachs just upgraded their S&P 500 target. But looking at the bond market, the yield curve inversion is still screaming recession. Don't get trapped by the FOMO.",
        created_at=datetime.now()
    )
    
    print("\n" + "="*50)
    print("测试案例 1: 美联储转向")
    print("="*50)
    try:
        result = await translator.translate_tweet(tweet1)
        print(f"📄 标题: {result.title}")
        print(f"📝 正文:\n{result.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")

    print("\n" + "="*50)
    print("测试案例 2: 高盛 vs 债市")
    print("="*50)
    try:
        result = await translator.translate_tweet(tweet2)
        print(f"📄 标题: {result.title}")
        print(f"📝 正文:\n{result.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_translation())
