from rest_framework import permissions


class IsScanQueueWorkerAPIUser(permissions.BasePermission):
    """Allow access to a user who is a part of the `scan_queue_workers` group"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name="scan_queue_workers").exists()
