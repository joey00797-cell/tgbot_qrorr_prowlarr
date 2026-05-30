import datetime


def progress_bar(progress: float, length=8):

    filled = int(round(length * progress))

    return (
        "■" * filled +
        "▨" * (length - filled)
    )


def format_eta(seconds):

    if seconds < 0:
        return "∞"

    if seconds > 86400 * 7:
        return "∞"

    return str(
        datetime.timedelta(
            seconds=seconds
        )
    )


def readable_state(state, progress):

    if state in ["downloading", "metaDL"]:
        return "📥 Скачивается"

    if state in ["pausedDL", "stoppedDL"]:

        if progress < 1:
            return "⏸ Пауза"

        return "✅ Готов"

    if state == "stalledDL":
        return "⏳ Нет сидов"

    if state == "uploading":
        return "📤 Раздается"

    if state in [
        "stalledUP",
        "pausedUP",
        "queuedUP"
    ]:
        return "✅ Раздача"

    return state
