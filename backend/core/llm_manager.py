"""
LLM管理器 - 统一管理多个模型提供商
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from .llm_providers import (
    LLMProvider, LLMProviderFactory, ProviderType, 
    ModelInfo, LLMResponse
)
from ..utils.llm_debug import (
    is_llm_debug_enabled,
    mask_secret,
    summarize_text,
    write_llm_debug_event,
    write_llm_debug_blob,
)

logger = logging.getLogger(__name__)

class LLMManager:
    """LLM管理器"""
    
    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = settings_file or self._get_default_settings_file()
        self.current_provider: Optional[LLMProvider] = None
        self._settings_mtime: Optional[float] = self._get_settings_mtime()
        self.settings = self._load_settings()
        self._initialize_provider()
    
    def _get_default_settings_file(self) -> Path:
        """获取默认设置文件路径"""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # backend/core -> backend -> project_root
        return project_root / "data" / "settings.json"
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        default_settings = {
            "llm_provider": "dashscope",
            "dashscope_api_key": "",
            "dashscope_http_base_url": "",
            "dashscope_workspace": "",
            "openai_api_key": "",
            "gemini_api_key": "",
            "siliconflow_api_key": "",
            "model_name": "qwen-plus",
            "chunk_size": 5000,
            "min_score_threshold": 0.7,
            "max_clips_per_collection": 5,
            "llm_debug": False
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
            except Exception as e:
                logger.warning(f"加载设置文件失败: {e}")
        
        return default_settings

    def _get_settings_mtime(self) -> Optional[float]:
        """获取设置文件修改时间（文件不存在时返回None）"""
        try:
            if self.settings_file.exists():
                return self.settings_file.stat().st_mtime
        except Exception as e:
            logger.warning(f"读取设置文件修改时间失败: {e}")
        return None

    def _refresh_settings_if_changed(self):
        """
        当设置文件在其他进程被修改时（如Web进程更新，Celery长进程仍在运行），
        自动重新加载配置并重建provider，避免使用过期API密钥/模型。
        """
        current_mtime = self._get_settings_mtime()
        if current_mtime == self._settings_mtime:
            return

        logger.info("检测到LLM设置文件变化，正在重新加载配置")
        self.settings = self._load_settings()
        self._settings_mtime = current_mtime
        self._initialize_provider()
    
    def _save_settings(self):
        """保存设置"""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            self._settings_mtime = self._get_settings_mtime()
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            raise
    
    def _initialize_provider(self):
        """初始化当前提供商"""
        try:
            provider_type = ProviderType(self.settings.get("llm_provider", "dashscope"))
            model_name = self.settings.get("model_name", "qwen-plus")
            
            # 获取对应提供商的API密钥
            api_key = self._get_api_key_for_provider(provider_type)
            
            if api_key:
                provider_kwargs = self._get_provider_kwargs(provider_type)
                self.current_provider = LLMProviderFactory.create_provider(
                    provider_type, api_key, model_name, **provider_kwargs
                )
                logger.info(f"已初始化{provider_type.value}提供商，模型: {model_name}")
                write_llm_debug_event(
                    "provider_initialized",
                    {
                        "provider": provider_type.value,
                        "model": model_name,
                        "api_key_masked": mask_secret(api_key),
                        "llm_debug": is_llm_debug_enabled(),
                    },
                )
            else:
                logger.warning(f"未找到{provider_type.value}的API密钥")
                
        except Exception as e:
            logger.error(f"初始化提供商失败: {e}")
            self.current_provider = None
    
    def _get_api_key_for_provider(self, provider_type: ProviderType) -> Optional[str]:
        """获取指定提供商的API密钥"""
        key_mapping = {
            ProviderType.DASHSCOPE: "dashscope_api_key",
            ProviderType.OPENAI: "openai_api_key",
            ProviderType.GEMINI: "gemini_api_key",
            ProviderType.SILICONFLOW: "siliconflow_api_key",
        }
        
        key_name = key_mapping.get(provider_type)
        if key_name:
            return self.settings.get(key_name, "")
        return None
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """更新设置"""
        self.settings.update(new_settings)
        self._save_settings()
        self._initialize_provider()
    
    def set_provider(self, provider_type: ProviderType, api_key: str, model_name: str):
        """设置提供商"""
        try:
            # 更新设置
            provider_settings = {
                "llm_provider": provider_type.value,
                "model_name": model_name
            }
            
            # 更新对应提供商的API密钥
            key_mapping = {
                ProviderType.DASHSCOPE: "dashscope_api_key",
                ProviderType.OPENAI: "openai_api_key",
                ProviderType.GEMINI: "gemini_api_key",
                ProviderType.SILICONFLOW: "siliconflow_api_key",
            }
            
            key_name = key_mapping.get(provider_type)
            if key_name:
                provider_settings[key_name] = api_key
            
            self.update_settings(provider_settings)
            
            # 创建新的提供商实例
            provider_kwargs = self._get_provider_kwargs(provider_type)
            self.current_provider = LLMProviderFactory.create_provider(
                provider_type, api_key, model_name, **provider_kwargs
            )
            
            logger.info(f"已切换到{provider_type.value}提供商，模型: {model_name}")
            
        except Exception as e:
            logger.error(f"设置提供商失败: {e}")
            raise
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> str:
        """调用LLM"""
        self._refresh_settings_if_changed()
        if not self.current_provider:
            raise ValueError("未配置LLM提供商，请在设置页面配置API密钥")
        
        try:
            provider = self.settings.get("llm_provider", "dashscope")
            model = self.settings.get("model_name", "qwen-plus")
            write_llm_debug_event(
                "call_start",
                {
                    "provider": provider,
                    "model": model,
                    "prompt_preview": summarize_text(prompt, 300),
                    "input_preview": summarize_text(input_data, 500),
                    "kwargs": kwargs,
                },
            )
            response = self.current_provider.call(prompt, input_data, **kwargs)
            write_llm_debug_event(
                "call_success",
                {
                    "provider": provider,
                    "model": model,
                    "response_preview": summarize_text(response.content, 1000),
                    "usage": response.usage,
                    "finish_reason": response.finish_reason,
                },
            )
            write_llm_debug_blob("llm_response", response.content or "")
            return response.content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            write_llm_debug_event(
                "call_error",
                {
                    "provider": self.settings.get("llm_provider", "dashscope"),
                    "model": self.settings.get("model_name", "qwen-plus"),
                    "error": str(e),
                },
            )
            raise
    
    def call_with_retry(self, prompt: str, input_data: Any = None, max_retries: int = 3, **kwargs) -> str:
        """带重试机制的LLM调用"""
        for attempt in range(max_retries):
            try:
                return self.call(prompt, input_data, **kwargs)
            except ValueError:  # 如果是API Key或参数错误，不重试
                raise
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"LLM调用在{max_retries}次重试后彻底失败。")
                    raise
                logger.warning(f"第{attempt + 1}次调用失败，准备重试: {str(e)}")
                import time
                time.sleep(2 ** attempt)  # 指数退避
        return ""
    
    def test_provider_connection(self, provider_type: ProviderType, api_key: str, model_name: str) -> bool:
        """测试提供商连接"""
        try:
            provider_kwargs = self._get_provider_kwargs(provider_type)
            provider = LLMProviderFactory.create_provider(
                provider_type, api_key, model_name, **provider_kwargs
            )
            return provider.test_connection()
        except Exception as e:
            logger.error(f"测试{provider_type.value}连接失败: {e}")
            return False

    def _get_provider_kwargs(self, provider_type: ProviderType) -> Dict[str, Any]:
        """获取提供商专属参数"""
        if provider_type == ProviderType.DASHSCOPE:
            return {
                "base_url": str(self.settings.get("dashscope_http_base_url") or "").strip(),
                "workspace": str(self.settings.get("dashscope_workspace") or "").strip(),
            }
        return {}
    
    def get_current_provider_info(self) -> Dict[str, Any]:
        """获取当前提供商信息"""
        self._refresh_settings_if_changed()
        if not self.current_provider:
            return {"provider": None, "model": None, "available": False}
        
        provider_type = ProviderType(self.settings.get("llm_provider", "dashscope"))
        model_name = self.settings.get("model_name", "qwen-plus")
        
        return {
            "provider": provider_type.value,
            "model": model_name,
            "available": True,
            "display_name": self._get_provider_display_name(provider_type)
        }
    
    def _get_provider_display_name(self, provider_type: ProviderType) -> str:
        """获取提供商显示名称"""
        display_names = {
            ProviderType.DASHSCOPE: "阿里通义千问",
            ProviderType.OPENAI: "OpenAI",
            ProviderType.GEMINI: "Google Gemini",
            ProviderType.SILICONFLOW: "硅基流动"
        }
        return display_names.get(provider_type, provider_type.value)
    
    def get_all_available_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有可用模型"""
        self._refresh_settings_if_changed()
        result = {}

        for provider_type in ProviderType:
            try:
                provider_class = LLMProviderFactory._providers.get(provider_type)
                if not provider_class:
                    models = []
                else:
                    provider_kwargs = self._get_provider_kwargs(provider_type)
                    model_name = self.settings.get("model_name", "qwen-plus")
                    temp_provider = provider_class("dummy_key", model_name, **provider_kwargs)
                    models = temp_provider.get_available_models()
            except Exception as e:
                logger.warning(f"无法获取{provider_type.value}的模型列表: {e}")
                models = []

            provider_name = provider_type.value
            result[provider_name] = [
                {
                    "name": model.name,
                    "display_name": model.display_name,
                    "max_tokens": model.max_tokens,
                    "description": model.description
                }
                for model in models
            ]
        
        return result
    
    def parse_json_response(self, response: str) -> Any:
        """解析JSON响应（保持与原LLMClient的兼容性）"""
        self._refresh_settings_if_changed()
        if not self.current_provider:
            raise ValueError("未配置LLM提供商")
        
        # 这里可以复用原LLMClient的JSON解析逻辑
        # 为了保持兼容性，我们创建一个临时的LLMClient实例
        from ..utils.llm_client import LLMClient
        temp_client = LLMClient()
        return temp_client.parse_json_response(response)

# 全局LLM管理器实例
_llm_manager: Optional[LLMManager] = None

def get_llm_manager() -> LLMManager:
    """获取全局LLM管理器实例"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

def initialize_llm_manager(settings_file: Optional[Path] = None) -> LLMManager:
    """初始化LLM管理器"""
    global _llm_manager
    _llm_manager = LLMManager(settings_file)
    return _llm_manager
