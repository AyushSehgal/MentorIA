from .canvas import CanvasConnector
from .gmail import GmailConnector
from .google_calendar import GoogleCalendarConnector
from .piazza import PiazzaConnector

CONNECTORS = {
    "canvas": CanvasConnector(),
    "google_calendar": GoogleCalendarConnector(),
    "gmail": GmailConnector(),
    "piazza": PiazzaConnector(),
}
