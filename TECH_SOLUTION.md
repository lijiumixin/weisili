# Twitter to WeChat Auto Publishing System - 技术方案

## 📌 项目概述

**项目名称**：Twitter → WeChat 自动发布系统  
**目标**：自动爬取指定 Twitter 账号最新内容，翻译后自动发布到微信公众号  
**目标账号**：https://x.com/neilksethi  
**适用对象**：编程小白，注重易用性和稳定性

---

## 🎯 核心需求

### 1. Twitter 内容爬取
- **目标账号**：https://x.com/neilksethi
- **爬取频率**：每 15-30 分钟随机间隔
- **爬取内容**：
  - 推文文本
  - 所有图片（完整下载到本地）
- **去重机制**：使用 Tweet ID 记录已爬取内容
- **技术要求**：
  - 使用 Playwright 模拟真人行为
  - 无需登录（公开账号）
  - 实现反反爬措施

### 2. 内容翻译
- **翻译方向**：英文 → 中文
- **内容风格**：宏观经济专业表述，适合国内金融从业者
- **输出要求**：
  - 标题：20字以内，简短吸引人
  - 正文：专业、流畅的中文翻译
- **翻译引擎**：OpenAI API（GPT-4 或 GPT-3.5-turbo）
- **可配置项**：翻译提示词（Prompt）放在配置文件

### 3. 微信公众号发布
- **发布方式**：直接发布（不存草稿）
- **发布策略**：
  - 每条推文独立发布为一篇图文
  - 多条推文间隔发布（模拟真人，间隔 3-10 分钟随机）
- **内容构成**：
  - 标题：翻译生成的标题
  - 正文：翻译后的文本
  - 图片：全部上传（保持原顺序）
- **技术实现**：
  - Playwright 模拟真人操作
  - 首次手动登录，保存登录态
  - 后续自动使用保存的 Cookies

### 4. 系统运行
- **运行环境**：Windows 本地
- **运行模式**：
  - 测试模式：有头浏览器（可见操作过程）
  - 生产模式：无头浏览器（后台运行）
- **定时任务**：Python `schedule` 库
- **通知机制**：
  - 日志文件（详细记录）
  - Windows 桌面通知（关键错误）
  - 可选邮件通知

---

## 🏗️ 技术架构

### 技术栈选型

| 模块 | 技术选型 | 理由 |
|------|---------|------|
| 编程语言 | Python 3.9+ | 生态丰富，对小白友好 |
| 浏览器自动化 | Playwright | 强大的反反爬能力，支持真人模拟 |
| 翻译服务 | OpenAI API | 翻译质量高，支持自定义 Prompt |
| 数据存储 | JSON 文件 | 轻量级，无需数据库 |
| 定时任务 | schedule | 简单易用，适合本地运行 |
| 日志系统 | Python logging | 标准库，成熟稳定 |
| 通知系统 | win10toast | Windows 原生通知 |

### 项目结构

```
weisili/
├── .env                        # 环境变量（API密钥等敏感信息）
├── config/
│   ├── config.yaml            # 主配置文件
│   ├── published_tweets.json  # 已发布推文记录
│   └── translation_prompt.txt # 翻译提示词模板
├── data/
│   └── images/                # 下载的Twitter图片（按日期/tweet_id组织）
├── logs/                      # 日志文件（按日期分割）
│   └── app_YYYYMMDD.log
├── screenshots/               # 调试截图
├── src/
│   ├── __init__.py
│   ├── config_manager.py      # 配置管理
│   ├── twitter_scraper.py     # Twitter爬虫
│   ├── translator.py          # 翻译模块
│   ├── wechat_publisher.py    # 微信发布模块
│   ├── scheduler.py           # 定时任务调度
│   ├── notifier.py            # 通知模块
│   └── utils.py               # 工具函数
├── spec/
│   └── PROJECT_SPEC.md        # 详细开发规范
├── tests/                     # 单元测试（可选）
│   ├── test_scraper.py
│   ├── test_translator.py
│   └── test_publisher.py
├── main.py                    # 主程序入口
├── requirements.txt           # Python依赖
├── README.md                  # 使用说明
└── TECH_SOLUTION.md           # 本文档
```

---

## 🔧 核心模块设计

### 1. Twitter Scraper（twitter_scraper.py）

**功能**：爬取 Twitter 账号的最新推文

**关键方法**：
```python
class TwitterScraper:
    def __init__(self, headless=False):
        """初始化爬虫"""
        
    async def scrape_tweets(self, username: str, since_id: str = None) -> List[Tweet]:
        """爬取指定用户的新推文
        Args:
            username: Twitter用户名
            since_id: 上次爬取的最后一条tweet ID
        Returns:
            新推文列表
        """
        
    async def download_images(self, tweet: Tweet) -> List[str]:
        """下载推文中的图片
        Returns:
            本地图片路径列表
        """
```

