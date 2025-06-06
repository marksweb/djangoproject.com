import stripe
from django import forms
from django.db import transaction
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3

from .models import INTERVAL_CHOICES, LEADERSHIP_LEVEL_AMOUNT, DjangoHero, Donation


class DjangoHeroForm(forms.ModelForm):
    hero_type = forms.ChoiceField(
        required=False,
        widget=forms.RadioSelect,
        label=_("I am donating as an"),
        choices=DjangoHero.HERO_TYPE_CHOICES,
        initial=DjangoHero.HERO_TYPE_CHOICES[0][0],
    )
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "required",
                "placeholder": _("Your name or the name of your organization"),
            },
        ),
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": (
                    _("Where are you located? (optional; will not be displayed)")
                ),
            },
        ),
    )
    url = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Which URL should we link your name to?"),
            },
        ),
    )
    logo = forms.FileField(
        required=False,
        help_text=_(
            "If you've donated at least US $%d, you can submit your logo and "
            "we will display it, too."
        )
        % LEADERSHIP_LEVEL_AMOUNT,
    )
    is_visible = forms.BooleanField(
        required=False,
        label=_(
            "Yes, display my name, URL, and logo on this site. "
            "It'll be displayed shortly after we verify it."
        ),
    )
    is_subscribed = forms.BooleanField(
        required=False,
        label=_(
            "Yes, the Django Software Foundation can inform me about "
            "future fundraising campaigns by email."
        ),
    )

    class Meta:
        model = DjangoHero
        fields = (
            "hero_type",
            "name",
            "location",
            "url",
            "logo",
            "is_visible",
            "is_subscribed",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkbox_fields = []
        self.radio_select_fields = []

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                self.checkbox_fields.append(name)
            elif isinstance(field.widget, forms.RadioSelect):
                self.radio_select_fields.append(name)

    def save(self, commit=True):
        hero = super().save(commit=commit)
        customer = stripe.Customer.retrieve(hero.stripe_customer_id)
        customer.description = hero.name or None
        customer.email = hero.email or None
        customer.save()
        return hero


class StripeTextInput(forms.TextInput):
    """
    Inspired by widgets in django-zebra
    """

    def _add_data_stripe_attr(self, name, kwargs):
        kwargs.setdefault("attrs", {}).update({"data-stripe": name})
        return kwargs

    def _strip_name_attr(self, widget_string, name):
        return widget_string.replace(f'name="{name}"', "")

    def render(self, name, *args, **kwargs):
        kwargs = self._add_data_stripe_attr(name, kwargs)
        rendered = super().render(name, *args, **kwargs)
        return mark_safe(self._strip_name_attr(rendered, name))


class DonateForm(forms.Form):
    """
    Used to generate the HTML form in the fundraising page.
    """

    AMOUNT_CHOICES = (
        (25, _("US $25")),
        (50, _("US $50")),
        (100, _("US $100")),
        (250, _("US $250")),
        (500, _("US $500")),
        (750, _("US $750")),
        (1000, _("US $1,000")),
        (1250, _("US $1,250")),
        (2500, _("US $2,500")),
        ("custom", _("Other amount")),
    )

    amount = forms.ChoiceField(choices=AMOUNT_CHOICES)
    interval = forms.ChoiceField(choices=INTERVAL_CHOICES)
    captcha = ReCaptchaField(widget=ReCaptchaV3(action="form"))


class DonationForm(forms.ModelForm):
    """
    Used in the manage donations view.
    """

    subscription_amount = forms.DecimalField(
        max_digits=9, decimal_places=2, required=True
    )
    # here we're removing "onetime" option from interval choices:
    interval = forms.ChoiceField(choices=INTERVAL_CHOICES[:3], required=True)

    class Meta:
        model = Donation
        fields = ("subscription_amount", "interval")

    @transaction.atomic()
    def save(self, commit=True, *args, **kwargs):
        donation = super().save(commit=commit)

        # Send data to Stripe
        subscription = stripe.Subscription.retrieve(donation.stripe_subscription_id)
        # TODO: Setting the plan is deprecated — use Price API instead.
        subscription.plan = self.cleaned_data["interval"]
        subscription.quantity = int(self.cleaned_data["subscription_amount"])

        subscription.save()

        return donation


class PaymentForm(forms.Form):
    """
    Used to validate values when configuring the Stripe Session.

    `amount` can be any integer, so a ChoiceField is not appropriate.
    """

    # NOTE: `action` needs to match the one used in stripe-donation.js
    captcha = ReCaptchaField(widget=ReCaptchaV3(action="form"))
    amount = forms.IntegerField(
        required=True,
        min_value=1,  # Minimum payment from Stripe API
        max_value=999_999,  # Reject clearly unrealistic amounts.
    )
    interval = forms.ChoiceField(
        required=True,
        choices=INTERVAL_CHOICES,
    )
