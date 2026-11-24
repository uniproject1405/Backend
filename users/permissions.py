from rest_framework.permissions import BasePermission, SAFE_METHODS
from .utils import is_profile_complete
from .models import Profile


class IsProfileComplete(BasePermission):

    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return False

        return is_profile_complete(profile)