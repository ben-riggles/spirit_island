from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import os
import pandas as pd
import random
import re


SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SHEET: str = '1X7nJuSdKJE26aJguIfNbmAKGN7eRv7jb6chR6O_h3LA'

def credentials() -> Credentials:
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None

    if os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('creds.json', SCOPES)
        creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    return creds

def pull_data(page: str, range: str = None) -> list[list]:
    if range is not None:
        page = f'{page}!{range}'

    service = build('sheets', 'v4', credentials=credentials())
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SHEET, range=page).execute()
    return result.get('values', [])


def spirit_odds(df) -> dict[str, int]:
    spirits = [x[0] for x in pull_data('Spirits', 'A2:A')]
    cols = [x for x in df.columns if re.search('spirit', x, re.IGNORECASE)]
    query = ' | '.join([f'(`{x}` == "<spirit>")' for x in cols])
    max_idx = df.index[-1]

    def _spirit_odds(spirit: str) -> int:
        _df = df.query(query.replace('<spirit>', spirit))

        # Get # of games since last play
        try:
            last_play = max_idx - _df.index[-1]
        except IndexError:
            last_play = max_idx

        # If played within last two games, set odds to 0
        if last_play < 2:
            return 0
        
        # Get # of games since second to last play
        try:
            second_last_play = max_idx - _df.index[-2]
        except IndexError:
            second_last_play = max_idx

        # Odds are (# of games since last play) + 0.5 * (# of games since play before that)
        return last_play * (second_last_play // 2)
    
    return {x: _spirit_odds(x) for x in spirits}


if __name__ == '__main__':
    data = pull_data('Game Log')
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df[df['Result'].str.len() > 0]
    odds = spirit_odds(df)

    spirit1 = random.choices(list(odds.keys()), weights=list(odds.values()), k=1)[0]
    odds[spirit1] = 0
    spirit2 = random.choices(list(odds.keys()), weights=list(odds.values()), k=1)[0]

    print([spirit1, spirit2])
    