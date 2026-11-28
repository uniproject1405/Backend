import re
import secrets
import urllib.parse

import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.authtoken.models import Token

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .models import GoogleProfile, Profile

User = get_user_model()

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKEN_EXCHANGE_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def _generate_unique_username(name, email):
    source = (name or "").strip()
    if not source:
        source = email.split("@")[0]

    slug = re.sub(r"[\s\-]+", "_", source)
    slug = re.sub(r"[^a-zA-Z0-9_]", "", slug).lower()

    if not slug:
        slug = "user"

    slug = slug[:140]

    username = slug
    counter = 1

    while User.objects.filter(username__iexact=username).exists():
        suffix = f"_{counter}"
        username = f"{slug[:150 - len(suffix)]}{suffix}"
        counter += 1

    return username


def _generate_random_unique_username():
    """
    Generates a temporary unique random username for Google OAuth.
    """

    while True:
        candidate = f"user_{secrets.token_hex(4)}"

        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate


def verify_id_token(token_string):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "") or None
    try:
        payload = google_id_token.verify_oauth2_token(
            token_string,
            google_requests.Request(),
            audience=client_id,
        )
        return payload
    except Exception:
        response = requests.get(
            GOOGLE_TOKENINFO_URL,
            params={"id_token": token_string},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if client_id and data.get("aud") != client_id:
                raise AuthenticationFailed("Invalid Google token audience.")
            return data
        raise AuthenticationFailed("Invalid or expired Google ID token.")


def verify_access_token(access_token):
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if response.status_code == 200:
        return response.json()
    raise AuthenticationFailed("Unable to verify Google access token.")


def exchange_auth_code(code, redirect_uri=None):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    effective_redirect = redirect_uri or getattr(settings, "GOOGLE_REDIRECT_URI", "")

    if not client_id or not client_secret:
        raise AuthenticationFailed("Google OAuth credentials are not properly configured.")

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": effective_redirect,
        "grant_type": "authorization_code",
    }

    response = requests.post(GOOGLE_TOKEN_EXCHANGE_URL, data=payload, timeout=10)
    if response.status_code != 200:
        raise AuthenticationFailed("Failed to exchange authorization code with Google.")

    tokens = response.json()
    if "id_token" in tokens:
        return verify_id_token(tokens["id_token"])
    if "access_token" in tokens:
        return verify_access_token(tokens["access_token"])

    raise AuthenticationFailed("Google OAuth response missing tokens.")


def get_or_create_google_user(profile_data):
    email = profile_data.get("email")
    if not email:
        raise ValidationError({"email": ["Google profile did not provide an email address."]})

    email_verified = profile_data.get("email_verified")
    if email_verified in (False, "false", "0"):
        raise ValidationError({"email": ["Google email is not verified."]})

    normalized_email = email.strip().lower()
    google_id = str(profile_data.get("sub") or profile_data.get("id") or "")
    picture = profile_data.get("picture") or ""
    name = (profile_data.get("name") or profile_data.get("given_name") or "").strip()

    user = User.objects.filter(email__iexact=normalized_email).first()
    is_new = False

    if user:
        if not user.is_active:
            raise AuthenticationFailed("User account is inactive.")
        if google_id:
            GoogleProfile.objects.update_or_create(
                user=user,
                defaults={"google_id": google_id, "picture": picture},
            )
    else:
# Generate temporary unique random username
        username = _generate_random_unique_username()
        user = User.objects.create_user(
            username=username,
            email=normalized_email,
        )
        user.set_unusable_password()
        user.save()
        is_new = True

        if google_id:
            GoogleProfile.objects.create(
                user=user,
                google_id=google_id,
                picture=picture,
                initial_username=username,
            )

        # Initialize profile with name from Google if available
        Profile.objects.get_or_create(
            user=user,
            defaults={"name": name},
        )
    token, _ = Token.objects.get_or_create(user=user)
    return user, token, is_new