**反反爬措施**：
- 随机 User-Agent
- 随机滚动速度和停顿时间
- 模拟鼠标移动轨迹
- 请求间随机延迟（2-5秒）
- 使用 Playwright 的 stealth 模式

### 2. Translator（translator.py）

**功能**：调用 OpenAI API 翻译推文

**关键方法**：
```python
class Translator:
    def __init__(self, api_key: str):
        """初始化翻译器"""
        
    async def translate_tweet(self, text: str) -> dict:
        """翻译推文
        Args:
            text: 原始英文推文
        Returns:
            {
                "title": "生成的中文标题（≤20字）",
                "content": "翻译后的正文"
            }
        """
```

**翻译提示词模板**（可配置）：
```
你是一位专业的宏观经济分析师和翻译专家。请将以下英文推文翻译成中文：

要求：
1. 风格：专业、严谨，适合国内金融从业者阅读
2. 术语：使用中国金融市场常用表述
3. 语气：客观中立，保持原文的观点和语气
4. 标题：提炼一个20字以内的吸引人标题
5. 正文：完整翻译，确保信息准确传达

原文：
{tweet_text}

请以JSON格式回复：
{
  "title": "标题",
  "content": "正文"
}
```

### 3. WeChat Publisher（wechat_publisher.py）

**功能**：自动发布内容到微信公众号

**关键方法**：
```python
class WeChatPublisher:
    def __init__(self, headless=False):
        """初始化发布器"""
        
    async def login(self, save_state=True):
        """登录微信公众号
        首次需手动扫码，保存登录态
        """
        
    async def check_login_status(self) -> bool:
        """检查登录状态是否有效"""
        
    async def publish_article(self, title: str, content: str, images: List[str]):
        """发布图文
        Args:
            title: 文章标题
            content: 文章正文
            images: 本地图片路径列表
        """
```

**发布流程**（基于截图）：
1. 访问微信公众号后台
2. 点击左侧菜单"图文消息"（模拟真人点击）
3. 在新页面中：
   - 填写标题
   - Hover "选择或拖拽图片到此处"
   - 点击下拉菜单的"本地上传"
   - 使用 Playwright 的文件选择器上传图片
   - 填写正文内容
4. 点击"发布"按钮

**真人模拟措施**：
- 每个操作间随机延迟（1-3秒）
- 模拟鼠标移动到目标位置
- 随机微调点击位置
- 模拟打字速度（逐字输入，随机延迟）

### 4. Scheduler（scheduler.py）

**功能**：定时任务调度

**关键方法**：
```python
class TaskScheduler:
    def __init__(self, config: dict):
        """初始化调度器"""
        
    def schedule_scraping(self):
        """安排爬取任务
        每15-30分钟随机间隔
        """
        
    async def run_pipeline(self):
        """执行完整流程
        1. 爬取新推文
        2. 翻译内容
        3. 间隔发布到微信
        """
        
    def start(self):
        """启动定时任务"""
```

### 5. Notifier（notifier.py）

**功能**：错误通知和日志记录

**通知级别**：
- **INFO**：正常运行信息（仅日志）
- **WARNING**：警告信息（日志 + 控制台）
- **ERROR**：错误信息（日志 + 桌面通知）
- **CRITICAL**：严重错误（日志 + 桌面通知 + 可选邮件）

**关键方法**：
```python
class Notifier:
    def log(self, level: str, message: str):
        """记录日志"""
        
    def notify_desktop(self, title: str, message: str):
        """Windows桌面通知"""
        
    def notify_email(self, subject: str, body: str):
        """邮件通知（可选）"""
```

---

## ⚙️ 配置文件设计

### config.yaml
```yaml
# Twitter 配置
twitter:
  target_username: "neilksethi"
  scrape_interval_min: 15  # 最小间隔（分钟）
  scrape_interval_max: 30  # 最大间隔（分钟）

# OpenAI 配置
openai:
  api_key: "${OPENAI_API_KEY}"  # 从环境变量读取
  model: "gpt-4"  # 或 "gpt-3.5-turbo"
  temperature: 0.7
  max_tokens: 2000

# 翻译配置
translation:
  prompt_template_file: "config/translation_prompt.txt"
  style: "专业、严谨，适合国内金融从业者"

# 微信公众号配置
wechat:
  login_url: "https://mp.weixin.qq.com/"
  state_file: "config/wechat_state.json"  # 保存的登录态
  publish_interval_min: 3  # 发布间隔最小（分钟）
  publish_interval_max: 10  # 发布间隔最大（分钟）

# 运行模式
runtime:
  headless: false  # 测试时false，正式运行改为true
  screenshot_on_error: true  # 出错时截图
  max_retries: 3  # 失败重试次数

# 通知配置
notification:
  desktop_enabled: true
  email_enabled: false  # 可选
  email_to: ""
  smtp_server: ""
  smtp_port: 587
  smtp_username: ""
  smtp_password: "${EMAIL_PASSWORD}"

# 日志配置
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file_rotation: "daily"  # 按天分割日志
  max_log_size_mb: 10
```

