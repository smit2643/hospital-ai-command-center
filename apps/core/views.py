from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render


@login_required
def dashboard_redirect(request):
    role = request.user.role
    if role == request.user.Role.ADMIN:
        return redirect("doctors:approval_list")
    if role == request.user.Role.DOCTOR:
        return redirect("doctors:dashboard")
    if role == request.user.Role.PATIENT:
        return redirect("patients:dashboard")
    return render(request, "core/dashboard.html")


def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/home.html")


def health(request):
    return JsonResponse({"status": "ok", "service": "hospital_ai"})
