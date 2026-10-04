import time
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class SecurityAndRateLimitMiddleware(MiddlewareMixin):
    """
    Lightweight, high-performance security & rate-limiting middleware.
    Protects against:
      - Denial of Service (DoS) & server overload
      - Brute-force login / signup spam
      - Cart & checkout order flood
      - Missing security headers
    """

    # Requests allowed per 60-second window
    GENERAL_LIMIT = 120
    SENSITIVE_LIMIT = 25

    SENSITIVE_PATHS = [
        '/signin/',
        '/signup/',
        '/direct_order/',
        '/checkout/',
        '/add_to_cart/',
        '/apply_coupon/',
    ]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def process_request(self, request):
        # Exclude static files from rate limiting
        path = request.path
        if path.startswith('/static/') or path.startswith('/favicon.ico'):
            return None

        ip = self.get_client_ip(request)
        now = int(time.time())
        window = now // 60  # 1-minute window bucket

        # Check if sensitive endpoint
        is_sensitive = any(path.startswith(p) for p in self.SENSITIVE_PATHS)
        limit = self.SENSITIVE_LIMIT if is_sensitive else self.GENERAL_LIMIT
        prefix = 'rl_sens' if is_sensitive else 'rl_gen'
        cache_key = f"{prefix}:{ip}:{window}"

        try:
            # Increment request counter for current window
            current_count = cache.get(cache_key, 0)
            if current_count >= limit:
                response = HttpResponse(
                    '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 60px 20px;">'
                    '<h1 style="color: #fc8019; font-size: 2.5rem; margin-bottom: 10px;">⚡ Server Protection Active</h1>'
                    '<h3 style="color: #282c3f; margin-bottom: 12px;">Too Many Requests</h3>'
                    '<p style="color: #686b78; max-width: 480px; margin: 0 auto 20px; line-height: 1.5;">'
                    'To prevent server overload and ensure smooth delivery service for everyone, '
                    'your requests have been temporarily paused. Please wait a few seconds and refresh.'
                    '</p>'
                    '<a href="/" style="display: inline-block; background: #fc8019; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">Return to Home</a>'
                    '</div>',
                    status=429,
                    content_type='text/html'
                )
                response['Retry-After'] = '30'
                return response

            # Update cache with 70s TTL
            cache.set(cache_key, current_count + 1, timeout=70)
        except Exception:
            # Never crash requests if cache backend is unavailable
            pass

        return None

    def process_response(self, request, response):
        # Enforce essential security headers to prevent XSS, clickjacking and sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
