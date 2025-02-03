import json
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

app = FastAPI()

CREDS_PATH = 'creds.json'
GOOGLE_CLIENT_ID = ''
GOOGLE_CLIENT_SECRET = ''
GOOGLE_REDIRECT_URI = 'http://localhost:8000/auth/google/business'
SCOPES = ['https://www.googleapis.com/auth/business.manage']


@app.get("/")
def read_root(request: Request):
    url = request.url_for('get_auth_url')
    return RedirectResponse(url=url, status_code=302)


@app.get('/google/auth-url')
def get_auth_url():
    """
    Generate the Google OAuth URL.
    """
    flow = Flow.from_client_secrets_file(
        CREDS_PATH,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

    return {'auth_url': auth_url}


@app.get('/auth/google/business')
async def google_callback(request: Request):
    """
    Handle the Google OAuth callback.
    """
    code = request.query_params.get("code")

    if not code:
        raise HTTPException(status_code=400, detail='Code OAuth manquant.')

    flow = Flow.from_client_secrets_file(
        CREDS_PATH,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save the credentials to a file
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())

        return {'message': 'Authentification réussie. Tokens enregistrés.'}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OAuth: {str(e)}")


@app.get('/google/accounts')
def get_google_accounts():
    """
    Get the Google Business Profile accounts.
    :return: List of accounts.
    """
    if not os.path.exists("token.json"):
        raise HTTPException(status_code=401, detail="Authentification requise. Appelez /google/auth-url d'abord.")

    creds = Credentials.from_authorized_user_file("token.json", ['https://www.googleapis.com/auth/business.manage'])
    service = build('mybusinessaccountmanagement', "v1", credentials=creds)

    try:
        accounts = service.accounts().list().execute()
        account = accounts['accounts'][0]['name']
        print(f"Account : {account}")
        return {
            "account:": account,
            "accounts": accounts.get("accounts", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des comptes : {str(e)}")


@app.get("/google/locations/{account_id}")
def get_google_locations(account_id: str):
    """
    Get the Google Business Profile locations.
    :param account_id: The account ID.
    :return: List of locations.
    """
    if not os.path.exists("token.json"):
        raise HTTPException(status_code=401, detail="Authentification requise. Appelez /google/auth-url d'abord.")

    creds = Credentials.from_authorized_user_file("token.json", ['https://www.googleapis.com/auth/businessinformation'])

    # Initialisation du service Google My Business
    service = build("mybusinessbusinessinformation", "v1", credentials=creds)

    try:
        # Get the locations for the account
        locations = service.accounts().locations().list(
            parent=f"accounts/{account_id}",
            readMask="labels,name,storeCode,title,websiteUri"
        ).execute()

        return {"locations": locations.get("locations", [])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error to retrieve the establishments : {str(e)}")


@app.get("/google/reviews/{account_id}/{location_id}")
def get_google_reviews(account_id: str, location_id: str):
    """
    Get the Google Business Profile reviews.
    :param account_id: The location ID.
    :param location_id: The location ID.
    :return:
    """
    # Check if the token.json file exists
    if not os.path.exists("token.json"):
         raise HTTPException(status_code=401, detail="Authentication required. Call /google/auth-url first.")
    # Load the token from the token.json file
    creds = json.load(open("token.json"))
    print(f"Credentials : {creds.get('token')}")

    headers = {"Authorization": f"Bearer {creds.get('token')}"}
    url = f"https://mybusiness.googleapis.com/v4/accounts/{account_id}/locations/{location_id}/reviews"
    api_req = requests.get(url, headers=headers)
    review_data = api_req.json()
    print(f"Review Data : {review_data}")
    count = review_data.get('totalReviewCount', 0)
    print(f"Total Reviews : {count}")
    print(f"Reviews : {review_data.get('reviews')}")

    return {
        'account_id': account_id,
        'location_id': location_id,
        'total_reviews': review_data.get('totalReviewCount', 0),
        'averageRating': review_data.get('averageRating', 0),
        'reviews': review_data.get("reviews", [])
    }