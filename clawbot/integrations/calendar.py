"""Google Calendar API integration"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from clawbot.auth.oauth import get_google_credentials
from dateutil import parser as date_parser


class CalendarService:
    """Google Calendar API service wrapper"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.credentials = get_google_credentials(user_id)
        if not self.credentials:
            raise ValueError(f"No valid credentials found for user {user_id}")
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars"""
        try:
            calendar_list = self.service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except Exception as e:
            raise Exception(f"Error listing calendars: {str(e)}")
    
    def get_calendar(self, calendar_id: str = 'primary') -> Dict[str, Any]:
        """Get calendar details"""
        try:
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()
            return calendar
        except Exception as e:
            raise Exception(f"Error getting calendar: {str(e)}")
    
    def list_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = 'startTime'
    ) -> List[Dict[str, Any]]:
        """List events from calendar"""
        try:
            if time_min is None:
                time_min = datetime.utcnow()
            if time_max is None:
                time_max = time_min + timedelta(days=7)
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=single_events,
                orderBy=order_by
            ).execute()
            
            events = events_result.get('items', [])
            return [self._parse_event(event) for event in events]
        except Exception as e:
            raise Exception(f"Error listing events: {str(e)}")
    
    def get_event(
        self, 
        event_id: str, 
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """Get event details"""
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return self._parse_event(event)
        except Exception as e:
            raise Exception(f"Error getting event: {str(e)}")
    
    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = 'primary',
        timezone: str = 'UTC',
        add_meet_link: bool = False
    ) -> Dict[str, Any]:
        """Create a new calendar event. Set add_meet_link=True for a Google Meet video call."""
        try:
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
            }
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            if add_meet_link:
                event['conferenceData'] = {
                    'createRequest': {
                        'requestId': str(uuid.uuid4()),
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                    }
                }
            
            insert_kwargs = {'calendarId': calendar_id, 'body': event}
            if add_meet_link:
                insert_kwargs['conferenceDataVersion'] = 1
            
            created_event = self.service.events().insert(**insert_kwargs).execute()
            
            return self._parse_event(created_event)
        except Exception as e:
            raise Exception(f"Error creating event: {str(e)}")
    
    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = 'primary',
        timezone: str = 'UTC'
    ) -> Dict[str, Any]:
        """Update an existing event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start_time:
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                }
            if end_time:
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                }
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return self._parse_event(updated_event)
        except Exception as e:
            raise Exception(f"Error updating event: {str(e)}")
    
    def delete_event(
        self, 
        event_id: str, 
        calendar_id: str = 'primary'
    ) -> bool:
        """Delete an event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Error deleting event: {str(e)}")
    
    def _parse_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse calendar event into readable format"""
        start = event.get('start', {})
        end = event.get('end', {})
        
        start_time = None
        end_time = None
        
        if 'dateTime' in start:
            start_time = date_parser.parse(start['dateTime'])
        elif 'date' in start:
            start_time = date_parser.parse(start['date'])
        
        if 'dateTime' in end:
            end_time = date_parser.parse(end['dateTime'])
        elif 'date' in end:
            end_time = date_parser.parse(end['date'])
        
        result = {
            'id': event.get('id'),
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': start_time.isoformat() if start_time else None,
            'end': end_time.isoformat() if end_time else None,
            'attendees': [
                att.get('email') for att in event.get('attendees', [])
            ],
            'status': event.get('status', ''),
            'html_link': event.get('htmlLink', ''),
            'created': event.get('created', ''),
            'updated': event.get('updated', '')
        }
        # Include Google Meet / Hangouts link if present
        conf = event.get('conferenceData', {})
        entry_points = conf.get('entryPoints', [])
        for ep in entry_points:
            if ep.get('entryPointType') == 'video':
                result['meet_link'] = ep.get('uri', '')
                break
        return result
    
    def search_events(
        self,
        query: str,
        calendar_id: str = 'primary',
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search events by query"""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [self._parse_event(event) for event in events]
        except Exception as e:
            raise Exception(f"Error searching events: {str(e)}")
