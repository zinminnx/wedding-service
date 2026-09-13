from django.db.models import Q

from weddings.models import Wedding

from .models import WeddingStaffMembership


PERM_VIEW_DASHBOARD = "view_dashboard"
PERM_MANAGE_WEDDING = "manage_wedding"
PERM_VIEW_GUESTS = "view_guests"
PERM_MANAGE_GUESTS = "manage_guests"
PERM_VIEW_INVITATIONS = "view_invitations"
PERM_MANAGE_INVITATIONS = "manage_invitations"
PERM_VIEW_RSVP = "view_rsvp"
PERM_CHECK_IN = "check_in"
PERM_MANAGE_GIFTS = "manage_gifts"
PERM_MANAGE_STAFF = "manage_staff"
PERM_PHOTO = "photo"
PERM_PRINT = "print"

ALL_STAFF_ROLES = {
    WeddingStaffMembership.Role.WEDDING_MANAGER,
    WeddingStaffMembership.Role.RECEPTION_STAFF,
    WeddingStaffMembership.Role.PHOTO_STAFF,
    WeddingStaffMembership.Role.PRINT_STAFF,
    WeddingStaffMembership.Role.VIEWER,
}

PERMISSION_ROLES = {
    PERM_VIEW_DASHBOARD: ALL_STAFF_ROLES,
    PERM_MANAGE_WEDDING: {WeddingStaffMembership.Role.WEDDING_MANAGER},
    PERM_VIEW_GUESTS: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.VIEWER,
    },
    PERM_MANAGE_GUESTS: {WeddingStaffMembership.Role.WEDDING_MANAGER},
    PERM_VIEW_INVITATIONS: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.VIEWER,
    },
    PERM_MANAGE_INVITATIONS: {WeddingStaffMembership.Role.WEDDING_MANAGER},
    PERM_VIEW_RSVP: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.RECEPTION_STAFF,
        WeddingStaffMembership.Role.VIEWER,
    },
    PERM_CHECK_IN: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.RECEPTION_STAFF,
    },
    PERM_MANAGE_GIFTS: {WeddingStaffMembership.Role.WEDDING_MANAGER},
    PERM_MANAGE_STAFF: {WeddingStaffMembership.Role.WEDDING_MANAGER},
    PERM_PHOTO: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.PHOTO_STAFF,
    },
    PERM_PRINT: {
        WeddingStaffMembership.Role.WEDDING_MANAGER,
        WeddingStaffMembership.Role.PRINT_STAFF,
    },
}


def accessible_weddings(user, permission=None):
    qs = Wedding.objects.select_related("owner")
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if user.is_superuser:
        return qs

    query = Q(owner=user)
    allowed_roles = PERMISSION_ROLES.get(permission, ALL_STAFF_ROLES) if permission else ALL_STAFF_ROLES
    if allowed_roles:
        query |= Q(
            staff_memberships__user=user,
            staff_memberships__status=WeddingStaffMembership.Status.ACTIVE,
            staff_memberships__role__in=allowed_roles,
        )
    return qs.filter(query).distinct()


def get_wedding_for_user(user, permission=None):
    return accessible_weddings(user, permission).order_by("-created_at").first()


def get_user_wedding_role(user, wedding):
    if not wedding or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return "SUPER_ADMIN"
    if wedding.owner_id == user.id:
        return "WEDDING_OWNER"
    membership = WeddingStaffMembership.objects.filter(
        wedding=wedding,
        user=user,
        status=WeddingStaffMembership.Status.ACTIVE,
    ).first()
    return membership.role if membership else None


def has_wedding_permission(user, wedding, permission):
    if not wedding or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or wedding.owner_id == user.id:
        return True
    role = get_user_wedding_role(user, wedding)
    return role in PERMISSION_ROLES.get(permission, set())


def can_create_wedding(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    role = getattr(user, "role", "")
    return role in {"SUPER_ADMIN", "ADMIN", "WEDDING_OWNER"}


def access_summary(user, wedding):
    role = get_user_wedding_role(user, wedding)
    labels = {
        "SUPER_ADMIN": "Super Admin",
        "WEDDING_OWNER": "Wedding Owner",
        WeddingStaffMembership.Role.WEDDING_MANAGER: "Wedding Manager",
        WeddingStaffMembership.Role.RECEPTION_STAFF: "Reception Staff",
        WeddingStaffMembership.Role.PHOTO_STAFF: "Photo Staff",
        WeddingStaffMembership.Role.PRINT_STAFF: "Print Staff",
        WeddingStaffMembership.Role.VIEWER: "Viewer",
    }
    return {
        "role": role,
        "role_label": labels.get(role, "Wedding User"),
        "can_create_wedding": can_create_wedding(user),
        "manage_wedding": has_wedding_permission(user, wedding, PERM_MANAGE_WEDDING),
        "view_guests": has_wedding_permission(user, wedding, PERM_VIEW_GUESTS),
        "manage_guests": has_wedding_permission(user, wedding, PERM_MANAGE_GUESTS),
        "view_invitations": has_wedding_permission(user, wedding, PERM_VIEW_INVITATIONS),
        "manage_invitations": has_wedding_permission(user, wedding, PERM_MANAGE_INVITATIONS),
        "view_rsvp": has_wedding_permission(user, wedding, PERM_VIEW_RSVP),
        "check_in": has_wedding_permission(user, wedding, PERM_CHECK_IN),
        "manage_gifts": has_wedding_permission(user, wedding, PERM_MANAGE_GIFTS),
        "manage_staff": has_wedding_permission(user, wedding, PERM_MANAGE_STAFF),
        "photo": has_wedding_permission(user, wedding, PERM_PHOTO),
        "print": has_wedding_permission(user, wedding, PERM_PRINT),
    }
