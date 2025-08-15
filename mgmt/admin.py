from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Dentist, DefaultPriceList, PriceList, CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'user_type', 'is_staff', 'is_active']
    list_filter = ['user_type', 'is_staff', 'is_active']
    
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
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