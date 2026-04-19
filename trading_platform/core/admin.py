from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "broker_type", "is_staff", "created_at")
    list_filter = ("is_staff", "is_active", "broker_type")
    search_fields = ("email", "username")
    ordering = ("-created_at",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Trading Settings",
            {
                "fields": (
                    "default_capital",
                    "broker_type",
                    "broker_api_key",
                    "broker_api_secret",
                )
            },
        ),
        ("Preferences", {"fields": ("timezone", "notifications_enabled")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "risk_per_trade_pct", "max_positions", "chart_theme")
    list_filter = ("chart_theme",)
    search_fields = ("user__email",)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "ip_address", "created_at", "expires_at")
    list_filter = ("is_active",)
    search_fields = ("user__email",)
