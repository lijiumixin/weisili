# Twitter to WeChat & Xiaohongshu Auto Publishing System

> 自动爬取Twitter内容，翻译后发布到微信公众号和小红书

## 📖 项目简介

本系统可以自动完成以下工作流程：

1. **爬取Twitter** - 定时爬取指定账号的最新推文和图片
2. **翻译内容** - 使用OpenAI API将英文翻译成专业的中文
3. **多平台发布** - 自动发布到微信公众号和小红书，包括图片和文字

**特点**：
- ✅ 模拟真人操作，避免被平台检测
- ✅ 支持多平台发布（微信公众号 + 小红书）
- ✅ 支持图片自动下载和上传
- ✅ 智能去重，不会重复发布
- ✅ 异常自动通知
- ✅ 详细日志记录

---

## 🚀 快速开始

### 1. 环境要求

- **Python 3.9+**
- **Windows 10/11**（用于桌面通知）

### 2. 安装依赖

```bash
# 克隆或下载项目后，进入项目目录
cd weisili

# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 3. 配置

#### 3.1 创建 `.env` 文件

复制 `.env.example` 为 `.env`，填入你的 OpenAI API密钥：

```env
OPENAI_API_KEY=sk-your-api-key-here
```

#### 3.2 修改配置文件（可选）

编辑 `config/config.yaml`，根据需要调整：

- `twitter.target_username` - 目标Twitter用户名
- `twitter.scrape_interval_min` / `max` - 爬取间隔
- `openai.model` - 使用的模型（gpt-4 或 gpt-3.5-turbo）
- `wechat.publish_interval_min` / `max` - 发布间隔
- `runtime.headless` - 是否无头模式运行
- `translation.style` - 翻译风格

### 4. 首次运行

#### 步骤1：登录微信公众号

```bash
python main.py --login
```

- 浏览器会自动打开微信公众号登录页
- 使用手机微信扫码登录
- 登录成功后，程序会自动保存登录态

#### 步骤2：登录小红书创作者平台

```bash
python main.py --login-xiaohongshu
```

- 浏览器会自动打开小红书创作者平台登录页
- 完成登录（扫码或账号密码）
- 登录成功后，程序会自动保存登录态

#### 步骤3：测试运行

```bash
python main.py --mode test
```

- 系统会执行一次完整流程：
  - 爬取Twitter
  - 翻译内容
  - 发布到微信公众号
  - 发布到小红书（如启用）
- 检查是否正常工作

#### 步骤4：正式运行

确认无误后，启动定时任务：

```bash
python main.py --mode production
```

- 系统将按配置的间隔自动运行
- 可以将 `runtime.headless` 改为 `true` 以后台运行
- 按 `Ctrl+C` 停止程序

---

## 📂 项目结构

```
weisili/
├── config/                    # 配置文件
│   ├── config.yaml           # 主配置
│   ├── translation_prompt.txt # 翻译提示词
│   ├── published_tweets.json # 已发布记录
│   └── wechat_state.json     # 微信登录态（自动生成）
├── data/                     # 数据文件
│   └── images/               # 下载的Twitter图片
├── logs/                     # 日志文件（自动生成）
├── screenshots/              # 截图（调试用，自动生成）
├── src/                      # 源代码
│   ├── config_manager.py     # 配置管理
│   ├── twitter_scraper.py    # Twitter爬虫
│   ├── translator.py         # 翻译模块
│   ├── wechat_publisher.py   # 微信发布
│   ├── xiaohongshu_publisher.py # 小红书发布
│   ├── scheduler.py          # 任务调度
│   ├── notifier.py           # 通知与日志
│   └── utils.py              # 工具函数
├── spec/                     # 开发规范
│   └── PROJECT_SPEC.md       # 详细规范文档
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖清单
├── .env                      # 环境变量（需创建）
└── README.md                 # 本文档
```

---

## 🛠️ 使用说明

### 命令行参数

```bash
# 首次登录微信
python main.py --login

# 首次登录小红书
python main.py --login-xiaohongshu

