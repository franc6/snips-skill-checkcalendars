#!/usr/bin/env python3
"""Action for the Check Calendars skill"""
from datetime import timedelta
import gettext
import locale
import os
import re
import sys
import warnings

import arrow
from arrow.factory import ArrowParseWarning
from dumper import dump
from simple_rest_client.api import API

from snipskit.hermes.apps import HermesSnipsApp
from snipskit.config import AppConfig
from snipskit.hermes.decorators import intent
from hermes_python.ontology.injection import (
    InjectionRequestMessage,
    AddFromVanillaInjectionRequest
    )

from CalendarResource import CalendarResource

warnings.simplefilter('ignore', ArrowParseWarning)

# Set up localse
locale.setlocale(locale.LC_ALL, '')
# Set gettext to be the right thing for python2 and python3
if sys.version_info[0] < 3:
    gettext = gettext.translation('messages', localedir='locales').ugettext
else:
    gettext.bindtextdomain('messages', 'locales')
    gettext = gettext.gettext

class CheckCalendarsApp(HermesSnipsApp):
    """HermeseSnipsApp for Check Calendars skill"""

    calendars = []
    token = None
    url = None
    api = None

    @intent('franc:checkCalendar')
    def check_calendar(self, hermes, intent_message):
        """Intent handler for checkCalendar"""

        calendar = None
        calendar_name = None
        timeref = None
        now = arrow.now()
        if intent_message.slots is not None:
            if intent_message.slots.Calendar:
                calendar_name = str(intent_message.slots.Calendar[0].slot_value.value.value)
                print(calendar_name)

            if intent_message.slots.Date:
                date_slot = intent_message.slots.Date[0]
                slot_value = date_slot.slot_value
                dump(slot_value)
                dump(slot_value.value)
                timeref = str(date_slot.raw_value)
                if slot_value.value.kind == "InstantTime":
                    start = arrow.get(slot_value.value.value)
                    if slot_value.grain == "Day":
                        end = start.ceil('day')
                    if slot_value.grain == "Week":
                        # TODO: Figure out how to fix up start & end based on start of week
                        end = start.ceil('day')
                        end += timedelta(days=7)
                if slot_value.value.kind == "TimeInterval":
                    start = arrow.get(slot_value.value['from'])
                    end = arrow.get(slot_value.value.to)

        # if timeref wasn't set, then we should jsut use today!
        if timeref is None:
            timeref = "today"
            start = now.floor('day')
            end = now.ceil('day')

        # Get calendar from calendar_name
        if calendar_name is not None:
            for cal in self.calendars:
                if cal['name'] == calendar_name:
                    calendar = cal
                    break;
            # TODO: if calendar was not found, then snips didn't understand
            # the name of the calendar correctly; ask for clarification
            #if calendar is None:

        # At this point, we know which calendar the user wants, or if the
        # user wants all calendars, so get the events!
        if calendar is not None:
            event_list = self._get_events(calendar, start, end)
        else:
            event_list = []
            for calendar in self.config['secret']['calendars']:
                event_list.append(self._get_events(calendar, start, end))

        # Build our response string...
        events = ''
        if len(event_list) != 0:
            now = arrow.now()
            for event in event_list:
                start_time = arrow.get(event['start'])
                end_time = arrow.get(event['end'])
                td = end_time - start_time
                if td.days == 1 and td.seconds == 0:
                    events += gettext("STR_EVENT_ALL_DAY").format(day=start_time.stftime('%A'))
                else:
                    td = start_time - now
                    if td.days == 0 and td.seconds <= 7200:
                        start = start_time.humanize()
                    else:
                        start = start_time.ctime()
                    events += gettext("STR_EVENT") \
                        .format(start=start, end=end_time.ctime(), subject=event['title'])
            sentence = gettext("STR_EVENTS") \
                .format(timeref=timeref, events=events)
        else:
            sentence = gettext("STR_NO_EVENTS").format(timeref=timeref)

        hermes.publish_end_session(intent_message.session_id, sentence)

    def initialize(self):
        """Initialization; inject our calendar names"""
        self.calendars = []
        # Iterate through the whole set of calendars
        if 'token' in self.config['secret']:
            self.token = self.config['secret']['token']
        else:
            self.token = os.environ['HASSIO_TOKEN']

        if 'url' in self.config['secret']:
            self.url = self.config['secret']['url']
        elif self.token is not None:
            self.url = 'http://hassio/homeassistant/api'

        self.api = API(api_root_url = self.url,
                params = {},
                headers={ 'Authorization': "Bearer {}".format(self.token),
                    'Content-Type': 'application/json' },
                timeout=30,
                append_slash=False,
                json_encode_body=True
                )
        self.api.add_resource(resource_name='calendars', resource_class=CalendarResource)
        self._get_calendars()
        self.inject_calendar_names()

    def get_calendar_names_payload(self):
        """Gets the names as an AddFromVanillaInjectionRequest"""
        calendar_names = []
        for calendar in self.calendars:
            calendar_names.append(calendar['name'])
        return AddFromVanillaInjectionRequest({'calendar_names': calendar_names})

    def get_update_payload(self):
        """Gets all injection requests as an InjectionRequestMessage"""
        operations = []
        operations.append(self.get_calendar_names_payload())
        return InjectionRequestMessage(operations)

    def inject_calendar_names(self):
        """Requests an injection of the lists and items"""
        payload = self.get_update_payload()
        self.hermes.request_injection(payload)

    def _get_events(self, calendar, start, end):
        response = self.api.calendars.events(calendar['entity_id'], start, end)
        return response.body

    def _get_calendars(self):
        response = self.api.calendars.list()
        for calendar in response.body:
            self.calendars.append(calendar)

if __name__ == "__main__":
    CheckCalendarsApp(config=AppConfig())

