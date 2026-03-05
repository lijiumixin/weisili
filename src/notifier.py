"""
通知与日志管理模块
负责日志记录和Windows桌面通知
"""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False
    print("⚠️  win10toast未安装，桌面通知功能将不可用")

try:
    from colorlog import ColoredFormatter
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


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
        self.toaster = ToastNotifier() if TOAST_AVAILABLE else None
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
        
        # 清除已有的handlers（避免重复）
        self.logger.handlers.clear()
        
        # 创建logs目录
        Path('logs').mkdir(exist_ok=True)
        
        # 文件handler（按天分割）
        log_filename = f'logs/app.log'
        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
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
        if COLORLOG_AVAILABLE:
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
        else:
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
        level = level.upper()
        log_func = getattr(self.logger, level.lower(), self.logger.info)
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
        
        if not TOAST_AVAILABLE or not self.toaster:
            self.log('WARNING', f'桌面通知不可用: {title} - {message}')
            return
        
        try:
            self.toaster.show_toast(
                title=title,
                msg=message,
                duration=duration,
                icon_path=None,
                threaded=True
            )
        except Exception as e:
            self.log('ERROR', f'桌面通知发送失败: {str(e)}')


# 测试代码
if __name__ == "__main__":
    notifier = Notifier(
        notification_config={'desktop_enabled': True},
        logging_config={'level': 'INFO'}
    )
    
    notifier.log('INFO', '测试信息日志')
    notifier.log('WARNING', '测试警告日志')
    notifier.log('ERROR', '测试错误日志')
    notifier.notify_desktop('测试通知', '这是一条测试通知')