# 测试模式（执行一次，可见浏览器）
python main.py --mode test

# 生产模式（定时运行）
python main.py --mode production
```

### 查看日志

日志文件位于 `logs/app.log`，按天分割，保留30天。

```bash
# Windows查看实时日志
Get-Content logs/app.log -Wait
```

### 调整翻译风格

编辑 `config/translation_prompt.txt`，自定义翻译提示词。

### 查看已发布记录

`config/published_tweets.json` 记录了所有已发布的推文ID，避免重复。

---

## ⚙️ 配置说明

### `config/config.yaml` 主要参数

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `twitter.target_username` | 目标Twitter用户名 | neilksethi |
| `twitter.scrape_interval_min` | 爬取最小间隔（分钟） | 15 |
| `twitter.scrape_interval_max` | 爬取最大间隔（分钟） | 30 |
| `openai.model` | OpenAI模型 | gpt-4 |
| `wechat.publish_interval_min` | 发布最小间隔（分钟） | 3 |
| `wechat.publish_interval_max` | 发布最大间隔（分钟） | 10 |
| `xiaohongshu.enabled` | 是否启用小红书发布 | true |
| `xiaohongshu.fixed_tags` | 固定话题标签 | #股票#宏观#投资#炒股#投资观察 |
| `runtime.headless` | 无头模式（后台运行） | false |
| `runtime.screenshot_on_error` | 错误时截图 | true |
| `notification.desktop_enabled` | 桌面通知 | true |
| `logging.level` | 日志级别 | INFO |

---

## 🔔 通知机制

### 桌面通知

系统会在以下情况发送Windows桌面通知：

- ❌ 发布失败
- ⚠️  登录过期
- 🚨 严重错误

### 日志级别

- **INFO** - 正常流程信息
- **WARNING** - 警告信息
- **ERROR** - 错误信息（单条推文失败）
- **CRITICAL** - 严重错误（系统级问题）

---

## 🐛 常见问题

### 1. `playwright install` 失败

```bash
# 尝试手动安装chromium
playwright install --force chromium
```

### 2. OpenAI API报错

- 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
- 确认API密钥有余额
- 如果使用国内代理，可能需要配置代理

### 3. 微信登录过期

- 运行 `python main.py --login` 重新登录
- 系统会自动检测并通知

### 4. 爬取不到推文

- 检查Twitter账号是否公开
- 确认网络连接正常
- 查看 `logs/app.log` 了解详细错误

### 5. 发布失败

- 检查微信公众号权限
- 确认图片大小和格式符合要求
- 查看 `screenshots/` 目录下的错误截图

---

## 📝 开发文档

### 技术方案

详见 [`TECH_SOLUTION.md`](TECH_SOLUTION.md)

### 开发规范

详见 [`spec/PROJECT_SPEC.md`](spec/PROJECT_SPEC.md)

### 模块说明

- **twitter_scraper.py** - 使用Playwright爬取Twitter，包含反反爬措施
- **translator.py** - 调用OpenAI API翻译，支持自定义提示词
- **wechat_publisher.py** - 模拟真人操作发布到微信公众号
- **xiaohongshu_publisher.py** - 模拟真人操作发布到小红书（文字配图模式）
- **scheduler.py** - 协调各模块，管理定时任务
- **notifier.py** - 统一的日志和通知管理

---

## 🔐 安全建议

1. **不要提交 `.env` 文件到Git**（已在 `.gitignore` 中）
2. **定期更换API密钥**
3. **不要公开分享 `config/wechat_state.json`**（包含登录信息）
4. **本地运行时注意网络安全**

---

## 📄 许可证

本项目仅供学习交流使用，请遵守相关平台的服务条款。

---

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 浏览器自动化
- [OpenAI](https://openai.com/) - GPT翻译服务

---

## 📞 技术支持

如有问题，请查看：

1. **日志文件** - `logs/app.log`
2. **开发规范** - `spec/PROJECT_SPEC.md`
3. **截图记录** - `screenshots/`

---

**最后更新**: 2025-11-25  
**版本**: v1.0
