from functools import wraps
from django.shortcuts import redirect
from judges.models import Judge

# Custom decorator to restrict judge page to judges
def judge_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                judge_profile = Judge.objects.get(user=request.user)
                if judge_profile.is_judge:  # Assuming is_judge is a boolean field in your Judge model
                    return view_func(request, *args, **kwargs)
            except Judge.DoesNotExist:
                return redirect('admin_dashboard:dashboard')  # Redirect or handle the case where the user isn't a judge
        # If the user is not logged in or not a judge, handle accordingly
        return redirect('judge:judge-login')  # Redirect to an error page or another view

    return _wrapped_view


