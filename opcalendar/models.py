import requests
import json

from typing import Tuple
from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Group

from esi.errors import TokenExpiredError, TokenInvalidError
from esi.models import Token

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import State

from .providers import esi
from .decorators import fetch_token_for_owner

logger = get_extension_logger(__name__)


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access this app"),
            ("view_public", "Can see public events"),
            ("view_member", "Can see member events"),
            ("view_ingame", "Can see events from ingame calendar"),
            ("create_event", "Can create and edit events"),
            ("manage_event", "Can delete and manage signups"),
            (
                "add_ingame_calendar_owner",
                "Can add ingame calendar feeds for their corporation",
            ),
        )


class WebHook(models.Model):
    """Discord Webhook for pings"""

    name = models.CharField(
        max_length=150,
        help_text=_("Name for this webhook"),
    )
    webhook_url = models.CharField(
        max_length=500,
        help_text=_("Webhook URL"),
    )
    enabled = models.BooleanField(default=True, help_text=_("Is the webhook enabled?"))

    def send_embed(self, embed):
        custom_headers = {"Content-Type": "application/json"}
        data = '{"embeds": [%s]}' % json.dumps(embed)
        r = requests.post(self.webhook_url, headers=custom_headers, data=data)
        r.raise_for_status()

    class Meta:
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"

    def __str__(self):
        return "{}".format(self.name)


