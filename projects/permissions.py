from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.utils import is_profile_complete
from users.models import Profile


class IsCreatorOrReadOnly(BasePermission):
    """
    Allow anyone to view a project.
    Only the creator with a complete profile can update or delete it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        if obj.creator_id != request.user.id:
            return False

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return False

        return is_profile_complete(profile)