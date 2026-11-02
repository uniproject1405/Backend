
from django.http import JsonResponse


def users_api(request):
    return JsonResponse({
        "message": "API is working!",
        "status": "success"
    })
