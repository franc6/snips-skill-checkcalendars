#!/usr/bin/env python3
"""Action for the Check Calendars skill"""

import gettext
import locale
import re
import sys

from snipskit.hermes.apps import HermesSnipsApp
from snipskit.config import AppConfig
from snipskit.hermes.decorators import intent
from hermes_python.ontology.injection import (
    InjectionRequestMessage,
    AddFromVanillaInjectionRequest
    )

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

    @intent('franc:checkCalendar')
    def check_calendar(self, hermes, intent_message):
        """Intent handler for checkCalendar"""

        # TODO: Set calendar variable based on the calendar slot;

        # TODO: Set start and end based on the Date slot

        # TODO: Fix up start & end based on self.config['global']['startOfWeek'] if slot is for a whole week

        if calendar is not None:
            event_list = self._get_events(calendar, start, end)
        else:
            event_list = []
            for calendar in self.config['secret']['calendars']:
                event_list.append(self._get_events(calendar, start, end)

        events = ''
        for event in event_list:
            events += gettext("STR_EVENT").format(start=start,end=end,subject=subject)

        sentence = gettext("STR_EVENTS") \
            .format(events=events)
        hermes.publish_end_session(intent_message.session_id, sentence)

    def initialize(self):
        """Initialization; inject our calendar names"""
        self.inject_calendar_names()

    def get_calendar_names_payload(self, calendar_names):
        """Gets the lists as an AddFromVanillaInjectionRequest"""
        return AddFromVanillaInjectionRequest({'calendar_names': calendar_names})

    def get_update_payload(self):
        """Gets all injection requests as an InjectionRequestMessage"""
        operations = []

        # TODO: Find the right way to iterate through a whole set of calendars!
        calendar_names = []
        for calendar in self.config['secret']['calendars']:
            calendar_names.append(calendar['name'])

        operations.append(self.get_calendar_names_payload(calendar_names))
        return InjectionRequestMessage(operations)

    def inject_calendar_names(self):
        """Requests an injection of the lists and items"""
        payload = self.get_update_payload()
        self.hermes.request_injection(payload)

    def _get_events(self, calendar, start, end):
        event_list = []
        return event_list

if __name__ == "__main__":
    CheckCalendarsApp(config=AppConfig())
