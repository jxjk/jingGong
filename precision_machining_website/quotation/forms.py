from django import forms
from .models import QuotationRequest, QuotationAdjustmentFactor

class QuotationRequestForm(forms.ModelForm):
    """报价请求表单"""
    class Meta:
        model = QuotationRequest
        fields = ['email', 'phone', 'contact_person', 'part_name', 'processing_type', 'material', 
                 'quantity', 'accuracy', 'surface_treatment', 'description', 'model_file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 设置联系人字段为必填
        self.fields['contact_person'].required = True

    def clean_contact_person(self):
        contact_person = self.cleaned_data.get('contact_person')
        if not contact_person:
            raise forms.ValidationError("联系人字段是必填的。")
        return contact_person


class QuotationUpdateForm(forms.ModelForm):
    class Meta:
        model = QuotationRequest
        fields = ['final_price', 'material_cost', 'processing_cost', 'programming_cost', 
                  'surface_treatment_cost', 'packaging_shipping_cost', 'tax_cost', 'other_cost',
                  'profit_margin', 'profit_amount', 'price_explanation', 'status']
        widgets = {
            'final_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'material_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'processing_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'programming_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'surface_treatment_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'packaging_shipping_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'tax_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'other_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'profit_margin': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '例如: 20.00 表示20%利润率'
            }),
            'profit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'price_explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
        }


class QuotationAdjustmentFactorForm(forms.ModelForm):
    """报价调控因子表单"""
    class Meta:
        model = QuotationAdjustmentFactor
        fields = ['name', 'description', 'value', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'value': forms.NumberInput(attrs={'step': '0.01'}),
        }
        
    def clean_quantity(self):
        """验证数量字段"""
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError("数量必须大于0")
        return quantity
        
    def clean_model_file(self):
        """验证上传文件"""
        model_file = self.cleaned_data.get('model_file', False)
        if model_file:
            # 检查文件大小（限制为50MB）
            if model_file.size > 50 * 1024 * 1024:
                raise forms.ValidationError("文件大小不能超过50MB")
            
            # 检查文件类型
            valid_extensions = ['.step', '.stp', '.stl', '.igs', '.iges', '.obj']
            ext = '.' + str(model_file).split('.')[-1].lower()  # 保留点号便于比较
            if ext not in valid_extensions:
                # 强调STEP格式在提示中
                raise forms.ValidationError(f"只允许上传以下格式的文件: {', '.join(valid_extensions)}。推荐使用STEP(.step/.stp)格式以获得最佳兼容性。")
                
        return model_file