from django.contrib import admin
from .models import QuotationRequest, QuotationAdjustmentFactor

@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'processing_type', 'material', 'quantity', 'status', 'estimated_price', 'final_price', 'created_at']
    list_filter = ['processing_type', 'material', 'status', 'surface_treatment', 'created_at']
    search_fields = ['id', 'name', 'email', 'part_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'email', 'phone', 'customer', 'contact_person')
        }),
        ('项目信息', {
            'fields': ('part_name', 'processing_type', 'material', 'quantity', 'accuracy', 'surface_treatment', 'description', 'model_file')
        }),
        ('3D模型分析结果', {
            'fields': ('volume', 'surface_area', 'bounding_box_length', 'bounding_box_width', 'bounding_box_height',
                      'min_radius', 'max_aspect_ratio', 'complexity_score', 'min_tool_diameter', 'machining_difficulty',
                      'oc_curved_surfaces', 'oc_sharp_edges', 'oc_holes', 'oc_undercuts', 'oc_min_tolerance',
                      'oc_estimated_weight', 'oc_machining_difficulty', 'cq_cnc_difficulty_level',
                      'cq_cnc_difficulty_score', 'cq_estimated_cost', 'cq_fillets', 'cq_finishing_time',
                      'cq_holes', 'cq_recommended_process', 'cq_roughing_time', 'cq_thin_walls', 'cq_utilization_percent',
                      'cq_waste_volume'),
            'classes': ('collapse',)
        }),
        ('DMF设计因子', {
            'fields': ('dmf_volume_factor', 'dmf_surface_area_factor', 'dmf_complexity_factor', 
                      'dmf_precision_factor', 'dmf_feature_factor'),
            'classes': ('collapse',)
        }),
        ('报价信息', {
            'fields': ('status', 'estimated_price', 'final_price', 'price_explanation',
                      'material_cost', 'processing_cost', 'programming_cost', 
                      'surface_treatment_cost', 'packaging_shipping_cost', 'tax_cost', 'other_cost')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'is_processed')
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