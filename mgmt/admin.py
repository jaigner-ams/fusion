from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Dentist, DefaultPriceList, PriceList, CustomUser, CreditPurchase, CreditTransaction, FileUpload

# Configure admin site branding
admin.site.site_header = "AMS Fusion Administration"
admin.site.site_title = "AMS Fusion Admin"
admin.site.index_title = "Welcome to AMS Fusion Administration"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'user_type', 'credits', 'is_staff', 'is_active']
    list_filter = ['user_type', 'is_staff', 'is_active']
    
    fieldsets = UserAdmin.fieldsets + (
        ('User Information', {'fields': ('user_type', 'credits', 'lab_profile_id')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Information', {'fields': ('user_type', 'credits', 'lab_profile_id')}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(user_type='dentist')
        else:
            return qs.none()

class PriceListInline(admin.TabularInline):
    model = PriceList
    extra = 1
    fields = ['applied_after', 'price']
    ordering = ['applied_after']

@admin.register(Dentist)
class DentistAdmin(admin.ModelAdmin):
    list_display = ['name', 'lab', 'get_custom_price_count']
    list_filter = ['lab']
    search_fields = ['name']
    inlines = [PriceListInline]
    
    def get_custom_price_count(self, obj):
        return obj.custom_prices.count()
    get_custom_price_count.short_description = 'Custom Prices'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(lab=request.user)
        else:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change and request.user.is_lab_user():
            obj.lab = request.user
        super().save_model(request, obj, form, change)

@admin.register(DefaultPriceList)
class DefaultPriceListAdmin(admin.ModelAdmin):
    list_display = ['applied_after', 'price', 'lab']
    list_filter = ['lab']
    ordering = ['applied_after']
    list_editable = ['price']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(lab=request.user)
        else:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change and request.user.is_lab_user():
            obj.lab = request.user
        super().save_model(request, obj, form, change)

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['dentist', 'applied_after', 'price']
    list_filter = ['dentist']
    search_fields = ['dentist__name']
    ordering = ['dentist', 'applied_after']
    list_editable = ['price']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(dentist__lab=request.user)
        else:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dentist" and request.user.is_lab_user():
            kwargs["queryset"] = Dentist.objects.filter(lab=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(CreditPurchase)
class CreditPurchaseAdmin(admin.ModelAdmin):
    list_display = ['dentist', 'user', 'quantity', 'quality_type', 'unit_price', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'quality_type', 'created_at']
    search_fields = ['dentist__name', 'user__username']
    readonly_fields = ['created_at', 'completed_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(dentist__lab=request.user)
        else:
            return qs.none()

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'balance_after', 'reason', 'is_reversed', 'created_by', 'created_at']
    list_filter = ['transaction_type', 'is_reversed', 'created_at']
    search_fields = ['user__username', 'reason', 'created_by__username']
    readonly_fields = ['created_at', 'balance_after', 'is_reversed', 'reversed_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'transaction_type', 'amount', 'dentist')
        }),
        ('Reason & Notes', {
            'fields': ('reason', 'notes')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'balance_after', 'is_reversed', 'reversed_by'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            # Show transactions for dentists belonging to this lab
            # Include transactions where dentist is None but user belongs to their dentists
            from django.db.models import Q
            return qs.filter(
                Q(dentist__lab=request.user) | 
                Q(dentist__isnull=True, user__dentist_profile__lab=request.user)
            )
        else:
            return qs.none()
    
    def has_add_permission(self, request):
        # Prevent adding transactions through admin - should be done through the app
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing transactions through admin - they should be immutable
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deleting transactions through admin
        return False

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['dentist', 'original_filename', 'uploaded_by', 'lab', 'status', 'uploaded_at', 'downloaded_at']
    list_filter = ['status', 'uploaded_at', 'lab']
    search_fields = ['dentist__name', 'original_filename', 'uploaded_by__username']
    readonly_fields = ['uploaded_at', 'downloaded_at', 'downloaded_by']
    
    fieldsets = (
        ('File Information', {
            'fields': ('dentist', 'file', 'original_filename', 'description')
        }),
        ('Upload Details', {
            'fields': ('uploaded_by', 'lab', 'uploaded_at')
        }),
        ('Download Information', {
            'fields': ('status', 'downloaded_at', 'downloaded_by')
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user():
            return qs
        elif request.user.is_lab_user():
            return qs.filter(lab=request.user)
        else:
            return qs.none()
    
    def has_add_permission(self, request):
        # Files should be uploaded through the app
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow viewing but not editing
        return request.user.is_superuser or request.user.is_admin_user()
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for admin users
        return request.user.is_superuser or request.user.is_admin_user()