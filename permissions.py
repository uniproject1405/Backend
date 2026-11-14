from rest_framework import permissions


class IsApplicantOrProjectCreator(permissions.BasePermission):
    """
    Applicant can view or cancel their request.
    Project creator can view or update the status (accept/reject).
    """
    def has_object_permission(self, request, view, obj):
        # Allow applicant and project creator to view
        if request.user == obj.user or request.user == obj.project.creator:
            return True
        return False

