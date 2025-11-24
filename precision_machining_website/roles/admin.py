from django.contrib import admin
from django.contrib.auth.models import Permission
from .models import Role, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)
    ordering = ('name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_at', 'assigned_by')
    list_filter = ('role', 'assigned_at')
    search_fields = ('user__username', 'role__name')
    ordering = ('user', 'role')


# 注册权限模型到管理后台
admin.site.register(Permission)