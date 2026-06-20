import re

from django import template

register = template.Library()


@register.filter
def format_phone(value):
    """Format a 10-digit US phone number as (XXX) XXX-XXXX; leave anything else as-is."""
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 10:
        return f'({digits[0:3]}) {digits[3:6]}-{digits[6:10]}'
    if len(digits) == 11 and digits[0] == '1':
        return f'({digits[1:4]}) {digits[4:7]}-{digits[7:11]}'
    return value
