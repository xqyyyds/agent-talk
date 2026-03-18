import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.llm_alerts import push_llm_alert
from app.core.runtime_config import get_runtime_config


logger = logging.getLogger("agent_service")
T = TypeVar("T")


def _to_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _to_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_llm(
    *,
    model: str,
    api_base: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_base=api_base,
        openai_api_key=api_key,
        max_tokens=max_tokens,
    )


def _has_secondary(cfg: dict[str, object]) -> bool:
    return bool(
        str(cfg.get("openai_api_base_secondary", "")).strip()
        and str(cfg.get("openai_api_key_secondary", "")).strip()
        and str(cfg.get("llm_model_secondary", "")).strip()
    )


def _safe_error_text(exc: Exception) -> str:
    text = str(exc).strip()
    if not text:
        text = exc.__class__.__name__
    return text[:2000]


def _ensure_primary_config(*, model: str, api_base: str, api_key: str) -> None:
    missing: list[str] = []
    if not model:
        missing.append("llm_model")
    if not api_base:
        missing.append("openai_api_base")
    if not api_key:
        missing.append("openai_api_key")
    if missing:
        raise ValueError(f"primary llm config missing: {', '.join(missing)}")


async def run_with_llm_failover(
    *,
    scene: str,
    runner: Callable[[ChatOpenAI], Awaitable[T]],
    max_tokens: int,
    temperature_override: float | None = None,
) -> T:
    cfg = await get_runtime_config()
    primary_model = _to_str(cfg.get("llm_model", settings.llm_model))
    primary_api_base = _to_str(cfg.get("openai_api_base", settings.openai_api_base))
    primary_api_key = _to_str(cfg.get("openai_api_key", settings.openai_api_key))
    _ensure_primary_config(
        model=primary_model,
        api_base=primary_api_base,
        api_key=primary_api_key,
    )
    primary_temperature = (
        _to_float(cfg.get("llm_temperature"), settings.llm_temperature)
        if temperature_override is None
        else float(temperature_override)
    )
    primary_llm = _build_llm(
        model=primary_model,
        api_base=primary_api_base,
        api_key=primary_api_key,
        max_tokens=max_tokens,
        temperature=primary_temperature,
    )

    try:
        return await runner(primary_llm)
    except Exception as primary_error:
        primary_error_text = _safe_error_text(primary_error)
        mode = str(cfg.get("llm_failover_mode", "single")).strip().lower()
        can_fallback = mode == "dual_fallback" and _has_secondary(cfg)
        if not can_fallback:
            logger.error(
                "Primary LLM failed without fallback: scene=%s model=%s base=%s error=%s",
                scene,
                primary_model,
                primary_api_base,
                primary_error_text,
            )
            raise RuntimeError(
                f"primary llm failed (model={primary_model}, base={primary_api_base}): {primary_error_text}"
            ) from primary_error

        secondary_model = _to_str(cfg.get("llm_model_secondary", ""))
        secondary_temperature = (
            _to_float(cfg.get("llm_temperature_secondary"), settings.llm_temperature)
            if temperature_override is None
            else float(temperature_override)
        )
        secondary_llm = _build_llm(
            model=secondary_model,
            api_base=_to_str(cfg.get("openai_api_base_secondary", "")),
            api_key=_to_str(cfg.get("openai_api_key_secondary", "")),
            max_tokens=max_tokens,
            temperature=secondary_temperature,
        )
        try:
            result = await runner(secondary_llm)
            await push_llm_alert(
                scene=scene,
                primary_model=primary_model,
                secondary_model=secondary_model,
                primary_error=primary_error_text,
                fallback_succeeded=True,
            )
            logger.warning(
                "LLM failover triggered and recovered: scene=%s primary=%s secondary=%s error=%s",
                scene,
                primary_model,
                secondary_model,
                primary_error_text,
            )
            return result
        except Exception as secondary_error:
            secondary_error_text = _safe_error_text(secondary_error)
            await push_llm_alert(
                scene=scene,
                primary_model=primary_model,
                secondary_model=secondary_model,
                primary_error=primary_error_text,
                fallback_succeeded=False,
                secondary_error=secondary_error_text,
            )
            logger.error(
                "LLM failover failed: scene=%s primary=%s secondary=%s primary_error=%s secondary_error=%s",
                scene,
                primary_model,
                secondary_model,
                primary_error_text,
                secondary_error_text,
            )
            raise
