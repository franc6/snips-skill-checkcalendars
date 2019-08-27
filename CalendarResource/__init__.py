from simple_rest_client.resource import Resource

class CalendarResource(Resource):
    actions = {
            "list": { "method": "GET", "url": "calendars"},
            "events": { "method": "GET", "url": "calendars/{}?start={}&end={}"}
    }

