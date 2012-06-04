from django.contrib.auth.models import User
from django.core import urlresolvers
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from timezones.fields import TimeZoneField
from notification import models as notification


class Profile(models.Model):
    
    user = models.ForeignKey(User, unique=True, verbose_name=_("user"))
    name = models.CharField(_("name"), max_length=50, null=True, blank=True)
    about = models.TextField(_("about"), null=True, blank=True)
    location = models.CharField(_("location"),
        max_length = 40,
        null = True,
        blank = True
    )
    website = models.URLField(_("website"),
        null = True,
        blank = True
    )
    
    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")
    
    def __unicode__(self):
        return self.user.username
    
    def get_absolute_url(self):
        return urlresolvers.reverse("profile_detail", kwargs={
            "username": self.user.username
        })


def create_profile(sender, instance=None, **kwargs):
    if instance is None:
        return
    profile, created = Profile.objects.get_or_create(user=instance)

post_save.connect(create_profile, sender=User)


def should_deliver_callback(sender, **kwargs):
    """Prevents sending notification to inactive and deleted users"""
    user = kwargs.get("recipient")
    result = kwargs.get("result", {})
    if not user.is_active or user.username.startswith("__"):
        result['pass'] = False

notification.should_deliver.connect(should_deliver_callback, notification.Notice)
