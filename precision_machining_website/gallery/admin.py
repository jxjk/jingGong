from django.contrib import admin
from .models import Category, Work

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured', 'created_at')
    search_fields = ('title', 'description', 'project_background')
    ordering = ('-created_at',)
    
    # 设置只读字段
    readonly_fields = ('created_at', 'updated_at')
    
    # 定义字段分组显示
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'category', 'description', 'is_featured')
        }),
        ('项目详情', {
            'fields': ('project_background', 'process_difficulties', 
                      'equipment_used', 'materials', 'process_techniques',
                      'project_duration')
        }),
        ('媒体文件', {
            'fields': ('image', 'model_file', 'video_url')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )