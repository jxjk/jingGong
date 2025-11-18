from django import forms
from .models import QuotationRequest

class QuotationRequestForm(forms.ModelForm):
    """报价请求表单"""
    
    class Meta:
        model = QuotationRequest
        fields = [
            'name', 'email', 'phone', 'processing_type', 'material',
            'quantity', 'accuracy', 'surface_treatment', 'description', 'model_file'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'processing_type': forms.Select(attrs={'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'accuracy': forms.TextInput(attrs={'class': 'form-control'}),
            'surface_treatment': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'model_file': forms.FileInput(attrs={'class': 'form-control'}),
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
            valid_extensions = ['.step', '.stp', '.stl', '.igs', '.iges']
            ext = str(model_file).split('.')[-1].lower()
            if not ext in [e.replace('.', '') for e in valid_extensions]:
                raise forms.ValidationError(f"只允许上传以下格式的文件: {', '.join(valid_extensions)}")
                
        return model_file