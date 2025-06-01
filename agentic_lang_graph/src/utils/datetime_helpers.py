"""
Helpers pour la gestion des dates dans le projet.
Résout les problèmes de timezone mixing.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    S'assure qu'une datetime a une timezone.
    
    Args:
        dt: Datetime à vérifier
        
    Returns:
        Datetime avec timezone UTC ou None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Date naive -> considère comme UTC
        return dt.replace(tzinfo=timezone.utc)
    
    return dt

def safe_datetime_diff(dt1: Optional[datetime], dt2: Optional[datetime]) -> Optional[timedelta]:
    """
    Calcule la différence entre deux dates de manière sécurisée.
    
    Args:
        dt1: Première date
        dt2: Seconde date
        
    Returns:
        Différence ou None si impossible
    """
    if dt1 is None or dt2 is None:
        return None
    
    # S'assure que les deux dates ont une timezone
    dt1_aware = ensure_timezone_aware(dt1)
    dt2_aware = ensure_timezone_aware(dt2)
    
    if dt1_aware is None or dt2_aware is None:
        return None
    
    return dt1_aware - dt2_aware

def get_age_in_days(published_date: Optional[datetime]) -> str:
    """
    Retourne l'âge d'un contenu en jours de manière sécurisée.
    
    Args:
        published_date: Date de publication
        
    Returns:
        String représentant l'âge ou "?" si indéterminable
    """
    if published_date is None:
        return "?"
    
    now = datetime.now(timezone.utc)
    diff = safe_datetime_diff(now, published_date)
    
    if diff is None:
        return "?"
    
    return str(diff.days)

def normalize_published_date(date_str: str, source: str = "") -> Optional[datetime]:
    """
    Normalise une date de publication depuis différents formats.
    
    Args:
        date_str: String de date à parser
        source: Source d'origine pour adapter le parsing
        
    Returns:
        Datetime normalisée en UTC ou None
    """
    if not date_str:
        return None
    
    try:
        # Format ISO standard
        if 'T' in date_str and ('Z' in date_str or '+' in date_str or '-' in date_str):
            # Remplace Z par +00:00 pour Python
            normalized = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(normalized)
        
        # Format simple YYYY-MM-DD
        if len(date_str) == 10 and date_str.count('-') == 2:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.replace(tzinfo=timezone.utc)
        
        # Autres formats selon la source
        if source.lower() == 'medium':
            # Format Medium spécifique si nécessaire
            pass
        elif source.lower() == 'arxiv':
            # Format ArXiv déjà géré au-dessus
            pass
        
        return None
        
    except (ValueError, TypeError) as e:
        print(f"Erreur parsing date '{date_str}' pour {source}: {e}")
        return None
