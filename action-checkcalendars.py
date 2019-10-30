#!/usr/bin/env python3
"""Action for the Check Calendars skill"""
from datetime import timedelta
import gettext
import locale
from os import environ
import re
import sys
import threading
#import warnings

import arrow
#from arrow.factory import ArrowParseWarning
from dumper import dump
from simple_rest_client.api import API

from snipskit.hermes.apps import HermesSnipsApp
from snipskit.config import AppConfig
from snipskit.hermes.decorators import intent
from hermes_python.ontology.injection import (
    InjectionRequestMessage,
    AddFromVanillaInjectionRequest
    )
from hermes_python.ontology.slot import (
    InstantTimeValue,
    TimeIntervalValue
    )
from hermes_python.ffi.ontology import Grain

from CalendarResource import CalendarResource

#warnings.simplefilter('ignore', ArrowParseWarning)

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
    _nameregex = re.compile(r'[[:space:]`~!@#$%^&*()_-+=[]{}\|;;:,./<>?\'"]')
    _nameregex2 = re.compile(r'\s+')

    @intent('franc:checkCalendar')
    def check_calendar(self, hermes, intent_message):
        """Intent handler for checkCalendar"""

        calendar = None
        calendar_name = None
        timeref = None
        now = arrow.now()
        if intent_message.slots is not None:
            if intent_message.slots.Calendar:
                calendar_name = self._normalize_calendar_name(str(intent_message.slots.Calendar[0].slot_value.value.value))
                #calendar_name = str(intent_message.slots.Calendar[0].slot_value.value.value)
                self._progress("Checking calendar: {}".format(calendar_name))

            if intent_message.slots.Date:
                date_slot = intent_message.slots.Date[0]
                slot_value = date_slot.slot_value
                timeref = str(date_slot.raw_value)
                if isinstance(slot_value.value, InstantTimeValue):
                    start = arrow.get(slot_value.value.value, "YYYY-MM-DD HH:mm:ss ZZ")
                    if slot_value.value.grain == Grain.DAY:
                        end = start.ceil('day')
                    if slot_value.value.grain == Grain.WEEK:
                        # TODO: Figure out how to fix up start & end based on start of week
                        end = start.ceil('day')
                        end += timedelta(days=7)
                if isinstance(slot_value.value, TimeIntervalValue):
                    start = arrow.get(slot_value.value.from_date, "YYYY-MM-DD HH:mm:ss ZZ")
                    end = arrow.get(slot_value.value.to_date, "YYYY-MM-DD HH:mm:ss ZZ")

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
            if calendar is None:
                self._progress("Didn\'t find a matching calendar: {}".format(calendar_name))
            # TODO: if calendar was not found, then snips didn't understand
            # the name of the calendar correctly; ask for clarification
            #if calendar is None:

        threading.Timer(interval=0.2, function=self._check_calendars, args=[hermes, intent_message.site_id, calendar, start, end, timeref]).start()
        if calendar is None:
            hermes.publish_end_session(intent_message.session_id, gettext("PLEASE_WAIT_PLURAL"))
        else:
            hermes.publish_end_session(intent_message.session_id, gettext("PLEASE_WAIT").format(calendar=calendar['name']))

    def initialize(self):
        """Initialization; inject our calendar names"""
        self.calendars = []
        # Iterate through the whole set of calendars
        if 'token' in self.config['secret']:
            self.token = self.config['secret']['token']
        elif 'HASSIO_TOKEN' in environ:
            self.token = environ['HASSIO_TOKEN']

        if 'url' in self.config['secret']:
            self.url = self.config['secret']['url']
        elif self.token is not None and 'HASSIO_TOKEN' in environ:
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
            self._progress('Adding calendar name: {}'.format(calendar['name']))
            calendar_names.append(calendar['name'])
        return AddFromVanillaInjectionRequest({'CalendarName': calendar_names})

    def get_update_payload(self):
        """Gets all injection requests as an InjectionRequestMessage"""
        operations = []
        operations.append(self.get_calendar_names_payload())
        return InjectionRequestMessage(operations)

    def inject_calendar_names(self):
        """Requests an injection of the lists and items"""
        payload = self.get_update_payload()
        self.hermes.request_injection(payload)

    def _check_calendars(self, hermes, site_id, calendar, start, end, timeref):
        # At this point, we know which calendar the user wants, or if the
        # user wants all calendars, so get the events!
        if calendar is not None:
            self._progress('Checking single calendar')
            event_list = self._get_events(calendar, start, end)
        else:
            self._progress('Checking all calendars')
            event_list = []
            for calendar in self.calendars:
                event_list.extend(self._get_events(calendar, start, end))

        # Build our response string...
        events = ''
        if len(event_list) != 0:
            date_format = gettext("FORMAT_DATE_TIME_12")
            if self.config['secret']['Hour'] == 24:
                date_format = gettext("FORMAT_DATE_TIME_24")
            now = arrow.now()
            for event in event_list:
                start_time = arrow.get(event['start'])
                end_time = arrow.get(event['end'])
                td = end_time - start_time
                if td.days == 1 and td.seconds == 0:
                    event_text = gettext("STR_EVENT_ALL_DAY") \
                        .format(subject=event['title'], day=start_time.strftime('%A'))
                    events += event_text
                else:
                    td = start_time - now
                    if td.days == 0 and td.seconds <= 7200:
                        start = start_time.humanize(granularity='minute')
                    else:
                        start = start_time.strftime(date_format)
                    event_text = gettext("STR_EVENT") \
                        .format(start=start, end=end_time.strftime(date_format), subject=event['title'])
                    events += event_text

            sentence = gettext("STR_EVENTS") \
                .format(timeref=timeref, events=events)
        else:
            sentence = gettext("STR_NO_EVENTS").format(timeref=timeref)

        self._progress(sentence)
        hermes.publish_start_session_notification(site_id, sentence, None)
        #hermes.publish_end_session(session_id, sentence)

    def _get_events(self, calendar, start, end):
        date_format = gettext("FORMAT_DATE_TIME_24")
        self._progress("Getting events for calendar: {} start: {} end: {}".format(calendar['name'], start.strftime(date_format), end.strftime(date_format)))
        response = self.api.calendars.events(calendar['entity_id'], start, end)
        return response.body

    def _get_calendars(self):
        response = self.api.calendars.list()
        for calendar in response.body:
            calendar['name'] = self._normalize_calendar_name(calendar['name'])
            self.calendars.append(calendar)

    def _normalize_calendar_name(self, name):
        name = self._nameregex.sub(' ', name)
        name = self._nameregex2.sub(' ', name)
        return name.casefold()

    def _progress(self, progress):
        print(progress)

if __name__ == "__main__":
    CheckCalendarsApp(config=AppConfig())

