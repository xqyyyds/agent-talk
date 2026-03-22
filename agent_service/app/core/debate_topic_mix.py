import random


TRACK_PLATFORM_HUMAN_AI = "platform_human_ai"
TRACK_GENERAL_HUMAN_AI = "general_human_ai"
TRACK_GENERAL_CONTROVERSY = "general_controversy"

TRACK_LABELS = {
    TRACK_PLATFORM_HUMAN_AI: "平台相关人机冲突",
    TRACK_GENERAL_HUMAN_AI: "通用人机冲突",
    TRACK_GENERAL_CONTROVERSY: "其他高争议辩题",
}


def select_topic_track(roll: float | None = None) -> str:
    value = random.random() if roll is None else max(0.0, min(0.999999, float(roll)))
    if value < 0.42:
        return TRACK_PLATFORM_HUMAN_AI
    if value < 0.70:
        return TRACK_GENERAL_HUMAN_AI
    return TRACK_GENERAL_CONTROVERSY


def get_track_label(track: str) -> str:
    return TRACK_LABELS.get(track, TRACK_LABELS[TRACK_GENERAL_CONTROVERSY])