class EventVisibility(models.Model):
    name = models.CharField(
        max_length=150, null=False, help_text="Name for the visibility filter"
    )
    restricted_to_group = models.ManyToManyField(
        Group,
        blank=True,
        related_name="eventvisibility_require_groups",
        help_text=_(
            "The group(s) that will be able to see this event visibility type ..."
        ),
    )
    restricted_to_state = models.ManyToManyField(
        State,
        blank=True,
        related_name="eventvisibility_require_states",
        help_text=_(
            "The state(s) that will be able to see this event visibility type ..."
        ),
    )
    webhook = models.ForeignKey(
        WebHook,
        on_delete=models.CASCADE,
        null=True,
        help_text=_("Webhook to send over notifications about these fleet types"),
    )
    ignore_past_fleets = models.BooleanField(
        default=True,
        help_text=_("Should we ignore fleet signals that are in the past"),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=("Whether this visibility filter is active"),
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Event Visibility"
        verbose_name_plural = "Event Visibilities"


class EventHost(models.Model):
    """Fleet Timer Create/Delete pings"""

    community = models.CharField(
        max_length=150, null=False, help_text="Name of the community"
    )
    logo_url = models.CharField(
        max_length=256, blank=True, help_text="Absolute URL for the community logo"
    )
    ingame_channel = models.CharField(
        max_length=150, blank=True, help_text="Ingame channel name"
    )
    ingame_mailing_list = models.CharField(
        max_length=150, blank=True, help_text="Ingame mailing list name"
    )
    fleet_comms = models.CharField(
        max_length=150,
        blank=True,
        help_text="Link or description for primary comms such as discord link",
    )
    fleet_doctrines = models.CharField(
        max_length=150, blank=True, help_text="Link or description to the doctrines"
    )
    website = models.CharField(max_length=150, blank=True)
    discord = models.CharField(max_length=150, blank=True, help_text="Discord link URL")
    twitch = models.CharField(max_length=150, blank=True, help_text="Twitch link URL")
    twitter = models.CharField(max_length=150, blank=True, help_text="Twitter link URL")
    youtube = models.CharField(max_length=150, blank=True, help_text="Youtube link URL")
    facebook = models.CharField(
        max_length=150, blank=True, help_text="Facebook link URL"
    )
    details = models.CharField(
        max_length=150, blank=True, help_text="Short description about the host."
    )
    external = models.BooleanField(
        default=False,
        help_text=_(
            "External hosts are for NPSI API imports. Checking this box will hide the host in the manual event form."
        ),
    )

    def __str__(self):
        return str(self.community)

    class Meta:
        verbose_name = "Host"
        verbose_name_plural = "Hosts"


class EventCategory(models.Model):
    # Colors for calendar
    COLOR_BLUE = "blue"
    COLOR_GREEN = "green"
    COLOR_RED = "red"
    COLOR_ORANGE = "orange"
    COLOR_GREY = "grey"
    COLOR_YELLOW = "yellow"
    COLOR_PURPLE = "purple"

    COLOR_CHOICES = (
        (COLOR_GREEN, _("Green")),
        (COLOR_RED, _("Red")),
        (COLOR_ORANGE, _("Orange")),
        (COLOR_BLUE, _("Blue")),
        (COLOR_GREY, _("Grey")),
        (COLOR_YELLOW, _("Yellow")),
        (COLOR_PURPLE, _("Purple")),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Name for the category"),
    )
    ticker = models.CharField(
        max_length=10,
        help_text=_("Ticker for the category"),
    )
    color = models.CharField(max_length=6, choices=COLOR_CHOICES, default="green")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return str(self.name)


class EventImport(models.Model):
    """NPSI IMPORT OPTIONS"""

    SPECTRE_FLEET = "Spectre Fleet"
    EVE_UNIVERSITY = "EVE University"
    FUN_INC = "Fun Inc."

    IMPORT_SOURCES = [
        (SPECTRE_FLEET, _("Spectre Fleet")),
        (EVE_UNIVERSITY, _("EVE University")),
        (FUN_INC, _("Fun Inc.")),
    ]

    source = models.CharField(
        max_length=32,
        choices=IMPORT_SOURCES,
        help_text="The API source where you want to pull events from",
    )

    host = models.ForeignKey(
        EventHost,
        on_delete=models.CASCADE,
        default=1,
        help_text="The AA host that will be used for the pulled events",
    )
    operation_type = models.ForeignKey(
        EventCategory,
        on_delete=models.CASCADE,
        help_text="Operation type and ticker that will be assigned for the pulled fleets",
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default="1",
        help_text="User that has been used to create the fleet (most often the superuser who manages the plugin)",
    )
    eve_character = models.ForeignKey(
        EveCharacter,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Event creator main character",
    )

    def __str__(self):
        return str(self.source)

    class Meta:
        verbose_name = "NPSI Event Import"
        verbose_name_plural = "NPSI Event Imports"


class Event(models.Model):
    operation_type = models.ForeignKey(
        EventCategory,
        on_delete=models.CASCADE,
        help_text=_("Event category type"),
    )
    title = models.CharField(
        max_length=200,
        unique=False,
        help_text=_("Title for the event"),
    )
    host = models.ForeignKey(
        EventHost,
        on_delete=models.CASCADE,
        default=1,
        help_text=_("Host entity for the event"),
    )
    doctrine = models.CharField(
        max_length=254,
        default="",
        blank=True,
        help_text=_("Doctrine URL or name"),
    )
    formup_system = models.CharField(
        max_length=254,
        default="",
        blank=True,
        help_text=_("Location for formup"),
    )
    description = models.TextField(
        null=True,
        help_text=_("Description text for the operation"),
    )
    start_time = models.DateTimeField(
        help_text=_("Event start date and time"),
    )
    end_time = models.DateTimeField(
        help_text=_("Event end date and time"),
    )
    fc = models.CharField(
        max_length=254,
        default="",
        help_text=_("Fleet commander/manager for the event"),
    )
    event_visibility = models.ForeignKey(
        EventVisibility,
        on_delete=models.CASCADE,
        null=True,
        help_text=_("Visibility filter that dictates who is able to see this event"),
    )
    external = models.BooleanField(
        default=False,
        null=False,
        help_text=_("Is the event an external event over API"),
    )
    created_date = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the event was created"),
    )
    eve_character = models.ForeignKey(
        EveCharacter,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Character used to create the event"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User who created the event"),
    )

    class Meta:
        unique_together = ["title", "start_time"]

    def duration(self):
        return self.end_time - self.start_time

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("opcalendar:event-detail", args=(self.id,))

    @property
    def get_html_url(self):
        url = reverse("opcalendar:event-detail", args=(self.id,))
        return f"{url}"

    @property
    def get_html_title(self):
        return f'{self.start_time.strftime("%H:%M")} - {self.end_time.strftime("%H:%M")} <i>{self.host.community}</i> <br> <b>{self.operation_type.ticker} {self.title}</b>'

    @property
    def get_html_operation_color(self):
        return f"{self.operation_type.color}"

    def user_can_edit(self, user: user) -> bool:
        """Checks if the given user can edit this timer. Returns True or False"""
        return user.has_perm("opcalendar.manage_event") or (
            self.user == user and user.has_perm("opcalendar.create_event")
        )


