from rest_framework import permissions


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own data,
    but staff can access the list view and all users' details.
    """
    def has_object_permission(self, request, view, obj):
        # Allow staff to view any object, and allow the user to view their own object
        return request.user.is_staff or obj.id == request.user.id

    def has_permission(self, request, view):
        # Allow staff to view the list view, but non-staff cannot
        if view.action == 'list':
            return request.user.is_staff
        # Allow detail view (retrieve) for the object's owner
        return True
    
class DeleteNotAllowed(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own data,
    but staff can access the list view and all users' details.
    """
    def has_permission(self, request, view):
        # Allow DELETE if the user is staff, otherwise deny
        if request.method == 'DELETE' and not request.user.is_staff:
            return False
        return True