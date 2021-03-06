from __future__ import absolute_import, unicode_literals
from django import template

from pinax.apps.tribes.forms import TribeForm
from pinax.apps.tribes.models import Tribe

register = template.Library()


@register.inclusion_tag("tribes/tribe_item.html", takes_context=True)
def show_tribe(context, tribe):
    return {"tribe": tribe, "request": context["request"]}

# @@@ should move these next two as they aren't particularly tribe-specific


@register.simple_tag
def clear_search_url(request):
    getvars = request.GET.copy()
    if "search" in getvars:
        del getvars["search"]
    if len(list(getvars.keys())) > 0:
        return "{0}?{1}".format(request.path, getvars.urlencode())
    else:
        return request.path


@register.simple_tag
def persist_getvars(request):
    getvars = request.GET.copy()
    if len(list(getvars.keys())) > 0:
        return "?{0}".format(getvars.urlencode())
    return ""


@register.filter
def tribes_for_user(user):
    return Tribe.objects.filter(
        members__status='active',
        members__user=user
    ).order_by('name')
