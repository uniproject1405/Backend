import re


def is_profile_complete(profile):
    if not profile:
        return False

    # 1. Mandatory Profile Fields: Name must be non-empty
    if not profile.name or not profile.name.strip():
        return False

    # 2. Mandatory Profile Fields: At least one skill must be assigned
    if not profile.skills.exists():
        return False

    # 3. Google OAuth check: User remains a Viewer until they customize their username
    user = profile.user
    if hasattr(user, "google_profile"):
        initial = getattr(user.google_profile, "initial_username", None)
        if initial and user.username.strip().lower() == initial.strip().lower():
            return False
        if re.fullmatch(r"user_[0-9a-f]{8}", user.username.strip().lower()):
            return False

    return True
