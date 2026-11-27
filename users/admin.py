from django.contrib import admin
from .models import Profile, ProfileSkill, GoogleProfile


@admin.register(ProfileSkill)
class ProfileSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "job_title", "open_to_collaboration", "open_to_mentoring")
    search_fields = ("name", "user__username", "user__email", "job_title")


@admin.register(GoogleProfile)
class GoogleProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "google_id", "initial_username", "created_at")
    search_fields = ("user__username", "user__email", "google_id")
