from django.contrib import admin
from .models import QuotationRequest

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