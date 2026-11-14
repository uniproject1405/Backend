from django.contrib import admin
from .models import MembershipRequest


@admin.register(MembershipRequest)
class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'project__title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_accepted', 'mark_as_rejected']

    @admin.action(description="Mark selected requests as Accepted")
    def mark_as_accepted(self, request, queryset):
        queryset.update(status=MembershipRequest.STATUS_ACCEPTED)

    @admin.action(description="Mark selected requests as Rejected")
    def mark_as_rejected(self, request, queryset):
        queryset.update(status=MembershipRequest.STATUS_REJECTED)

