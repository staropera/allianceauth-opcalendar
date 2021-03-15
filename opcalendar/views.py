# cal/views.py
import calendar
from datetime import datetime, date, timedelta

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from django.contrib import messages
from django.urls import reverse

from django.views.generic import ListView
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.db.models import Q

from esi.decorators import token_required
from opcalendar.models import (
    Event,
    EventCategory,
    EventVisibility,
    EventMember,
    IngameEvents,
    Owner,
)

from . import tasks
from .utils import Calendar, messages_plus
from .forms import EventForm, AddMemberForm

logger = get_extension_logger(__name__)


@login_required(login_url="signup")
def index(request):
    return HttpResponse("hello")


@token_required(scopes=["esi-calendar.read_calendar_events.v1"])
def add_ingame_calendar(request, token):
    token_char = EveCharacter.objects.get(character_id=token.character_id)

    success = True
    try:
        owned_char = CharacterOwnership.objects.get(
            user=request.user, character=token_char
        )
    except CharacterOwnership.DoesNotExist:

        success = False
        owned_char = None

        messages_plus.error(
            request,
            format_html(
                gettext_lazy(
                    "You can only use your main or alt characters "
                    "to add corporations. "
                    "However, character %s is neither. "
                )
                % format_html("<strong>{}</strong>", token_char.character_name)
            ),
        )

    if success:

        try:
            corporation = EveCorporationInfo.objects.get(
                corporation_id=token_char.corporation_id
            )
        except EveCorporationInfo.DoesNotExist:
            corporation = EveCorporationInfo.objects.create_corporation(
                token_char.corporation_id
            )

        with transaction.atomic():
            owner, _ = Owner.objects.update_or_create(
                corporation=corporation, defaults={"character": owned_char}
            )

            owner.save()

        tasks.update_events_for_owner(owner_pk=owner.pk)

        messages_plus.success(
            request,
            format_html(
                gettext_lazy(
                    "Succesfully added ingame calendar sync for %(character)s. Process will run on background. You will receive a report once the process is finished."
                )
                % {
                    "corporation": format_html("<strong>{}</strong>", owner),
                    "character": format_html(
                        "<strong>{}</strong>", owner.character.character.character_name
                    ),
                }
            ),
        )

    return redirect("opcalendar:calendar")


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split("-"))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = "month=" + str(prev_month.year) + "-" + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = "month=" + str(next_month.year) + "-" + str(next_month.month)
    return month


class CalendarView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "opcalendar.basic_access"
    login_url = "signup"
    model = Event
    template_name = "opcalendar/calendar.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        # user_permissions = self.request.user.has_perm('app.get_main_view')
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get("month", None))
        cal = Calendar(d.year, d.month, user)
        html_cal = cal.formatmonth(withyear=True)
        context["category"] = EventCategory.objects.all()
        context["visibility"] = EventVisibility.objects.all()
        context["calendar"] = mark_safe(html_cal)
        context["prev_month"] = prev_month(d)
        context["next_month"] = next_month(d)
        return context


@login_required(login_url="signup")
@permission_required("opcalendar.create_event")
def create_event(request):
    form = EventForm(request.POST or None)
    if request.POST and form.is_valid():
        # Get character
        character = request.user.profile.main_character
        operation_type = form.cleaned_data["operation_type"]
        title = form.cleaned_data["title"]
        host = form.cleaned_data["host"]
        doctrine = form.cleaned_data["doctrine"]
        formup_system = form.cleaned_data["formup_system"]
        description = form.cleaned_data["description"]
        start_time = form.cleaned_data["start_time"]
        end_time = form.cleaned_data["end_time"]
        fc = form.cleaned_data["fc"]
        event_visibility = form.cleaned_data["event_visibility"]
        Event.objects.get_or_create(
            user=request.user,
            operation_type=operation_type,
            title=title,
            host=host,
            doctrine=doctrine,
            formup_system=formup_system,
            description=description,
            start_time=start_time,
            end_time=end_time,
            eve_character=character,
            fc=fc,
            event_visibility=event_visibility,
        )
        messages.success(
            request,
            _("Event %(opname)s created for %(date)s.")
            % {"opname": title, "date": start_time.strftime("%Y-%m-%d %H:%M")},
        )

        return HttpResponseRedirect(reverse("opcalendar:calendar"))

    return render(request, "opcalendar/event-add.html", {"form": form})


