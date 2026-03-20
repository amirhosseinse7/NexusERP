from apps.core.models import _thread_locals

class TenantMiddleware:
    """
    Enterprise SaaS Middleware.
    Extracts the Company from the logged-in User's Profile and 
    stores it in the thread-local storage so TenantAwareModel can 
    automatically filter all database queries.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        _thread_locals.company = None
        

        if request.user.is_authenticated:
            try:

                _thread_locals.company = request.user.profile.company
            except AttributeError:

                pass

        response = self.get_response(request)


        _thread_locals.company = None
        
        return response