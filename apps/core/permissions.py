from django.core.exceptions import PermissionDenied


def require_role(user, *roles: str):
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    if user.role not in roles and not user.is_superuser:
        raise PermissionDenied("You do not have permission for this action")


def doctor_can_access_patient(user, patient_profile) -> bool:
    if user.is_superuser or user.role == user.Role.ADMIN:
        return True
    if user.role == user.Role.PATIENT:
        return patient_profile.user_id == user.id
    if user.role != user.Role.DOCTOR:
        return False
    return patient_profile.assignments.filter(doctor__user_id=user.id, is_active=True).exists()