@login_required(login_url="signup")
@permission_required("opcalendar.basic_access")
def event_details(request, event_id):

    try:
        event = (
            Event.objects.filter(
                Q(event_visibility__restricted_to_group__in=request.user.groups.all())
                | Q(event_visibility__restricted_to_group__isnull=True),
            )
            .filter(
                Q(event_visibility__restricted_to_state=request.user.profile.state)
                | Q(event_visibility__restricted_to_state__isnull=True),
            )
            .get(id=event_id)
        )

        context = {"event": event}

        return render(request, "opcalendar/event-details.html", context)

    except Event.DoesNotExist:
        return redirect("opcalendar:calendar")


@permission_required("opcalendar.create_event")
def EventEdit(request, event_id):
    logger.debug(
        "edit_event called by user %s for optimer id %s" % (request.user, event_id)
    )
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        form = EventForm(request.POST)
        logger.debug(
            "Received POST request containing update optimer form, is valid: %s"
            % form.is_valid()
        )
        if form.is_valid():

            event.operation_type = form.cleaned_data["operation_type"]
            event.title = form.cleaned_data["title"]
            event.host = form.cleaned_data["host"]
            event.doctrine = form.cleaned_data["doctrine"]
            event.formup_system = form.cleaned_data["formup_system"]
            event.description = form.cleaned_data["description"]
            event.start_time = form.cleaned_data["start_time"]
            event.end_time = form.cleaned_data["end_time"]
            event.fc = form.cleaned_data["fc"]
            event.event_visibility = form.cleaned_data["event_visibility"]

            logger.info("User %s updating optimer id %s " % (request.user, event_id))
            event.save()
            messages.success(
                request,
                _("Saved changes to event for %(event)s.") % {"event": event.title},
            )
            return redirect("opcalendar:calendar")
    else:
        data = {
            "operation_type": event.operation_type,
            "title": event.title,
            "host": event.host,
            "doctrine": event.doctrine,
            "formup_system": event.formup_system,
            "description": event.description,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "fc": event.fc,
            "event_visibility": event.event_visibility,
        }
        form = EventForm(initial=data)
    return render(request, "opcalendar/event-edit.html", context={"form": form})


@login_required(login_url="signup")
@permission_required("opcalendar.basic_access")
def ingame_event_details(request, event_id):
    event = IngameEvents.objects.get(event_id=event_id)

    context = {"event": event}

    if request.user.has_perm("opcalendar.view_ingame"):
        return render(request, "opcalendar/ingame-event-details.html", context)
    else:
        return redirect("opcalendar:calendar")


@login_required(login_url="signup")
@permission_required("opcalendar.manage_event")
def add_eventmember(request, event_id):
    forms = AddMemberForm()
    if request.method == "POST":
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)
            if member.count() <= 9:
                user = forms.cleaned_data["user"]
                EventMember.objects.create(event=event, user=user)
                return redirect("opcalendar:calendar")
            else:
                print("--------------User limit exceed!-----------------")
    context = {"form": forms}
    return render(request, "opcalendar/add_member.html", context)


@login_required
@permission_required("opcalendar.create_event")
def EventDeleteView(request, event_id):
    logger.debug(
        "remove_optimer called by user %s for operation id %s"
        % (request.user, event_id)
    )
    op = get_object_or_404(Event, id=event_id)
    op.delete()
    logger.info("Deleting optimer id %s by user %s" % (event_id, request.user))
    messages.error(request, _("Removed event %(opname)s.") % {"opname": op.title})
    return redirect("opcalendar:calendar")
