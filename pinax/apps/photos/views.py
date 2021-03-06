from __future__ import absolute_import, unicode_literals
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from pinax.apps.photos.models import Image, Pool
from pinax.apps.photos.forms import PhotoUploadForm, PhotoEditForm

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

try:
    from friends.models import Friendship
except ImportError:
    Friendship = None


def group_and_bridge(request):
    """
    Given the request we can depend on the GroupMiddleware to provide the
    group and bridge.
    """

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
    else:
        bridge = None

    return group, bridge


def group_context(group, bridge):
    # @@@ use bridge
    ctx = {
        "group": group,
    }
    if group:
        ctx["group_base"] = bridge.group_base_template()
    return ctx


@login_required
def upload(request, form_class=PhotoUploadForm, template_name="photos/upload.html"):
    """
    upload form for photos
    """

    group, bridge = group_and_bridge(request)

    photo_form = form_class()
    if request.method == "POST":
        if request.POST.get("action") == "upload":
            photo_form = form_class(request.user, request.POST, request.FILES)
            if photo_form.is_valid():
                photo = photo_form.save(commit=False)
                photo.member = request.user
                photo.save()

                # in group context we create a Pool object for it
                if group:
                    pool = Pool()
                    pool.photo = photo
                    group.associate(pool, gfk_field="content_object")
                    pool.save()

                messages.add_message(
                    request, messages.SUCCESS,
                    ugettext("Successfully uploaded photo '%s'") % photo.title
                )

                if notification:
                    # Fixed TypeError: can't pickle function objects
                    # photo = Image.objects.get(pk=photo.pk)
                    if group:
                        notify_list = group.member_queryset().exclude(id__exact=photo.member.id)
                    else:
                        notify_list = [x['friend'] for x in Friendship.objects.friends_for_user(photo.member)]

                    notification.send(notify_list, "photos_image_new", {
                        "creator": photo.member,
                        "image": photo,
                        "group": photo.group,
                        "context_object": photo,
                    })

                include_kwargs = {"id": photo.id}
                if group:
                    redirect_to = bridge.reverse("photo_details", group, kwargs=include_kwargs)
                else:
                    redirect_to = reverse("photo_details", kwargs=include_kwargs)

                return HttpResponseRedirect(redirect_to)

    ctx = group_context(group, bridge)
    ctx.update({
        "photo_form": photo_form,
    })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
def yourphotos(request, template_name="photos/yourphotos.html"):
    """
    photos for the currently authenticated user
    """

    group, bridge = group_and_bridge(request)

    photos = Image.objects.filter(member=request.user)

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photos = photos.order_by("-date_added")

    ctx = group_context(group, bridge)
    ctx.update({
        "photos": photos,
    })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
def photos(request, template_name="photos/latest.html"):
    """
    latest photos
    """

    group, bridge = group_and_bridge(request)

    photos = Image.objects.filter(
        Q(is_public=True) |
        Q(is_public=False, member=request.user)
    )

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photos = photos.order_by("-date_added")

    ctx = group_context(group, bridge)
    ctx.update({
        "photos": photos,
    })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
def details(request, id, template_name="photos/details.html"):
    """
    show the photo details
    """

    group, bridge = group_and_bridge(request)

    photos = Image.objects.all()

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photo = get_object_or_404(photos, id=id)

    # @@@: test
    if not photo.is_public and request.user != photo.member:
        raise Http404

    title = photo.title
    host = "http://{0}".format(request.get_host())

    if photo.member == request.user:
        is_me = True
    else:
        is_me = False

    ctx = group_context(group, bridge)
    ctx.update({
        "host": host,
        "photo": photo,
        "is_me": is_me,
    })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
def memberphotos(request, username, template_name="photos/memberphotos.html"):
    """
    Get the members photos and display them
    """

    group, bridge = group_and_bridge(request)

    user = get_object_or_404(User, username=username)

    photos = Image.objects.filter(
        member__username=username,
        is_public=True,
    )

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photos = photos.order_by("-date_added")

    ctx = group_context(group, bridge)
    ctx.update({
        "photos": photos,
        "member": user,
    })
    ctx = RequestContext(request, ctx)
    return render_to_response(template_name, ctx)


@login_required
def edit(request, id, form_class=PhotoEditForm, template_name="photos/edit.html"):

    group, bridge = group_and_bridge(request)

    photos = Image.objects.all()

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photo = get_object_or_404(photos, id=id)

    if request.method == "POST":
        if photo.member != request.user:
            messages.add_message(
                request, messages.ERROR,
                ugettext("You can't edit photos that aren't yours")
            )
            include_kwargs = {"id": photo.id}
            if group:
                redirect_to = bridge.reverse("photo_details", group, kwargs=include_kwargs)
            else:
                redirect_to = reverse("photo_details", kwargs=include_kwargs)

            return HttpResponseRedirect(reverse('photo_details', args=(photo.id,)))
        if request.POST["action"] == "update":
            photo_form = form_class(request.user, request.POST, instance=photo)
            if photo_form.is_valid():
                photoobj = photo_form.save(commit=False)
                photoobj.save()

                messages.add_message(
                    request, messages.SUCCESS,
                    ugettext("Successfully updated photo '%s'") % photo.title
                )

                include_kwargs = {"id": photo.id}
                if group:
                    redirect_to = bridge.reverse("photo_details", group, kwargs=include_kwargs)
                else:
                    redirect_to = reverse("photo_details", kwargs=include_kwargs)

                return HttpResponseRedirect(redirect_to)
        else:
            photo_form = form_class(instance=photo)

    else:
        photo_form = form_class(instance=photo)

    ctx = group_context(group, bridge)
    ctx.update({
        "photo_form": photo_form,
        "photo": photo,
    })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
def destroy(request, id):

    group, bridge = group_and_bridge(request)

    photos = Image.objects.all()

    if group:
        photos = group.content_objects(photos, join="pool", gfk_field="content_object")
    else:
        photos = photos.filter(pool__object_id=None)

    photo = get_object_or_404(photos, id=id)
    title = photo.title

    if group:
        redirect_to = bridge.reverse("photos_yours", group)
    else:
        redirect_to = reverse("photos_yours")

    if photo.member != request.user:
        messages.add_message(
            request, messages.ERROR,
            ugettext("You can't edit photos that aren't yours")
        )
        return HttpResponseRedirect(redirect_to)

    if request.method == "POST" and request.POST["action"] == "delete":
        photo.delete()
        messages.add_message(
            request, messages.SUCCESS,
            ugettext("Successfully deleted photo '%s'") % title
        )

    return HttpResponseRedirect(redirect_to)
