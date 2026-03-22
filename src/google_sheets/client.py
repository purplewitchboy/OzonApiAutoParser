import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    def __init__(self, credentials_json: Dict[str, Any] = None, credentials_file: str = None):
        if credentials_json:
            self.credentials_json = credentials_json
        elif credentials_file:
            with open(credentials_file, 'r') as f:
                self.credentials_json = json.load(f)
        else:
            raise ValueError("Need credentials_json or credentials_file")
        
        self._authenticate()
    
    def _authenticate(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                self.credentials_json, scope
            )
            
            self.client = gspread.authorize(credentials)
            logger.info("Google Sheets authenticated")
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise
    
    def open_spreadsheet(self, spreadsheet_id: str):
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            logger.info(f"Opened spreadsheet: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            logger.error(f"Error opening spreadsheet {spreadsheet_id}: {e}")
            raise