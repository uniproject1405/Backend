from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models.functions import Lower
import uuid


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Skill Name")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Skill"
        verbose_name_plural = "Skills"
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_skill_name_ci'
            )
        ]

    def __str__(self):
        return self.name

class SkillAlias(models.Model):
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='aliases'
    )
    name = models.CharField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return f"{self.name} ({self.skill.name})"

class Project(models.Model):
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PROJECT_TYPE_STARTUP = 'startup'
    PROJECT_TYPE_LEARNING = 'learning'
    PROJECT_TYPE_RESEARCH = 'research'
    PROJECT_TYPE_PERSONAL = 'personal'
    PROJECT_TYPE_OTHER = 'other'

    PROJECT_TYPE_CHOICES = [
        (PROJECT_TYPE_STARTUP, 'Startup'),
        (PROJECT_TYPE_LEARNING, 'Learning'),
        (PROJECT_TYPE_RESEARCH, 'Research'),
        (PROJECT_TYPE_PERSONAL, 'Personal'),
        (PROJECT_TYPE_OTHER, 'Other'),
    ]

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    title = models.CharField(max_length=255, verbose_name="Project Title")
    goal = models.TextField(verbose_name="Project Goal")
    description = models.TextField(blank=True, verbose_name="Project Description")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_projects',
        verbose_name="Creator",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Capacity",
        help_text="Maximum total team capacity",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        verbose_name="Project Status",
    )
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        blank=True,
        verbose_name="Project Type",
    )
    custom_project_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Custom Project Type",
    )
    skills = models.ManyToManyField(
        Skill,
        related_name='projects',
        blank=True,
        verbose_name="Required Skills",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name='project_capacity_gte_1',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=['open', 'closed']),
                name='project_status_valid',
            ),
        ]

    def __str__(self):
        return self.title


class ProjectMember(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name="Project",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name="User",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'],
                name='unique_project_membership',
            ),
        ]
        ordering = ['joined_at']
        verbose_name = "Project Member"
        verbose_name_plural = "Project Members"

    def __str__(self):
        return f"{self.user} in {self.project}"
