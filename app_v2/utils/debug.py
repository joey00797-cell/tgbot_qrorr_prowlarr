import logging


log = logging.getLogger(
    "torrent_bot"
)


def user_tag(obj):

    user = obj.from_user

    return (
        f"{user.id}"
        f":{user.username}"
    )


def log_action(
    obj,
    action,
    extra=None
):

    msg = (
        f"[USER] "
        f"{user_tag(obj)} | "
        f"{action}"
    )

    if extra:
        msg += f" | {extra}"

    log.info(msg)


def log_error(
    obj,
    action,
    error
):

    log.exception(
        f"[ERROR] "
        f"{user_tag(obj)} | "
        f"{action} | "
        f"{error}"
    )
