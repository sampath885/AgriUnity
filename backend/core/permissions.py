from rest_framework.permissions import BasePermission


class IsAuthenticatedAndFarmer(BasePermission):
    """Allow only authenticated users with FARMER role."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "FARMER")


class IsAuthenticatedAndVerifiedBuyer(BasePermission):
    """Allow only authenticated users with BUYER role who are verified."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "BUYER"
            and getattr(user, "is_verified", False)
        )


