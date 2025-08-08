import re
from typing import Optional
from pydantic import validator
from email_validator import validate_email, EmailNotValidError

def validate_email_format(email: str) -> str:
    """Validate email format"""
    try:
        valid_email = validate_email(email)
        return valid_email.email
    except EmailNotValidError:
        raise ValueError("Invalid email format")

def validate_password_strength(password: str) -> str:
    """Validate password strength"""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character")
    
    return password

def validate_currency_code(currency: str) -> str:
    """Validate currency code"""
    valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR"]
    if currency not in valid_currencies:
        raise ValueError(f"Invalid currency code. Must be one of: {', '.join(valid_currencies)}")
    return currency

def validate_timezone(timezone: str) -> str:
    """Validate timezone"""
    import pytz
    try:
        pytz.timezone(timezone)
        return timezone
    except pytz.exceptions.UnknownTimeZoneError:
        raise ValueError("Invalid timezone")

def validate_phone_number(phone: str) -> str:
    """Validate phone number format"""
    # Basic phone number validation: optional '+' and '1', then 9–15 digits
    phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
    cleaned = phone.replace(' ', '').replace('-', '')
    if not phone_pattern.match(cleaned):
        raise ValueError("Invalid phone number format")
    return phone