from django.db import models
from django.conf import settings
import uuid
from django.db.models.functions import Lower

class ProfileSkill(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Profile Skill Name"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_profile_skill_name_ci"
            )
        ]

    def __str__(self):
        return self.name
    
class Profile(models.Model):
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    name = models.CharField(
        max_length=100
    )

    bio = models.TextField(
        blank=True
    )

    job_title = models.CharField(
        max_length=150,
        blank=True
    )

    skills = models.ManyToManyField(
        ProfileSkill,
        related_name="profiles",
        blank=True
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True
    )

    contact_links = models.JSONField(
        default=dict, 
        blank=True
    )

    open_to_collaboration = models.BooleanField(
        default=False
    )

    open_to_mentoring = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name or self.user.username


class GoogleProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_profile",
    )
    google_id = models.CharField(max_length=255, unique=True, db_index=True)
    picture = models.URLField(max_length=500, blank=True)
    initial_username = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Google Profile"
        verbose_name_plural = "Google Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.google_id})"
