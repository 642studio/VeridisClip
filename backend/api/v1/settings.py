"""
设置API路由
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from pathlib import Path

router = APIRouter()
API_KEY_FIELDS = [
    "dashscope_api_key",
    "openai_api_key",
    "gemini_api_key",
    "siliconflow_api_key",
]

class SettingsRequest(BaseModel):
    """设置请求模型"""
    # 多提供商支持
    llm_provider: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    dashscope_http_base_url: Optional[str] = None
    dashscope_workspace: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    siliconflow_api_key: Optional[str] = None
    model_name: Optional[str] = None
    chunk_size: Optional[int] = None
    min_score_threshold: Optional[float] = None
    max_clips_per_collection: Optional[int] = None
    llm_debug: Optional[bool] = None

class ApiKeyTestRequest(BaseModel):
    """API密钥测试请求"""
    provider: str
    api_key: str
    model_name: str

class ApiKeyTestResponse(BaseModel):
    """API密钥测试响应"""
    success: bool
    error: Optional[str] = None

def get_settings_file_path() -> Path:
    """获取设置文件路径"""
    from ...core.path_utils import get_settings_file_path as get_settings_path
    return get_settings_path()

def load_settings() -> Dict[str, Any]:
    """加载设置"""
    settings_file = get_settings_file_path()
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
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                # 合并默认设置和保存的设置
                default_settings.update(saved_settings)
        except Exception as e:
            print(f"加载设置文件失败: {e}")
    
    return default_settings

def save_settings(settings: Dict[str, Any]):
    """保存设置"""
    settings_file = get_settings_file_path()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar configuracion: {e}")

def _mask_api_key(value: str) -> str:
    """Mask API keys for read operations."""
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"

def _is_masked_key_value(value: str) -> bool:
    """Detect masked placeholder values returned by this API."""
    return bool(value) and "*" in value

@router.get("/")
async def get_settings():
    """获取系统设置"""
    try:
        settings = load_settings()
        safe_settings = dict(settings)
        for field in API_KEY_FIELDS:
            raw_value = str(settings.get(field) or "")
            safe_settings[field] = _mask_api_key(raw_value)
            safe_settings[f"has_{field}"] = bool(raw_value)
        return safe_settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar configuracion: {e}")

@router.post("/")
async def update_settings(request: SettingsRequest):
    """更新系统设置"""
    try:
        settings = load_settings()

        def apply_api_key_update(field: str, value: Optional[str]) -> None:
            if value is None:
                return
            if _is_masked_key_value(value):
                return
            settings[field] = value
        
        # 更新多提供商设置
        if request.llm_provider is not None:
            settings["llm_provider"] = request.llm_provider
        
        if request.dashscope_api_key is not None:
            apply_api_key_update("dashscope_api_key", request.dashscope_api_key)

        if request.dashscope_http_base_url is not None:
            settings["dashscope_http_base_url"] = request.dashscope_http_base_url.strip()

        if request.dashscope_workspace is not None:
            settings["dashscope_workspace"] = request.dashscope_workspace.strip()
        
        if request.openai_api_key is not None:
            apply_api_key_update("openai_api_key", request.openai_api_key)
        
        if request.gemini_api_key is not None:
            apply_api_key_update("gemini_api_key", request.gemini_api_key)
        
        if request.siliconflow_api_key is not None:
            apply_api_key_update("siliconflow_api_key", request.siliconflow_api_key)
        
        if request.model_name is not None:
            settings["model_name"] = request.model_name
        
        if request.chunk_size is not None:
            settings["chunk_size"] = request.chunk_size
        
        if request.min_score_threshold is not None:
            settings["min_score_threshold"] = request.min_score_threshold
        
        if request.max_clips_per_collection is not None:
            settings["max_clips_per_collection"] = request.max_clips_per_collection

        if request.llm_debug is not None:
            settings["llm_debug"] = request.llm_debug

        # 同步环境变量（保持兼容性）
        os.environ["DASHSCOPE_API_KEY"] = str(settings.get("dashscope_api_key") or "")
        dashscope_base_url = str(settings.get("dashscope_http_base_url") or "").strip()
        if dashscope_base_url:
            os.environ["DASHSCOPE_HTTP_BASE_URL"] = dashscope_base_url
        else:
            os.environ.pop("DASHSCOPE_HTTP_BASE_URL", None)
        
        # 保存设置
        save_settings(settings)
        
        # 更新LLM管理器
        try:
            from ...core.llm_manager import get_llm_manager
            llm_manager = get_llm_manager()
            llm_manager.update_settings(settings)
        except Exception as e:
            print(f"更新LLM管理器失败: {e}")
        
        return {"message": "Configuracion actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar configuracion: {e}")

@router.post("/test-api-key")
async def test_api_key(request: ApiKeyTestRequest) -> ApiKeyTestResponse:
    """测试API密钥"""
    try:
        # 导入LLM管理器
        from ...core.llm_providers import ProviderType, LLMProviderFactory
        
        # 验证提供商类型
        try:
            provider_type = ProviderType(request.provider)
        except ValueError:
            return ApiKeyTestResponse(success=False, error=f"Proveedor no soportado: {request.provider}")

        provider_kwargs: Dict[str, Any] = {}
        if provider_type == ProviderType.DASHSCOPE:
            runtime_settings = load_settings()
            provider_kwargs = {
                "base_url": str(runtime_settings.get("dashscope_http_base_url") or "").strip(),
                "workspace": str(runtime_settings.get("dashscope_workspace") or "").strip(),
            }

        provider = LLMProviderFactory.create_provider(
            provider_type,
            request.api_key,
            request.model_name,
            **provider_kwargs,
        )
        response = provider.call("Responde exactamente: OK")
        if response.content and response.content.strip():
            return ApiKeyTestResponse(success=True)
        return ApiKeyTestResponse(success=False, error="Conexion establecida pero respuesta vacia del modelo")
                
    except Exception as e:
        return ApiKeyTestResponse(success=False, error=str(e))

@router.get("/available-models")
async def get_available_models():
    """获取所有可用模型"""
    try:
        from ...core.llm_manager import get_llm_manager
        llm_manager = get_llm_manager()
        return llm_manager.get_all_available_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener modelos disponibles: {e}")

@router.get("/current-provider")
async def get_current_provider():
    """获取当前提供商信息"""
    try:
        from ...core.llm_manager import get_llm_manager
        llm_manager = get_llm_manager()
        return llm_manager.get_current_provider_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el proveedor actual: {e}") 
