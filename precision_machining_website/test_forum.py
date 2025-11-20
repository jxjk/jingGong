#!/usr/bin/env python
"""
论坛功能测试脚本
用于验证论坛模块的基本功能
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'machining_platform.settings')
django.setup()

from django.contrib.auth.models import User
from forum.models import Category, Post, Comment

def test_forum_models():
    """测试论坛模型"""
    print("=== 论坛功能测试 ===")
    
    try:
        # 创建测试用户
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        if created:
            user.set_password('test123')
            user.save()
            print("✓ 创建测试用户")
        else:
            print("✓ 使用现有测试用户")
        
        # 创建测试分类
        category, created = Category.objects.get_or_create(
            name='测试分类',
            defaults={'description': '这是一个测试分类'}
        )
        if created:
            print("✓ 创建测试分类")
        else:
            print("✓ 使用现有测试分类")
        
        # 创建测试帖子
        post, created = Post.objects.get_or_create(
            title='测试帖子',
            defaults={
                'content': '这是一个测试帖子的内容',
                'author': user,
                'category': category
            }
        )
        if created:
            print("✓ 创建测试帖子")
        else:
            print("✓ 使用现有测试帖子")
        
        # 创建测试评论
        comment, created = Comment.objects.get_or_create(
            post=post,
            author=user,
            defaults={'content': '这是一个测试评论'}
        )
        if created:
            print("✓ 创建测试评论")
        else:
            print("✓ 使用现有测试评论")
        
        # 验证数据
        print(f"\n=== 验证数据 ===")
        print(f"分类数量: {Category.objects.count()}")
        print(f"帖子数量: {Post.objects.count()}")
        print(f"评论数量: {Comment.objects.count()}")
        
        # 显示帖子详情
        print(f"\n=== 帖子详情 ===")
        print(f"标题: {post.title}")
        print(f"作者: {post.author.username}")
        print(f"分类: {post.category.name}")
        print(f"内容: {post.content[:50]}...")
        print(f"浏览量: {post.view_count}")
        print(f"创建时间: {post.created_at}")
        
        print("\n✓ 论坛功能测试完成！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_forum_models()
