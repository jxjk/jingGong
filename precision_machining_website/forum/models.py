from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class ForumCategory(models.Model):
    """论坛版块模型，用于组织不同主题的子论坛"""
    name = models.CharField('版块名称', max_length=100)
    slug = models.SlugField('URL标识', default='', unique=True, help_text='用于URL的唯一标识，只能包含字母、数字、连字符')
    description = models.TextField('描述', blank=True)
    order = models.PositiveIntegerField('排序', default=0, help_text='数值越小排序越靠前')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '论坛版块'
        verbose_name_plural = '论坛版块'
        ordering = ['order', 'id']
        
    def __str__(self):
        return self.name


class ForumPost(models.Model):
    """论坛帖子模型"""
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, verbose_name='所属版块')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    is_published = models.BooleanField('已发布', default=True)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    
    class Meta:
        verbose_name = '论坛帖子'
        verbose_name_plural = '论坛帖子'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('forum:post_detail', kwargs={'pk': self.pk})


class PostComment(models.Model):
    """帖子评论模型"""
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, verbose_name='所属帖子')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论作者')
    content = models.TextField('评论内容')
    created_at = models.DateTimeField('评论时间', default=timezone.now)
    is_approved = models.BooleanField('已审核', default=True)
    
    class Meta:
        verbose_name = '帖子评论'
        verbose_name_plural = '帖子评论'
        ordering = ['created_at']
        
    def __str__(self):
        return f'{self.author.username} 对 {self.post.title} 的评论'