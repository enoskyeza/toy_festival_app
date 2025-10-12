import logging

logger = logging.getLogger(__name__)


class AuthenticationDebugMiddleware:
    """
    Middleware to log authentication headers for debugging cross-origin auth issues
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log authentication-related headers
        auth_header = request.headers.get('Authorization', 'No Authorization header')
        origin = request.headers.get('Origin', 'No Origin header')
        
        # Only log for API endpoints
        if request.path.startswith('/register/') or request.path.startswith('/score/'):
            logger.info(
                f"Auth Debug - Path: {request.path}, "
                f"Method: {request.method}, "
                f"Origin: {origin}, "
                f"Authorization: {auth_header[:50] if len(auth_header) > 50 else auth_header}, "
                f"User: {request.user if hasattr(request, 'user') else 'Not set yet'}"
            )

        response = self.get_response(request)
        return response
