# backend/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, BuyerProfile

# This is an "inline" admin class. It tells Django:
# "When you are showing the CustomUser admin page, also show a form
# for the related BuyerProfile right underneath it."
class BuyerProfileInline(admin.StackedInline):
    model = BuyerProfile
    can_delete = False  # We don't want to accidentally delete a profile
    verbose_name_plural = 'Buyer Profile Information'
    fk_name = 'user'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin interface for our custom user model.
    It integrates the BuyerProfile for users with the 'BUYER' role.
    """
    
    # Use the inline class we defined above
    inlines = (BuyerProfileInline,)

    # --- Display Configuration ---
    # Columns to show in the main user list view
    list_display = ('username', 'name', 'role', 'is_staff', 'is_verified')
    # Filters that appear on the right-hand side
    list_filter = ('role', 'is_staff', 'is_verified', 'groups')
    # Fields you can search by
    search_fields = ('username', 'name', 'email', 'phone_number')
    # Default sorting order
    ordering = ('username',)


    # --- Form Layout Configuration ---
    # This is the layout for the "Change user" page for an existing user.
    # We have removed 'first_name' and 'last_name' and added our custom fields.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('name', 'email', 'phone_number', 'region')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('AgriUnity Specific', {'fields': ('role', 'trust_score', 'is_verified')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # This is the layout for the "Add new user" page.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password', 'password2'), # password2 is for confirmation
        }),
        ('Personal Info', {'fields': ('name', 'email', 'phone_number', 'region')}),
        ('AgriUnity Specific', {'fields': ('role', 'is_verified')}),
    )


    def get_inline_instances(self, request, obj=None):
        """
        This is a clever function that ensures the BuyerProfile form
        ONLY appears on the admin page if the user's role is set to 'BUYER'.
        It will be hidden for Farmers and Admins.
        """
        if not obj or obj.role != CustomUser.Role.BUYER:
            return []
        return super().get_inline_instances(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        This ensures the correct fieldsets are used for adding vs. changing a user.
        """
        self.add_fieldsets = self.add_fieldsets
        return super().get_form(request, obj, **kwargs)