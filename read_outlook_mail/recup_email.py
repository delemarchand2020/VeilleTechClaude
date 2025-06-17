import pandas as pd
import sys


def extract_emails(reception_csv, envoi_csv, output_csv):
    """Extrait tous les emails avec Esma Aimeur"""

    emails_found = []

    print("🔍 Recherche des emails d'Esma Aimeur")

    # 1. EMAILS REÇUS
    print("📥 Traitement des emails reçus...")
    try:
        df_reception = pd.read_csv(reception_csv, encoding='utf-8')
        print(f"   📂 {len(df_reception)} emails lus")

        for index, row in df_reception.iterrows():
            sender_name = str(row.get("De: (nom)", ""))
            sender_email = str(row.get("De: (adresse)", ""))

            # Recherche Esma Aimeur
            if "aimeur@iro.umontreal.ca" in sender_email.lower() or "aimeur" in sender_name.lower():
                emails_found.append({
                    'Date': 'Non disponible',
                    'Type': 'Reception',
                    'Objet': row.get('Objet', ''),
                    'De_nom': sender_name,
                    'De_adresse': sender_email,
                    'Corps': row.get('Corps', '')
                })
                print(f"✅ Reçu: {row.get('Objet', 'Sans objet')}")

    except Exception as e:
        print(f"❌ Erreur avec {reception_csv}: {e}")

    # 2. EMAILS ENVOYÉS
    print("📤 Traitement des emails envoyés...")
    try:
        df_envoi = pd.read_csv(envoi_csv, encoding='utf-8')
        print(f"   📂 {len(df_envoi)} emails lus")

        for index, row in df_envoi.iterrows():
            to_name = str(row.get("A: (nom)", ""))
            to_email = str(row.get("A: (adresse)", ""))

            # Recherche vers Esma
            if "aimeur" in to_email.lower() or "aimeur" in to_name.lower():
                emails_found.append({
                    'Date': 'Non disponible',
                    'Type': 'Envoi',
                    'Objet': row.get('Objet', ''),
                    'De_nom': row.get("De: (nom)", ""),
                    'De_adresse': row.get("De: (adresse)", ""),
                    'Corps': row.get('Corps', '')
                })
                print(f"✅ Envoyé: {row.get('Objet', 'Sans objet')}")

    except Exception as e:
        print(f"❌ Erreur avec {envoi_csv}: {e}")

    # 3. SAUVEGARDE
    if emails_found:
        df_result = pd.DataFrame(emails_found)
        df_result.to_csv(output_csv, index=False, encoding='utf-8')

        print(f"\n📊 RÉSUMÉ:")
        print(f"Total emails trouvés: {len(emails_found)}")
        print(f"Emails reçus: {len([e for e in emails_found if e['Type'] == 'Reception'])}")
        print(f"Emails envoyés: {len([e for e in emails_found if e['Type'] == 'Envoi'])}")
        print(f"Fichier sauvé: {output_csv}")

    else:
        print("❌ Aucun email trouvé")

    return emails_found


# UTILISATION
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py reception.csv envoi.csv")
        sys.exit(1)

    reception_csv = sys.argv[1]
    envoi_csv = sys.argv[2]
    output_csv = "emails_esma_final.csv"

    extract_emails(reception_csv, envoi_csv, output_csv)