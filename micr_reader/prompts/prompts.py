# config/prompts.py
"""
Configuration des prompts pour l'analyse MICR
"""

class MICRPrompts:
    """Prompts pour l'analyse MICR des chèques canadiens"""
    
    @staticmethod
    def get_canadian_micr_prompt() -> str:
        """
        Prompt spécialisé pour l'analyse MICR des chèques canadiens - SPEC CORRECTE
        
        Returns:
            str: Prompt optimisé pour GPT-4o
        """
        return """
Analysez cette image de chèque canadien et extrayez les informations du code MICR (Magnetic Ink Character Recognition) situé au bas du chèque.

Le code MICR canadien suit ce format EXACT (éléments séparés par des espaces et symboles E-13B):
CHEQUE ⑆ TRANSIT ⑆ INSTITUTION ⑈ ACCOUNT ⑈

Où :
1. **CHEQUE** : Numéro de chèque (1-10 chiffres, parfois avec zéros en préfixe) - OPTIONNEL
2. **TRANSIT** : Code de transit/succursale (5 chiffres exactement) - OBLIGATOIRE
3. **INSTITUTION** : Numéro d'institution bancaire (3 chiffres exactement) - OBLIGATOIRE
4. **ACCOUNT** : Numéro de compte (7-12 chiffres) - OBLIGATOIRE

IMPORTANT: 
- Si le numéro de chèque n'est pas visible ou présent, laissez le champ vide
- Les informations essentielles sont : TRANSIT, INSTITUTION et ACCOUNT
- Un chèque sans numéro de chèque reste valide

Symboles E-13B :
- ⑆ : Séparateur de transit (entre chèque-transit et transit-institution)
- ⑈ : Séparateur on-us (entre institution-compte et fin)
- ⑇ : Séparateur de montant (rarement utilisé)
- ⑉ : Tiret (rarement utilisé)

Exemples réels de lignes MICR canadiennes :

Chèque complet avec numéro :
{
    "raw_line": "001234 ⑆ 12345 ⑆ 003 ⑈ 987654321 ⑈",
    "raw_confidence": 0.97,
    "cheque_number": "001234",
    "transit_number": "12345",
    "institution_number": "003",
    "account_number": "987654321",
    "amount": "",
    "auxiliary_on_us": "",
    "success": true,
    "error_message": null
}

Chèque SANS numéro de chèque (courant) :
{
    "raw_line": "⑆ 12345 ⑆ 003 ⑈ 987654321 ⑈",
    "raw_confidence": 0.95,
    "cheque_number": "",
    "transit_number": "12345",
    "institution_number": "003",
    "account_number": "987654321",
    "amount": "",
    "auxiliary_on_us": "",
    "success": true,
    "error_message": null
}

Image de qualité moyenne, quelques flous :
{
    "raw_line": "005678 ⑆ ?2345 ⑆ 010 ⑈ ?56789012 ⑈",
    "raw_confidence": 0.73,
    "cheque_number": "005678",
    "transit_number": "22345",
    "institution_number": "010",
    "account_number": "456789012",
    "amount": "",
    "auxiliary_on_us": "",
    "success": true,
    "error_message": null
}

Image sans numéro de chèque, qualité moyenne :
{
    "raw_line": "⑆ ?2345 ⑆ 010 ⑈ ?56789012 ⑈",
    "raw_confidence": 0.71,
    "cheque_number": "",
    "transit_number": "22345",
    "institution_number": "010",
    "account_number": "456789012",
    "amount": "",
    "auxiliary_on_us": "",
    "success": true,
    "error_message": null
}

Image très floue, très incertain :
{
    "raw_line": "?????? ⑆ ????? ⑆ ??? ⑈ ???????? ⑈",
    "raw_confidence": 0.18,
    "cheque_number": "012000",
    "transit_number": "12000",
    "institution_number": "001",
    "account_number": "1000000",
    "amount": "",
    "auxiliary_on_us": "",
    "success": true,
    "error_message": null
}

Évaluez la confiance de 0.0 à 1.0 basée sur la clarté et la lisibilité de l'image :
- 0.95-1.0: Image parfaite, texte très net
- 0.85-0.94: Bonne qualité, texte lisible
- 0.70-0.84: Qualité moyenne, quelques incertitudes
- 0.50-0.69: Qualité médiocre, difficultés de lecture
- 0.20-0.49: Mauvaise qualité, très incertain
- 0.0-0.19: Illisible ou pas de chèque

IMPORTANT: Dans votre réponse JSON, utilisez EXACTEMENT les chiffres que vous voyez, sans espaces ni formatage supplémentaire.

Fournissez votre réponse UNIQUEMENT en format JSON avec cette structure exacte.
Si un élément n'est pas visible ou présent, utilisez une valeur vide.
Si l'analyse échoue complètement, retournez success: false avec un message d'erreur.
"""

    @staticmethod
    def get_us_micr_prompt() -> str:
        """
        Prompt pour les chèques américains (pour usage futur)
        
        Returns:
            str: Prompt pour chèques US
        """
        return """
Analysez cette image de chèque américain et extrayez les informations MICR.

Format MICR américain typique:
⑈routing number⑈ account number⑈ check number

[Prompt à développer si nécessaire]
"""

    @staticmethod
    def get_european_micr_prompt() -> str:
        """
        Prompt pour les chèques européens (pour usage futur)
        
        Returns:
            str: Prompt pour chèques européens
        """
        return """
Analysez cette image de chèque européen et extrayez les informations MICR.

[Prompt à développer si nécessaire]
"""

# Configuration des prompts par région
PROMPT_CONFIG = {
    "canada": MICRPrompts.get_canadian_micr_prompt,
    "us": MICRPrompts.get_us_micr_prompt,
    "europe": MICRPrompts.get_european_micr_prompt,
    "default": MICRPrompts.get_canadian_micr_prompt  # Par défaut: Canada
}

def get_micr_prompt(region: str = "canada") -> str:
    """
    Obtient le prompt MICR pour une région donnée
    
    Args:
        region: Région ("canada", "us", "europe")
        
    Returns:
        str: Prompt approprié
    """
    prompt_func = PROMPT_CONFIG.get(region.lower(), PROMPT_CONFIG["default"])
    return prompt_func()