class Owner(models.Model):
    """A corporation that holds the calendars"""

    ERROR_NONE = 0
    ERROR_TOKEN_INVALID = 1
    ERROR_TOKEN_EXPIRED = 2
    ERROR_INSUFFICIENT_PERMISSIONS = 3
    ERROR_NO_CHARACTER = 4
    ERROR_ESI_UNAVAILABLE = 5
    ERROR_OPERATION_MODE_MISMATCH = 6
    ERROR_UNKNOWN = 99

    ERRORS_LIST = [
        (ERROR_NONE, "No error"),
        (ERROR_TOKEN_INVALID, "Invalid token"),
        (ERROR_TOKEN_EXPIRED, "Expired token"),
        (ERROR_INSUFFICIENT_PERMISSIONS, "Insufficient permissions"),
        (ERROR_NO_CHARACTER, "No character set for fetching data from ESI"),
        (ERROR_ESI_UNAVAILABLE, "ESI API is currently unavailable"),
        (
            ERROR_OPERATION_MODE_MISMATCH,
            "Operaton mode does not match with current setting",
        ),
        (ERROR_UNKNOWN, "Unknown error"),
    ]

    corporation = models.OneToOneField(
        EveCorporationInfo,
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Corporation owning the calendar",
        related_name="+",
    )
    character = models.ForeignKey(
        CharacterOwnership,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text="Character used for syncing the calendar",
        related_name="+",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=("whether this owner is currently included in the sync process"),
    )

    class Meta:
        verbose_name = "Ingame Clanedar Owner"
        verbose_name_plural = "Ingame Calendar Owners"

    @fetch_token_for_owner(["esi-calendar.read_calendar_events.v1"])
    def update_events_esi(self, token):
        if self.is_active:

            # Get all current imported fleets in database
            event_ids_to_remove = list(
                IngameEvents.objects.filter(owner=self).values_list(
                    "event_id", flat=True
                )
            )
            logger.debug(
                "Ingame events currently in database: %s" % event_ids_to_remove
            )

            events = self._fetch_events()
            for event in events:

                character_id = self.character.character.character_id

                details = (
                    esi.client.Calendar.get_characters_character_id_calendar_event_id(
                        character_id=character_id,
                        event_id=event["event_id"],
                        token=token.valid_access_token(),
                    ).results()
                )

                end_date = event["event_date"] + timedelta(minutes=details["duration"])

                original = IngameEvents.objects.filter(
                    owner=self, event_id=event["event_id"]
                ).first()

                if original is not None:

                    logger.debug("Event: %s already in database" % event["title"])
                    event_ids_to_remove.remove(original.event_id)

                else:
                    IngameEvents.objects.create(
                        event_id=event["event_id"],
                        owner=self,
                        text=details["text"],
                        owner_type=details["owner_type"],
                        owner_name=details["owner_name"],
                        importance=details["importance"],
                        duration=details["duration"],
                        event_start_date=event["event_date"],
                        event_end_date=end_date,
                        title=event["title"],
                    )
                    logger.debug("New event created: %s" % event["title"])

            logger.debug("Removing all events that we did not get over API")
            IngameEvents.objects.filter(pk__in=event_ids_to_remove).delete()

            logger.debug(
                "All events fetched for %s" % self.character.character.character_name
            )

    @fetch_token_for_owner(["esi-calendar.read_calendar_events.v1"])
    def _fetch_events(self, token) -> list:

        character_id = self.character.character.character_id

        events = esi.client.Calendar.get_characters_character_id_calendar(
            character_id=character_id,
            token=token.valid_access_token(),
        ).results()

        return events

    def token(self, scopes=None) -> Tuple[Token, int]:
        """returns a valid Token for the owner"""
        token = None
        error = None

        # abort if character is not configured
        if self.character is None:
            logger.error("%s: No character configured to sync", self)
            error = self.ERROR_NO_CHARACTER

        # abort if character does not have sufficient permissions
        elif self.corporation and not self.character.user.has_perm(
            "opcalendar.add_ingame_calendar_owner"
        ):
            logger.error(
                "%s: This character does not have sufficient permission to sync corporation calendars",
                self,
            )
            error = self.ERROR_INSUFFICIENT_PERMISSIONS

        # abort if character does not have sufficient permissions
        elif not self.character.user.has_perm("opcalendar.add_ingame_calendar_owner"):
            logger.error(
                "%s: This character does not have sufficient permission to sync personal calendars",
                self,
            )
            error = self.ERROR_INSUFFICIENT_PERMISSIONS

        else:
            try:
                # get token
                token = (
                    Token.objects.filter(
                        user=self.character.user,
                        character_id=self.character.character.character_id,
                    )
                    .require_scopes(scopes)
                    .require_valid()
                    .first()
                )
            except TokenInvalidError:
                logger.error("%s: Invalid token for fetching calendars", self)
                error = self.ERROR_TOKEN_INVALID
            except TokenExpiredError:
                logger.error("%s: Token expired for fetching calendars", self)
                error = self.ERROR_TOKEN_EXPIRED
            else:
                if not token:
                    logger.error("%s: No token found with sufficient scopes", self)
                    error = self.ERROR_TOKEN_INVALID

        return token, error


class IngameEvents(models.Model):

    event_id = models.PositiveBigIntegerField(
        primary_key=True, help_text="The EVE ID of the event"
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        help_text="Event holder",
    )
    event_start_date = models.DateTimeField()
    event_end_date = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=128)
    text = models.TextField()
    owner_type = models.CharField(max_length=128)
    owner_name = models.CharField(max_length=128)
    importance = models.CharField(max_length=128)
    duration = models.CharField(max_length=128)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Ingame Event"
        verbose_name_plural = "Ingame Events"

    def get_absolute_url(self):
        return reverse("opcalendar:ingame-event-detail", args=(self.event_id,))

    @property
    def get_html_url(self):
        url = reverse("opcalendar:ingame-event-detail", args=(self.event_id,))
        return f"{url}"

    @property
    def get_html_operation_color(self):
        return "black"

    @property
    def get_html_title(self):
        return f'{self.event_start_date.strftime("%H:%M")} - {self.event_end_date.strftime("%H:%M")}<i> {self.owner_name}</i><br><b>{self.title}</b>'


class EventMember(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["event", "user"]

    def __str__(self):
        return str(self.user)
