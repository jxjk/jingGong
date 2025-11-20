from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import ForumCategory, ForumPost, PostComment
from .forms import ForumPostForm, PostCommentForm


def category_list(request):
    """显示所有论坛版块"""
    categories = ForumCategory.objects.annotate(post_count=Count('forumpost')).order_by('order', 'id')
    return render(request, 'forum/category_list.html', {'categories': categories})


def post_list(request, category_id):
    """显示指定版块下的帖子列表"""
    category = get_object_or_404(ForumCategory, id=category_id)
    posts = ForumPost.objects.filter(category=category, is_published=True).select_related('author', 'category')
    
    # 分页处理
    paginator = Paginator(posts, 10)  # 每页显示10个帖子
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'forum/post_list.html', context)


def post_detail(request, pk):
    """显示帖子详情"""
    post = get_object_or_404(ForumPost, pk=pk, is_published=True)
    # 增加浏览量
    post.view_count += 1
    post.save(update_fields=['view_count'])
    
    # 获取该帖子的所有评论
    comments = post.postcomment_set.filter(is_approved=True)
    
    # 处理评论表单
    if request.method == 'POST':
        if request.user.is_authenticated:
            comment_form = PostCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                messages.success(request, '评论已成功发布！')
                return redirect('forum:post_detail', pk=post.pk)
        else:
            messages.error(request, '请先登录后再发表评论。')
            return redirect('login')
    else:
        comment_form = PostCommentForm()
    
    return render(request, 'forum/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form
    })


@login_required
def post_create(request):
    """创建新帖子"""
    if request.method == 'POST':
        form = ForumPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, '帖子已成功发布！')
            return redirect('forum:post_detail', pk=post.pk)
    else:
        form = ForumPostForm()
    return render(request, 'forum/post_form.html', {'form': form, 'title': '发布新帖子'})


@login_required
def post_edit(request, pk):
    """编辑帖子"""
    post = get_object_or_404(ForumPost, pk=pk, author=request.user)
    
    if request.method == 'POST':
        form = ForumPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, '帖子已成功更新！')
            return redirect('forum:post_detail', pk=post.pk)
    else:
        form = ForumPostForm(instance=post)
    return render(request, 'forum/post_form.html', {'form': form, 'title': '编辑帖子'})