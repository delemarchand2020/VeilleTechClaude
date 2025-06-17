from msal import PublicClientApplication
import requests
import json

# ID d'application Microsoft publique (autorisé par Microsoft)
CLIENT_ID = "14d82eec-204b-4c2f-b7e0-296a0da1e4f0"  # Microsoft Graph PowerShell

# Permissions nécessaires
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

# Créer l'application
app = PublicClientApplication(CLIENT_ID)

# Authentification interactive (ouvrira votre navigateur)
print("Authentification en cours... Une fenêtre de navigateur va s'ouvrir.")
result = app.acquire_token_interactive(scopes=SCOPES)

if "access_token" in result:
    print("✅ Connexion réussie !")

    # Test : récupérer vos 5 derniers emails
    headers = {'Authorization': f'Bearer {result["access_token"]}'}
    response = requests.get(
        'https://graph.microsoft.com/v1.0/me/messages?$top=5',
        headers=headers
    )

    if response.status_code == 200:
        emails = response.json()
        print(f"📧 Trouvé {len(emails['value'])} emails")
        for email in emails['value']:
            print(f"- {email['subject']} (de: {email['sender']['emailAddress']['address']})")
    else:
        print(f"❌ Erreur: {response.status_code}")
else:
    print("❌ Échec de l'authentification")
    print(result.get("error_description"))