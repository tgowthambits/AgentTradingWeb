from django import template

register = template.Library()


@register.filter
def pnl_color(value):
    try:
        v = float(value)
        return "text-success" if v >= 0 else "text-error"
    except (ValueError, TypeError):
        return ""


@register.filter
def format_inr(value):
    try:
        v = float(value)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:,.2f}"
    except (ValueError, TypeError):
        return str(value)
