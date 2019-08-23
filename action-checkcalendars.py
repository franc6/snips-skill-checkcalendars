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

        # Respond that we added it to the list
        sentence = gettext("STR_ADD_SUCCESS_DETAILS") \
            .format(q=quantity, w=what, l=which_list)
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

        calendar_names = []
        for calendar in self.config['secret']['calendars']:
            calendar_names.append(calendar['name'])

        operations.append(self.get_calendar_names_payload(calendar_names))
        return InjectionRequestMessage(operations)

    def inject_calendar_names(self):
        """Requests an injection of the lists and items"""
        payload = self.get_update_payload()
        self.hermes.request_injection(payload)

if __name__ == "__main__":
    CheckCalendarsApp(config=AppConfig())
