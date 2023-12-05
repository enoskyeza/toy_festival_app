# Custom decorator to restrict judge page to judges

def judge_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_judge:  # Assuming is_judge is a boolean field in your Judge model
                return view_func(request, *args, **kwargs)
            else:
                # If the user is logged in but not a judge, handle accordingly
                return redirect('admin_dashboard:dashboard')  # Redirect to an error page or another view
        else:
            # If the user is not logged in, redirect to login page
            return redirect('judge:judge-login')  # Redirect to your login page

    return _wrapped_view