"""
Core models for user management and authentication.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """Custom User model with trading-specific fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    # Trading settings
    default_capital = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=100000.00,
        help_text="Default capital for backtesting",
    )

    # Broker credentials (encrypted in production)
    broker_api_key = models.CharField(max_length=255, blank=True)
    broker_api_secret = models.CharField(max_length=255, blank=True)
    broker_type = models.CharField(max_length=50, default="paper")

    # Preferences
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")
    notifications_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    """Extended user profile for trading preferences."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Risk preferences
    risk_per_trade_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="Default risk percentage per trade",
    )
    max_daily_loss_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text="Maximum daily loss percentage",
    )
    max_positions = models.IntegerField(default=3)

    # UI preferences
    chart_theme = models.CharField(max_length=20, default="dark")
    default_chart_interval = models.CharField(max_length=10, default="5m")

    # Trading hours
    trading_start_time = models.TimeField(default="09:15:00")
    trading_end_time = models.TimeField(default="15:30:00")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile for {self.user.email}"


class UserSession(models.Model):
    """Track user sessions for multi-device support."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")

    token = models.CharField(max_length=500, unique=True)
    refresh_token = models.CharField(max_length=500, unique=True)

    device_info = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session for {self.user.email}"
