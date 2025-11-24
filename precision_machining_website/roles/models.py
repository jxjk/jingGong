from django.db import models
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """
    角色模型，用于定义系统中的各种角色
    """
    name = models.CharField(_('角色名称'), max_length=100, unique=True)
    description = models.TextField(_('角色描述'), blank=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('权限'),
        blank=True,
        related_name='roles'
    )
    is_active = models.BooleanField(_('是否激活'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('角色')
        verbose_name_plural = _('角色')
        db_table = 'roles_role'

    def __str__(self):
        return self.name

    def assign_to_user(self, user):
        """
        将角色分配给用户
        """
        # 将角色的权限分配给用户
        user.user_permissions.set(self.permissions.all())
        # 如果角色名称为管理员相关，则设置is_staff为True
        if '管理员' in self.name or '管理' in self.name:
            user.is_staff = True
        user.save()


class UserRole(models.Model):
    """
    用户角色关联模型
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('用户')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        verbose_name=_('角色')
    )
    assigned_at = models.DateTimeField(_('分配时间'), auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('分配人'),
        related_name='assigned_roles'
    )

    class Meta:
        verbose_name = _('用户角色')
        verbose_name_plural = _('用户角色')
        db_table = 'roles_userrole'
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"