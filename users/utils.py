def is_profile_complete(profile):
    if not profile.name or not profile.name.strip():
        return False

    if not profile.job_title or not profile.job_title.strip():
        return False

    if not profile.skills.exists():
        return False

    return True