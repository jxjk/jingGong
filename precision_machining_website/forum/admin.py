from django.contrib import admin
from .models import ForumCategory, ForumPost


class ForumCategoryAdmin(admin.ModelAdmin):
    """论坛分类后台管理"""
    list_display = ['name', 'order', 'created_at', 'updated_at']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']


class ForumPostAdmin(admin.ModelAdmin):
    """论坛帖子后台管理"""
    list_display = ['title', 'author', 'category', 'is_published', 'view_count', 'created_at']
    list_filter = ['is_published', 'category', 'created_at']
    list_editable = ['is_published']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['author', 'category']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'content', 'author', 'category')
        }),
        ('状态设置', {
            'fields': ('is_published',)
        }),
        ('统计信息', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# 注册模型
admin.site.register(ForumCategory, ForumCategoryAdmin)
admin.site.register(ForumPost, ForumPostAdmin)