from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Work, Category


def work_list(request, category_slug=None):
    """作品列表页面"""
    category = None
    works = Work.objects.all()
    categories = Category.objects.all()
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        works = works.filter(category=category)
        
    # 分页处理
    paginator = Paginator(works, 9)  # 每页显示9个作品
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
    }
    return render(request, 'gallery/work_list.html', context)


def work_detail(request, id):
    """作品详情页面"""
    work = get_object_or_404(Work, id=id)
    
    context = {
        'work': work,
    }
    return render(request, 'gallery/work_detail.html', context)