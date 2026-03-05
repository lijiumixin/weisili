"""
配置管理模块
负责加载和验证配置文件，管理环境变量
"""

import yaml
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Optional


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
    
    def reload(self):
        """重新加载配置"""
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> dict:
        """加载YAML配置"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise ConfigException(f"配置文件不存在: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 替换环境变量占位符
        config = self._replace_env_vars(config)
        return config
    
    def _replace_env_vars(self, obj: Any) -> Any:
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
            env_value = os.getenv(var_name, '')
            if not env_value:
                raise ConfigException(f"环境变量未设置: {var_name}")
            return env_value
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
            value = self._get_nested(self.config, key)
            if value is None or value == '':
                raise ConfigException(f'缺少必需配置项: {key}')
    
    def _get_nested(self, d: dict, key: str) -> Any:
        """
        获取嵌套字典的值
        
        Args:
            d: 字典
            key: 点分隔的键路径，如 'twitter.target_username'
        """
        keys = key.split('.')
        current = d
        for k in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(k)
            if current is None:
                return None
        return current
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点分隔的嵌套键，如 'twitter.target_username'）
            default: 默认值
        """
        value = self._get_nested(self.config, key)
        return value if value is not None else default
    
    def get_all(self) -> dict:
        """获取所有配置"""
        return self.config.copy()


class ConfigException(Exception):
    """配置异常"""
    pass


# 测试代码
if __name__ == "__main__":
    try:
        config = ConfigManager()
        print("✅ 配置加载成功")
        print(f"Twitter目标用户: {config.get('twitter.target_username')}")
        print(f"运行模式 (headless): {config.get('runtime.headless')}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
