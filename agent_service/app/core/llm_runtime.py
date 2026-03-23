import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

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


def _normalize_model_override(
    model_override: dict[str, Any] | None,
    *,
    temperature_override: float | None,
) -> dict[str, Any] | None:
    if not model_override:
        return None

    model = _to_str(model_override.get("model"))
    api_base = _to_str(model_override.get("base_url"))
    api_key = _to_str(model_override.get("api_key"))
    if not (model and api_base and api_key):
        return None

    temperature = (
        _to_float(model_override.get("temperature"), settings.llm_temperature)
        if temperature_override is None
        else float(temperature_override)
    )

    return {
        "label": _to_str(model_override.get("label"), model),
        "model": model,
        "api_base": api_base,
        "api_key": api_key,
        "temperature": temperature,
    }


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
    model_override: dict[str, Any] | None = None,
) -> T:
    resolved_override = _normalize_model_override(
        model_override,
        temperature_override=temperature_override,
    )
    if resolved_override:
        llm = _build_llm(
            model=resolved_override["model"],
            api_base=resolved_override["api_base"],
            api_key=resolved_override["api_key"],
            max_tokens=max_tokens,
            temperature=resolved_override["temperature"],
        )
        return await runner(llm)

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
    mode = str(cfg.get("llm_failover_mode", "single")).strip().lower()
    can_fallback = mode == "dual_fallback" and _has_secondary(cfg)

    secondary_model = _to_str(cfg.get("llm_model_secondary", ""))
    secondary_api_base = _to_str(cfg.get("openai_api_base_secondary", ""))
    secondary_api_key = _to_str(cfg.get("openai_api_key_secondary", ""))
    secondary_temperature = (
        _to_float(cfg.get("llm_temperature_secondary"), settings.llm_temperature)
        if temperature_override is None
        else float(temperature_override)
    )

    # Requested behavior: for creator flow, try "secondary" first, then "primary".
    creator_prefers_secondary = scene.startswith("creator.")
    first_is_secondary = creator_prefers_secondary and can_fallback

    first_model = secondary_model if first_is_secondary else primary_model
    first_api_base = secondary_api_base if first_is_secondary else primary_api_base
    first_api_key = secondary_api_key if first_is_secondary else primary_api_key
    first_temperature = secondary_temperature if first_is_secondary else primary_temperature

    fallback_model = primary_model if first_is_secondary else secondary_model
    fallback_api_base = primary_api_base if first_is_secondary else secondary_api_base
    fallback_api_key = primary_api_key if first_is_secondary else secondary_api_key
    fallback_temperature = primary_temperature if first_is_secondary else secondary_temperature

    first_llm = _build_llm(
        model=first_model,
        api_base=first_api_base,
        api_key=first_api_key,
        max_tokens=max_tokens,
        temperature=first_temperature,
    )

    try:
        return await runner(first_llm)
    except Exception as first_error:
        first_error_text = _safe_error_text(first_error)
        if not can_fallback:
            logger.error(
                "Primary LLM failed without fallback: scene=%s model=%s base=%s error=%s",
                scene,
                first_model,
                first_api_base,
                first_error_text,
            )
            raise RuntimeError(
                f"primary llm failed (model={first_model}, base={first_api_base}): {first_error_text}"
            ) from first_error

        fallback_llm = _build_llm(
            model=fallback_model,
            api_base=fallback_api_base,
            api_key=fallback_api_key,
            max_tokens=max_tokens,
            temperature=fallback_temperature,
        )
        try:
            result = await runner(fallback_llm)
            await push_llm_alert(
                scene=scene,
                primary_model=first_model,
                secondary_model=fallback_model,
                primary_error=first_error_text,
                fallback_succeeded=True,
            )
            logger.warning(
                "LLM failover triggered and recovered: scene=%s primary=%s secondary=%s error=%s",
                scene,
                first_model,
                fallback_model,
                first_error_text,
            )
            return result
        except Exception as fallback_error:
            fallback_error_text = _safe_error_text(fallback_error)
            await push_llm_alert(
                scene=scene,
                primary_model=first_model,
                secondary_model=fallback_model,
                primary_error=first_error_text,
                fallback_succeeded=False,
                secondary_error=fallback_error_text,
            )
            logger.error(
                "LLM failover failed: scene=%s primary=%s secondary=%s primary_error=%s secondary_error=%s",
                scene,
                first_model,
                fallback_model,
                first_error_text,
                fallback_error_text,
            )
            raise
