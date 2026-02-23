"""Integrations module for Clawbot"""
from clawbot.integrations.gmail import GmailService
from clawbot.integrations.calendar import CalendarService
from clawbot.integrations.gsuite import GSuiteService

__all__ = ['GmailService', 'CalendarService', 'GSuiteService']
