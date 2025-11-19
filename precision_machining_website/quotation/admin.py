from django.contrib import admin
from .models import QuotationRequest, QuotationAdjustmentFactor

@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'processing_type', 'material', 'quantity', 'created_at', 'is_processed')
    list_filter = ('processing_type', 'material', 'is_processed', 'created_at')
    search_fields = ('name', 'email', 'phone', 'description')
    readonly_fields = ('created_at',)
    list_editable = ('is_processed',)
    
    fieldsets = (
        ('客户信息', {
            'fields': ('name', 'email', 'phone')
        }),
        ('项目详情', {
            'fields': ('processing_type', 'material', 'quantity', 'accuracy', 
                      'surface_treatment', 'description', 'model_file')
        }),
        ('3D模型分析结果', {
            'fields': ('volume', 'surface_area', 'bounding_box_length', 
                      'bounding_box_width', 'bounding_box_height', 'min_radius',
                      'max_aspect_ratio', 'complexity_score', 'min_tool_diameter',
                      'machining_difficulty')
        }),
        ('系统信息', {
            'fields': ('created_at', 'is_processed')
        }),
    )


@admin.register(QuotationAdjustmentFactor)
class QuotationAdjustmentFactorAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_editable = ('value', 'is_active')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'value', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')