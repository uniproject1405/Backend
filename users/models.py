from django.db import models
from django.conf import settings


class GoogleProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_profile",
    )
    google_id = models.CharField(max_length=255, unique=True, db_index=True)
    picture = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Google Profile"
        verbose_name_plural = "Google Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.google_id})"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    name = models.CharField(max_length=100, blank=True, verbose_name="Full Name")
    headline = models.CharField(max_length=150, blank=True, verbose_name="Headline")
    bio = models.TextField(blank=True, verbose_name="Bio")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="Avatar")
    avatar_url = models.URLField(max_length=500, blank=True, verbose_name="Avatar URL")
    skills = models.ManyToManyField(
        'projects.Skill',
        related_name='profiles',
        blank=True,
        verbose_name="Skills",
    )
    contact_links = models.JSONField(default=list, blank=True, verbose_name="Contact Links")
    open_to_collaboration = models.BooleanField(default=True, verbose_name="Open to Collaboration")
    open_to_mentoring = models.BooleanField(default=False, verbose_name="Open to Mentoring")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.user.username

    @property
    def display_name(self):
        return self.name or self.user.username

    @property
    def open_for_collaboration(self):
        return self.open_to_collaboration

    @property
    def open_for_mentoring(self):
        return self.open_to_mentoring

    def get_contact(self, platform):
        if isinstance(self.contact_links, dict):
            return self.contact_links.get(platform, '')
        if isinstance(self.contact_links, list):
            for item in self.contact_links:
                if isinstance(item, dict) and platform in item:
                    return item[platform]
        return ''

    @property
    def telegram(self):
        return self.get_contact('telegram')

    @property
    def instagram(self):
        return self.get_contact('instagram')

    @property
    def github(self):
        return self.get_contact('github')

    @property
    def linkedin(self):
        return self.get_contact('linkedin')

