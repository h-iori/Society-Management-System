from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.html import format_html
from .models import User, Society, Flat, Tenant, MaintenanceBill


class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_name', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff')}),
    )
    
    add_fieldsets = (
        (None, {
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    def get_name(self, obj):
        return obj.get_full_name() or '-'
    get_name.short_description = 'Name'
    
    actions = ['send_login_credentials']
    

class SocietyAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_address', 'get_flats_count']
    search_fields = ['name', 'address']
    
    def get_address(self, obj):
        return obj.address[:60] + '...' if len(obj.address) > 60 else obj.address
    get_address.short_description = 'Address'
    
    def get_flats_count(self, obj):
        count = obj.flats.count()
        return format_html('<strong>{}</strong>', count)
    get_flats_count.short_description = 'Flats'


class FlatAdmin(admin.ModelAdmin):
    list_display = ['flat_number', 'society', 'get_owner', 'get_tenants_count']
    list_filter = ['society']
    search_fields = ['flat_number', 'society__name', 'owner__email']
    raw_id_fields = ['society', 'owner']
    
    def get_owner(self, obj):
        if obj.owner:
            return format_html('<span style="color: green;">● {}</span>', obj.owner.email)
        return format_html('<span style="color: red;">● Not Assigned</span>')
    get_owner.short_description = 'Owner'
    
    def get_tenants_count(self, obj):
        count = obj.tenants.filter(is_active=True).count()
        if count > 0:
            return format_html('<span style="color: blue;">{}</span>', count)
        return '-'
    get_tenants_count.short_description = 'Tenants'


class TenantAdmin(admin.ModelAdmin):
    list_display = ['get_tenant_name', 'flat', 'rent_amount', 'start_date', 'get_status']
    list_filter = ['is_active', 'flat__society']
    search_fields = ['user__email', 'user__first_name', 'flat__flat_number']
    raw_id_fields = ['user', 'flat']
    
    def get_tenant_name(self, obj):
        return obj.user.get_full_name() or obj.user.email
    get_tenant_name.short_description = 'Tenant'
    
    def get_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: white; background: green; padding: 2px 8px; border-radius: 3px;">Active</span>')
        return format_html('<span style="color: white; background: gray; padding: 2px 8px; border-radius: 3px;">Inactive</span>')
    get_status.short_description = 'Status'


class MaintenanceBillAdmin(admin.ModelAdmin):
    list_display = ['get_bill_period', 'flat', 'get_owner', 'amount', 'get_status']
    list_filter = ['status', 'year', 'month']
    search_fields = ['flat__flat_number', 'flat__owner__email', 'flat__society__name']
    raw_id_fields = ['flat']
    
    def get_bill_period(self, obj):
        return f"{obj.get_month_display()} {obj.year}"
    get_bill_period.short_description = 'Period'
    
    def get_owner(self, obj):
        if obj.flat.owner:
            return obj.flat.owner.get_full_name() or obj.flat.owner.email
        return '-'
    get_owner.short_description = 'Owner'
    
    def get_status(self, obj):
        if obj.status == 'PAID':
            return format_html('<span style="color: white; background: #28a745; padding: 3px 12px; border-radius: 3px; font-weight: bold;">PAID</span>')
        return format_html('<span style="color: black; background: #ffc107; padding: 3px 12px; border-radius: 3px; font-weight: bold;">UNPAID</span>')
    get_status.short_description = 'Status'
    
    actions = ['mark_paid', 'mark_unpaid']
    
    def mark_paid(self, request, queryset):
        count = queryset.update(status='PAID')
        self.message_user(request, f'{count} bill(s) marked as paid', messages.SUCCESS)
    mark_paid.short_description = 'Mark as PAID'
    
    def mark_unpaid(self, request, queryset):
        count = queryset.update(status='UNPAID')
        self.message_user(request, f'{count} bill(s) marked as unpaid', messages.WARNING)
    mark_unpaid.short_description = 'Mark as UNPAID'


admin.site.register(User, UserAdmin)
admin.site.register(Society, SocietyAdmin)
admin.site.register(Flat, FlatAdmin)
admin.site.register(Tenant, TenantAdmin)
admin.site.register(MaintenanceBill, MaintenanceBillAdmin)

admin.site.site_header = 'Society Management Admin'
admin.site.site_title = 'Society Admin'
admin.site.index_title = 'Dashboard'