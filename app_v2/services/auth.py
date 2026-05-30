import config

from storage.users import get_user


def is_hardware_admin(user_id: int) -> bool:

    return user_id == config.ADMIN_ID


def is_admin(user_id: int) -> bool:

    if is_hardware_admin(user_id):
        return True

    user = get_user(user_id)

    if not user:
        return False

    return user.get("role") == "admin"


def is_active(user_id: int) -> bool:

    if is_admin(user_id):
        return True

    user = get_user(user_id)

    if not user:
        return False

    return user.get("status") == "active"


def is_pending(user_id: int) -> bool:

    user = get_user(user_id)

    if not user:
        return False

    return user.get("status") == "pending"
