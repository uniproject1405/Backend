from django.db import models
from django.conf import settings
import uuid

class MembershipRequest(models.Model):
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='membership_requests',
        verbose_name="Project",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='membership_requests',
        verbose_name="Applicant",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Status",
    )
    message = models.TextField(blank=True, verbose_name="Application Message")
    response_message = models.TextField(blank=True, verbose_name="Response Message")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'],
                condition=models.Q(status='pending'),
                name='unique_pending_membership_request',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=['pending', 'accepted', 'rejected']),
                name='membership_request_status_valid',
            ),
        ]
        ordering = ['-created_at']
        verbose_name = "Membership Request"
        verbose_name_plural = "Membership Requests"

    def __str__(self):
        return f"Request by {self.user} for {self.project} ({self.status})"