### .env
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
EMAIL_PASSWORD=yourpassword  # 可选
```

---

## 🔄 工作流程

### 主流程图

```
┌─────────────────────┐
│  定时任务触发       │
│ (15-30分钟随机)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 1. 爬取Twitter      │
│  - 访问账号主页     │
│  - 获取新推文       │
│  - 下载图片         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. 检查新内容       │
│  - 对比tweet ID     │
│  - 过滤已发布       │
└──────────┬──────────┘
           │
           ▼
      ┌────┴────┐
      │ 有新推文？│
      └────┬────┘
           │ 是
           ▼
┌─────────────────────┐
│ 3. 翻译内容         │
│  - 调用OpenAI API   │
│  - 生成标题+正文    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. 发布到微信       │
│  - 检查登录状态     │
│  - 上传图片         │
│  - 填写标题正文     │
│  - 点击发布         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. 记录发布状态     │
│  - 保存tweet ID     │
│  - 记录日志         │
└──────────┬──────────┘
           │
           ▼
      ┌────┴────┐
      │还有待发布？│
      └────┬────┘
           │ 是
           ▼
      等待3-10分钟
           │
           └──（循环到步骤4）
```

### 错误处理流程

```
每个步骤出错时：
1. 记录错误日志
2. 截图保存（如果是浏览器操作）
3. 根据错误类型决定：
   - 重试（网络问题、临时错误）
   - 跳过（内容问题）
   - 停止并通知（严重错误，如登录失效）
```

---

## 🛡️ 安全与稳定性

### 反反爬策略
1. **请求频率控制**：随机间隔，避免规律性
2. **浏览器指纹**：使用真实浏览器环境
3. **人类行为模拟**：
   - 随机鼠标移动
   - 自然滚动速度
   - 页面停留时间
4. **错误恢复**：失败后指数退避重试

### 微信账号安全
1. **真人操作模拟**：
   - 打字速度随机化
   - 点击位置微调
   - 操作间合理延迟
2. **登录态保护**：
   - 加密存储 Cookies
   - 定期验证有效性
   - 异常时及时通知

### 数据安全
1. 敏感信息使用环境变量
2. 配置文件不包含密钥
3. `.gitignore` 排除敏感文件

---

## 📦 依赖包清单

```txt
# requirements.txt
playwright==1.40.0
openai==1.3.0
pyyaml==6.0.1
python-dotenv==1.0.0
schedule==1.2.0
win10toast==0.9  # Windows通知
Pillow==10.1.0  # 图片处理
aiohttp==3.9.0  # 异步HTTP
python-dateutil==2.8.2
colorlog==6.8.0  # 彩色日志
```

---

## 🚀 部署与运行

### 初次部署步骤

1. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **配置环境变量**
   - 复制 `.env.example` 为 `.env`
   - 填入 OpenAI API Key

3. **首次运行（测试模式）**
   ```bash
   python main.py --mode test
   ```
   - 会打开浏览器窗口
   - 提示你登录微信公众号
   - 爬取一次Twitter并发布

4. **确认无误后，启动生产模式**
   ```bash
   python main.py --mode production
   ```
   - 无头模式运行
   - 后台定时执行

### 日常维护

- **查看日志**：`logs/app_YYYYMMDD.log`
- **查看已发布记录**：`config/published_tweets.json`
- **调整配置**：编辑 `config/config.yaml`

---

## 🧪 测试计划

### 单元测试
- `test_scraper.py`：测试爬虫功能
- `test_translator.py`：测试翻译功能
- `test_publisher.py`：测试发布功能

### 集成测试
1. 手动爬取一条推文
2. 翻译并检查质量
3. 发布到微信（使用测试账号）

---

## 📝 开发规范（Spec模式）

详见：`spec/PROJECT_SPEC.md`

包含：
- 详细的模块接口定义
- 数据结构规范
- 错误处理规范
- 代码风格指南
- 测试用例

---

## 🎯 后续优化方向

1. **Web管理界面**：可视化监控爬取和发布状态
2. **多账号支持**：同时监控多个Twitter账号
3. **内容审核**：发布前人工审核
4. **数据分析**：统计发布效果（阅读量等）
5. **云端部署**：迁移到云服务器24小时运行

---

## 📞 技术支持

本项目采用 Spec 驱动开发模式，所有模块都有详细的规范文档。
如有问题，请查看：
1. `README.md` - 使用说明
2. `spec/PROJECT_SPEC.md` - 开发规范
3. `logs/` - 运行日志

---

**文档版本**：v1.0  
**最后更新**：2025-11-25  
**作者**：Antigravity AI Assistant
