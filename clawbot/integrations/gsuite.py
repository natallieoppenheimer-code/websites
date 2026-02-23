"""GSuite Admin API integration"""
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from clawbot.auth.oauth import get_google_credentials


class GSuiteService:
    """GSuite Admin API service wrapper"""
    
    def __init__(self, user_id: str, domain: Optional[str] = None):
        self.user_id = user_id
        self.domain = domain
        self.credentials = get_google_credentials(user_id)
        if not self.credentials:
            raise ValueError(f"No valid credentials found for user {user_id}")
        
        # GSuite Admin API requires domain-wide delegation
        # The credentials must be impersonating a super admin
        self.service = build('admin', 'directory_v1', credentials=self.credentials)
    
    def list_users(
        self,
        domain: Optional[str] = None,
        max_results: int = 100,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List users in the domain"""
        try:
            params = {
                'maxResults': max_results,
                'orderBy': 'email'
            }
            
            if domain:
                params['domain'] = domain
            elif self.domain:
                params['domain'] = self.domain
            
            if query:
                params['query'] = query
            
            results = self.service.users().list(**params).execute()
            users = results.get('users', [])
            
            return [self._parse_user(user) for user in users]
        except Exception as e:
            raise Exception(f"Error listing users: {str(e)}")
    
    def get_user(self, user_key: str) -> Dict[str, Any]:
        """Get user details"""
        try:
            user = self.service.users().get(userKey=user_key).execute()
            return self._parse_user(user)
        except Exception as e:
            raise Exception(f"Error getting user: {str(e)}")
    
    def create_user(
        self,
        primary_email: str,
        given_name: str,
        family_name: str,
        password: Optional[str] = None,
        change_password_at_next_login: bool = True
    ) -> Dict[str, Any]:
        """Create a new user"""
        try:
            user_data = {
                'primaryEmail': primary_email,
                'name': {
                    'givenName': given_name,
                    'familyName': family_name
                },
                'password': password or self._generate_password(),
                'changePasswordAtNextLogin': change_password_at_next_login
            }
            
            user = self.service.users().insert(body=user_data).execute()
            return self._parse_user(user)
        except Exception as e:
            raise Exception(f"Error creating user: {str(e)}")
    
    def update_user(
        self,
        user_key: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None,
        suspended: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update user details"""
        try:
            user = self.service.users().get(userKey=user_key).execute()
            
            if given_name:
                user['name']['givenName'] = given_name
            if family_name:
                user['name']['familyName'] = family_name
            if suspended is not None:
                user['suspended'] = suspended
            
            updated_user = self.service.users().update(
                userKey=user_key,
                body=user
            ).execute()
            
            return self._parse_user(updated_user)
        except Exception as e:
            raise Exception(f"Error updating user: {str(e)}")
    
    def delete_user(self, user_key: str) -> bool:
        """Delete a user"""
        try:
            self.service.users().delete(userKey=user_key).execute()
            return True
        except Exception as e:
            raise Exception(f"Error deleting user: {str(e)}")
    
    def list_groups(
        self,
        domain: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List groups in the domain"""
        try:
            params = {'maxResults': max_results}
            
            if domain:
                params['domain'] = domain
            elif self.domain:
                params['domain'] = self.domain
            
            results = self.service.groups().list(**params).execute()
            groups = results.get('groups', [])
            
            return [self._parse_group(group) for group in groups]
        except Exception as e:
            raise Exception(f"Error listing groups: {str(e)}")
    
    def get_group(self, group_key: str) -> Dict[str, Any]:
        """Get group details"""
        try:
            group = self.service.groups().get(groupKey=group_key).execute()
            return self._parse_group(group)
        except Exception as e:
            raise Exception(f"Error getting group: {str(e)}")
    
    def list_group_members(self, group_key: str) -> List[Dict[str, Any]]:
        """List members of a group"""
        try:
            results = self.service.members().list(groupKey=group_key).execute()
            members = results.get('members', [])
            
            return [
                {
                    'email': member.get('email'),
                    'role': member.get('role'),
                    'type': member.get('type')
                }
                for member in members
            ]
        except Exception as e:
            raise Exception(f"Error listing group members: {str(e)}")
    
    def add_member_to_group(
        self,
        group_key: str,
        email: str,
        role: str = 'MEMBER'
    ) -> Dict[str, Any]:
        """Add a member to a group"""
        try:
            member_data = {
                'email': email,
                'role': role
            }
            
            member = self.service.members().insert(
                groupKey=group_key,
                body=member_data
            ).execute()
            
            return {
                'email': member.get('email'),
                'role': member.get('role'),
                'type': member.get('type')
            }
        except Exception as e:
            raise Exception(f"Error adding member to group: {str(e)}")
    
    def remove_member_from_group(
        self,
        group_key: str,
        email: str
    ) -> bool:
        """Remove a member from a group"""
        try:
            self.service.members().delete(
                groupKey=group_key,
                memberKey=email
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Error removing member from group: {str(e)}")
    
    def _parse_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Parse user data into readable format"""
        return {
            'id': user.get('id'),
            'primary_email': user.get('primaryEmail'),
            'first_name': user.get('name', {}).get('givenName'),
            'last_name': user.get('name', {}).get('familyName'),
            'full_name': user.get('name', {}).get('fullName'),
            'is_admin': user.get('isAdmin', False),
            'is_delegated_admin': user.get('isDelegatedAdmin', False),
            'suspended': user.get('suspended', False),
            'creation_time': user.get('creationTime'),
            'last_login_time': user.get('lastLoginTime'),
            'org_unit_path': user.get('orgUnitPath'),
            'aliases': user.get('aliases', [])
        }
    
    def _parse_group(self, group: Dict[str, Any]) -> Dict[str, Any]:
        """Parse group data into readable format"""
        return {
            'id': group.get('id'),
            'email': group.get('email'),
            'name': group.get('name'),
            'description': group.get('description'),
            'admin_created': group.get('adminCreated', False)
        }
    
    def _generate_password(self, length: int = 16) -> str:
        """Generate a random password"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
