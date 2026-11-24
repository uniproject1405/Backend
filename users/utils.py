def is_profile_complete(profile):
    if not profile.name or not profile.name.strip():
        return False

    if not profile.skills.exists():
        return False

    return True