def authenticate_google(id_token=None, access_token=None, code=None, redirect_uri=None):
    if id_token:
        profile = verify_id_token(id_token)
    elif access_token:
        profile = verify_access_token(access_token)
    elif code:
        profile = exchange_auth_code(code, redirect_uri=redirect_uri)
    else:
        raise ValidationError({"detail": ["Missing authentication credential."]})

    return get_or_create_google_user(profile)


def get_google_auth_url(state=None):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

def generate_password_reset_token(user):
    """
    Generate URL-safe base64 encoded user ID and secure one-time reset token.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def verify_password_reset_token(uidb64, token):
    """
    Validate UID and one-time reset token against active user account.
    Returns (user, True) if valid, or (None, False) if invalid or expired.
    """
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=user_id, is_active=True).first()
    except (TypeError, ValueError, OverflowError):
        return None, False

    if user and default_token_generator.check_token(user, token):
        return user, True
    return None, False


def send_password_reset_email(user, redirect_url=None):
    """
    Build secure reset link and send email notification to user.
    """
    uid, token = generate_password_reset_token(user)

    if redirect_url:
        base_url = redirect_url
    else:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        base_url = f"{frontend_url}/reset-password"

    delimiter = '&' if '?' in base_url else '?'
    reset_url = f"{base_url}{delimiter}uid={uid}&token={token}"

    subject = "بازیابی رمز عبور در ترایب | Password Reset Request"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Tribe Support <noreply@tribe.local>')

    message_text = (
        f"سلام {user.username} عزیز،\n\n"
        f"درخواستی برای بازیابی رمز عبور حساب کاربری شما در پلتفرم ترایب ثبت شده است.\n"
        f"برای تنظیم رمز عبور جدید، لطفاً روی پیوند زیر کلیک کنید:\n\n"
        f"{reset_url}\n\n"
        f"این پیوند به مدت ۲۴ ساعت معتبر است.\n"
        f"اگر شما چنین درخواستی ثبت نکرده‌اید، نیازی به انجام کاری نیست و رمز عبور شما بدون تغییر باقی می‌ماند.\n\n"
        f"با احترام،\n"
        f"تیم ترایب\n"
    )

    html_message = (
        f"<div style='font-family: Tahoma, Arial, sans-serif; line-height: 1.6; color: #222; direction: rtl;'>"
        f"<h2>بازیابی رمز عبور در ترایب</h2>"
        f"<p>سلام <strong>{user.username}</strong> عزیز،</p>"
        f"<p>درخواستی برای بازیابی رمز عبور حساب کاربری شما ثبت شده است. برای تعیین رمز جدید، روی دکمه زیر کلیک کنید:</p>"
        f"<p style='margin: 24px 0;'>"
        f"<a href='{reset_url}' style='background-color: #2563eb; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;'>تنظیم رمز عبور جدید</a>"
        f"</p>"
        f"<p style='font-size: 13px; color: #666;'>اگر دکمه بالا کار نمی‌کند، لینک زیر را در مرورگر خود باز کنید:</p>"
        f"<p style='font-size: 12px; color: #2563eb; direction: ltr; text-align: left;'><a href='{reset_url}'>{reset_url}</a></p>"
        f"<hr style='border: none; border-top: 1px solid #eee; margin: 24px 0;' />"
        f"<p style='font-size: 12px; color: #888;'>این لینک تا ۲۴ ساعت آینده معتبر است. در صورتی که این درخواست از جانب شما نبوده، این ایمیل را نادیده بگیرید.</p>"
        f"</div>"
    )

    send_mail(
        subject=subject,
        message=message_text,
        from_email=from_email,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )

    return reset_url


def reset_user_password(user, new_password):
    """
    Set new password for user and invalidate prior authentication tokens.
    """
    user.set_password(new_password)
    user.save()
    Token.objects.filter(user=user).delete()
    return user

