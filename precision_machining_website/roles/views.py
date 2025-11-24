from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import Role, UserRole


def is_superuser(user):
    """检查用户是否为超级管理员"""
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def role_list(request):
    """角色列表页面"""
    roles = Role.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        roles = roles.filter(name__icontains=search_query)
    
    # 分页处理
    paginator = Paginator(roles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'roles/role_list.html', context)


@login_required
@user_passes_test(is_superuser)
def role_create(request):
    """创建角色"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        permission_ids = request.POST.getlist('permissions')
        is_active = bool(request.POST.get('is_active', False))
        
        if not name:
            messages.error(request, '角色名称不能为空')
            return render(request, 'roles/role_form.html', {
                'permissions': Permission.objects.all()
            })
        
        # 检查角色名称是否已存在
        if Role.objects.filter(name=name).exists():
            messages.error(request, '角色名称已存在')
            return render(request, 'roles/role_form.html', {
                'permissions': Permission.objects.all(),
                'name': name,
                'description': description,
                'permission_ids': permission_ids,
                'is_active': is_active
            })
        
        # 创建角色
        with transaction.atomic():
            role = Role.objects.create(
                name=name,
                description=description,
                is_active=is_active
            )
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
        
        messages.success(request, f'角色 "{name}" 创建成功')
        return redirect('roles:role_list')
    
    # GET请求，显示创建表单
    permissions = Permission.objects.all().order_by('content_type__app_label', 'name')
    return render(request, 'roles/role_form.html', {'permissions': permissions})


@login_required
@user_passes_test(is_superuser)
def role_edit(request, role_id):
    """编辑角色"""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        permission_ids = request.POST.getlist('permissions')
        is_active = bool(request.POST.get('is_active', False))
        
        if not name:
            messages.error(request, '角色名称不能为空')
            permission_ids = list(role.permissions.values_list('id', flat=True))
            context = {
                'role': role,
                'permissions': Permission.objects.all().order_by('content_type__app_label', 'name'),
                'permission_ids': permission_ids,
            }
            return render(request, 'roles/role_form.html', context)
        
        # 检查角色名称是否已存在（排除自己）
        if Role.objects.filter(name=name).exclude(id=role_id).exists():
            messages.error(request, '角色名称已存在')
            permission_ids = list(role.permissions.values_list('id', flat=True))
            context = {
                'role': role,
                'permissions': Permission.objects.all().order_by('content_type__app_label', 'name'),
                'permission_ids': permission_ids,
                'name': name,
                'description': description,
                'is_active': is_active
            }
            return render(request, 'roles/role_form.html', context)
        
        # 更新角色
        with transaction.atomic():
            role.name = name
            role.description = description
            role.is_active = is_active
            role.save()
            
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
            else:
                role.permissions.clear()
        
        messages.success(request, f'角色 "{name}" 更新成功')
        return redirect('roles:role_list')
    
    # GET请求，显示编辑表单
    permissions = Permission.objects.all().order_by('content_type__app_label', 'name')
    permission_ids = list(role.permissions.values_list('id', flat=True))
    
    context = {
        'role': role,
        'permissions': permissions,
        'permission_ids': permission_ids,
    }
    return render(request, 'roles/role_form.html', context)


@login_required
@user_passes_test(is_superuser)
def role_delete(request, role_id):
    """删除角色"""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        role_name = role.name
        role.delete()
        messages.success(request, f'角色 "{role_name}" 删除成功')
        return redirect('roles:role_list')
    
    context = {
        'role': role,
    }
    return render(request, 'roles/role_confirm_delete.html', context)


@login_required
@user_passes_test(is_superuser)
def user_role_list(request):
    """用户角色分配列表"""
    users = User.objects.all().order_by('username')
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(username__icontains=search_query) | \
                users.filter(first_name__icontains=search_query) | \
                users.filter(last_name__icontains=search_query) | \
                users.filter(email__icontains=search_query)
    
    # 分页处理
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取所有角色
    roles = Role.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'roles': roles,
    }
    return render(request, 'roles/user_role_list.html', context)


@login_required
@user_passes_test(is_superuser)
def user_role_assign(request, user_id):
    """为用户分配角色"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role_ids = request.POST.getlist('roles')
        
        with transaction.atomic():
            # 清除用户当前的所有角色
            UserRole.objects.filter(user=user).delete()
            
            # 分配新角色
            roles = Role.objects.filter(id__in=role_ids)
            user_roles = [
                UserRole(user=user, role=role, assigned_by=request.user)
                for role in roles
            ]
            UserRole.objects.bulk_create(user_roles)
            
            # 更新用户权限
            user.user_permissions.clear()
            for role in roles:
                user.user_permissions.add(*role.permissions.all())
            
            # 特殊处理管理员角色
            is_admin_role = roles.filter(name__icontains='管理员').exists()
            user.is_staff = is_admin_role
            user.save()
        
        messages.success(request, f'用户 "{user.username}" 的角色分配成功')
        return redirect('roles:user_role_list')
    
    # GET请求，显示分配表单
    roles = Role.objects.filter(is_active=True)
    user_role_ids = list(UserRole.objects.filter(user=user).values_list('role_id', flat=True))
    
    context = {
        'user_obj': user,
        'roles': roles,
        'user_role_ids': user_role_ids,
    }
    return render(request, 'roles/user_role_assign.html', context)