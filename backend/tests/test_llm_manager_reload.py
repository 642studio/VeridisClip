import json
import os
import time

from backend.core.llm_manager import LLMManager
from backend.core.llm_providers import LLMResponse, ProviderType


class DummyProvider:
    def __init__(self, label: str):
        self.label = label

    def call(self, prompt, input_data=None, **kwargs):
        return LLMResponse(content=f"provider:{self.label}")

    def test_connection(self):
        return True

    def get_available_models(self):
        return []


def _write_settings(path, api_key: str, model_name: str):
    path.write_text(
        json.dumps(
            {
                "llm_provider": "dashscope",
                "dashscope_api_key": api_key,
                "dashscope_http_base_url": "https://dashscope-us.aliyuncs.com/api/v1",
                "dashscope_workspace": "ws-test",
                "model_name": model_name,
                "llm_debug": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_llm_manager_reload_settings_when_file_changed(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    _write_settings(settings_file, "sk-old", "qwen-turbo")

    # 避免测试写入真实调试日志
    monkeypatch.setattr("backend.core.llm_manager.write_llm_debug_event", lambda *a, **k: None)
    monkeypatch.setattr("backend.core.llm_manager.write_llm_debug_blob", lambda *a, **k: None)

    created = []
    providers = [DummyProvider("old"), DummyProvider("new")]

    def fake_create_provider(provider_type, api_key, model_name, **kwargs):
        created.append((provider_type, api_key, model_name, kwargs))
        return providers[len(created) - 1]

    monkeypatch.setattr(
        "backend.core.llm_manager.LLMProviderFactory.create_provider",
        fake_create_provider,
    )

    manager = LLMManager(settings_file=settings_file)
    assert created[-1][0] == ProviderType.DASHSCOPE
    assert created[-1][1] == "sk-old"
    assert created[-1][2] == "qwen-turbo"

    _write_settings(settings_file, "sk-new", "qwen-plus-us")
    now = time.time() + 2
    os.utime(settings_file, (now, now))

    result = manager.call("ping")
    assert result == "provider:new"
    assert created[-1][0] == ProviderType.DASHSCOPE
    assert created[-1][1] == "sk-new"
    assert created[-1][2] == "qwen-plus-us"
