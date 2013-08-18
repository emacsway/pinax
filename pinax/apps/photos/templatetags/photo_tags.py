from __future__ import absolute_import, unicode_literals
import re

from django import template
from django.utils.encoding import force_unicode

from pinax.apps.photos.models import Image, Pool

register = template.Library()


class PrintExifNode(template.Node):
    
    def __init__(self, exif):
        self.exif = exif
    
    def render(self, context):
        try:
            exif = force_unicode(self.exif.resolve(context, True))
        except template.VariableDoesNotExist:
            exif = ""
        
        EXPR = "'(?P<key>[^:]*)'\:(?P<value>[^,]*),"
        expr = re.compile(EXPR)
        msg = "<table>"
        for i in expr.findall(exif):
            msg += "<tr><td>{0}</td><td>{1}</td></tr>".format(i[0],i[1])
        
        msg += "</table>"
        
        return '<div id="exif">{0}</div>'.format(msg)


@register.tag(name="print_exif")
def do_print_exif(parser, token):
    try:
        tag_name, exif = token.contents.split()
    except ValueError:
        msg = "{0} tag requires a single argument".format(token.contents[0])
        raise template.TemplateSyntaxError(msg)
    
    exif = parser.compile_filter(exif)
    return PrintExifNode(exif)


class PublicPhotosNode(template.Node):
    
    def __init__(self, context_var, user_var=None, use_pool=False):
        self.context_var = context_var
        if user_var is not None:
            self.user_var = template.Variable(user_var)
        else:
            self.user_var = None
        self.use_pool = use_pool
    
    def render(self, context):
        
        use_pool = self.use_pool
        
        if use_pool:
            queryset = Pool.objects.filter(
                photo__is_public = True,
            ).select_related("photo")
        else:
            queryset = Image.objects.filter(is_public=True)
        
        if self.user_var is not None:
            user = self.user_var.resolve(context)
            if use_pool:
                queryset = queryset.filter(photo__member=user)
            else:
                queryset = queryset.filter(member=user)
        
        context[self.context_var] = queryset
        return ""


@register.tag
def public_photos(parser, token, use_pool=False):
    
    bits = token.split_contents()
    
    if len(bits) != 3 and len(bits) != 5:
        message = "'{0}' tag requires three or five arguments".format(bits[0])
        raise template.TemplateSyntaxError(message)
    else:
        if len(bits) == 3:
            if bits[1] != "as":
                message = "'{0}' second argument must be 'as'".format(bits[0])
                raise template.TemplateSyntaxError(message)
            
            return PublicPhotosNode(bits[2], use_pool=use_pool)
            
        elif len(bits) == 5:
            if bits[1] != "for":
                message = "'{0}' second argument must be 'for'".format(bits[0])
                raise template.TemplateSyntaxError(message)
            if bits[3] != "as":
                message = "'{0}' forth argument must be 'as'".format(bits[0])
                raise template.TemplateSyntaxError(message)
            2
            return PublicPhotosNode(bits[4], bits[2], use_pool=use_pool)


@register.tag
def public_pool_photos(parser, token):
    return public_photos(parser, token, use_pool=True)
