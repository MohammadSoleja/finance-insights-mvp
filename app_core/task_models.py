"""
Task/Ticket Models for Project Progress Tracking
GitHub-style issue tracking system
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Project, Label, Organization


class TaskStatus(models.TextChoices):
    """Task status options"""
    BACKLOG = 'backlog', 'Backlog'
    TODO = 'todo', 'To Do'
    IN_PROGRESS = 'in_progress', 'In Progress'
    REVIEW = 'review', 'Review'
    DONE = 'done', 'Done'
    BLOCKED = 'blocked', 'Blocked'


class TaskPriority(models.TextChoices):
    """Task priority levels"""
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class Task(models.Model):
    """
    GitHub-style task/ticket for project tracking
    """
    # Basic Info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='tasks')

    # Task Number (auto-incrementing per project)
    task_number = models.IntegerField()

    # Status & Priority
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM
    )

    # Assignment
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    # Hierarchy
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_tasks'
    )

    # Milestone Link
    milestone = models.ForeignKey(
        'ProjectMilestone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    # Labels
    labels = models.ManyToManyField(Label, blank=True, related_name='tasks')

    # Time Tracking
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated hours to complete"
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Actual hours spent"
    )

    # Dates
    due_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Position for Kanban ordering
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['project', 'task_number']]
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['milestone']),
        ]

    def __str__(self):
        return f"#{self.task_number} {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate task number if not set
        if not self.task_number:
            last_task = Task.objects.filter(project=self.project).order_by('-task_number').first()
            self.task_number = (last_task.task_number + 1) if last_task else 1

        # Set completed_at when status changes to done
        if self.status == TaskStatus.DONE and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != TaskStatus.DONE and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != TaskStatus.DONE:
            return timezone.now().date() > self.due_date
        return False

    @property
    def progress_percentage(self):
        """Calculate progress based on sub-tasks"""
        if not self.sub_tasks.exists():
            return 100 if self.status == TaskStatus.DONE else 0

        total = self.sub_tasks.count()
        completed = self.sub_tasks.filter(status=TaskStatus.DONE).count()
        return int((completed / total) * 100)

    @property
    def completed_subtasks_count(self):
        """Get count of completed sub-tasks"""
        return self.sub_tasks.filter(status=TaskStatus.DONE).count()

    @property
    def time_spent_percentage(self):
        """Calculate time spent vs estimated"""
        if not self.estimated_hours or self.estimated_hours == 0:
            return None
        return int((self.actual_hours / self.estimated_hours) * 100)


class TaskComment(models.Model):
    """
    Comments on tasks with @mention support
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    # @mentions tracking
    mentioned_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='task_mentions'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task}"


class TaskTimeEntry(models.Model):
    """
    Time tracking entries for tasks
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    hours = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'Task time entries'

    def __str__(self):
        return f"{self.hours}h on {self.task} by {self.user.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update task's actual_hours
        self.task.actual_hours = self.task.time_entries.aggregate(
            models.Sum('hours')
        )['hours__sum'] or 0
        self.task.save()


class TaskActivity(models.Model):
    """
    Activity log for task changes
    """
    ACTIVITY_TYPES = [
        ('created', 'Created'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
        ('priority_changed', 'Priority Changed'),
        ('commented', 'Commented'),
        ('updated', 'Updated'),
        ('label_added', 'Label Added'),
        ('label_removed', 'Label Removed'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()

    # Store old/new values for changes
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Task activities'

    def __str__(self):
        return f"{self.activity_type} on {self.task} by {self.user.username}"

