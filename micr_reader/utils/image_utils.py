# utils/image_utils.py
"""
Utilitaires pour le traitement et la validation d'images
"""

import base64
import os
from typing import Tuple, Optional
from PIL import Image
import io
from config import config

class ImageProcessor:
    """
    Processeur d'images pour le MICR Reader
    """
    
    def __init__(self):
        self.max_file_size = config.image.max_file_size_mb * 1024 * 1024  # Convertir en bytes
        self.supported_formats = config.image.supported_formats
    
    def validate_image(self, image_path: str) -> bool:
        """
        Valide qu'une image est acceptable pour l'analyse
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            True si l'image est valide
        """
        try:
            # Vérifier que le fichier existe
            if not os.path.exists(image_path):
                print(f"❌ Fichier non trouvé: {image_path}")
                return False
            
            # Vérifier la taille du fichier
            file_size = os.path.getsize(image_path)
            if file_size > self.max_file_size:
                print(f"❌ Fichier trop volumineux: {file_size / (1024*1024):.1f}MB (max: {config.image.max_file_size_mb}MB)")
                return False
            
            if file_size == 0:
                print(f"❌ Fichier vide: {image_path}")
                return False
            
            # Vérifier l'extension
            _, ext = os.path.splitext(image_path.lower())
            if ext not in self.supported_formats:
                print(f"❌ Format non supporté: {ext} (supportés: {', '.join(self.supported_formats)})")
                return False
            
            # Vérifier que l'image peut être ouverte
            try:
                with Image.open(image_path) as img:
                    # Vérifier les dimensions minimales
                    width, height = img.size
                    if width < 100 or height < 100:
                        print(f"❌ Image trop petite: {width}x{height} (minimum 100x100)")
                        return False
                    
                    # Vérifier que ce n'est pas une image corrompue
                    img.verify()
            
            except Exception as e:
                print(f"❌ Image corrompue ou illisible: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur validation image: {e}")
            return False
    
    def encode_image(self, image_path: str) -> str:
        """
        Encode une image en base64 pour l'API OpenAI
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            Image encodée en base64
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Impossible d'encoder l'image {image_path}: {e}")
    
    def get_image_info(self, image_path: str) -> dict:
        """
        Récupère les informations détaillées d'une image
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            Dictionnaire avec les informations de l'image
        """
        try:
            file_size = os.path.getsize(image_path)
            
            with Image.open(image_path) as img:
                return {
                    'path': image_path,
                    'filename': os.path.basename(image_path),
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.size[0],
                    'height': img.size[1],
                    'file_size_bytes': file_size,
                    'file_size_mb': file_size / (1024 * 1024),
                    'is_valid': self.validate_image(image_path)
                }
        except Exception as e:
            return {
                'path': image_path,
                'error': str(e),
                'is_valid': False
            }
    
    def is_image_quality_sufficient(self, image_path: str, min_dpi: int = 150) -> bool:
        """
        Évalue si la qualité de l'image est suffisante pour l'OCR MICR
        
        Args:
            image_path: Chemin vers l'image
            min_dpi: DPI minimum requis
            
        Returns:
            True si la qualité semble suffisante
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Vérifier les dimensions (approximation pour du texte MICR lisible)
                min_width = 800   # Largeur minimum pour un chèque scanné
                min_height = 400  # Hauteur minimum
                
                if width < min_width or height < min_height:
                    print(f"⚠️ Résolution faible: {width}x{height} (recommandé: >{min_width}x{min_height})")
                    return False
                
                # Vérifier le DPI si disponible
                try:
                    dpi = img.info.get('dpi', (72, 72))
                    if isinstance(dpi, tuple):
                        actual_dpi = min(dpi)
                    else:
                        actual_dpi = dpi
                    
                    if actual_dpi < min_dpi:
                        print(f"⚠️ DPI faible: {actual_dpi} (recommandé: >{min_dpi})")
                        return False
                        
                except:
                    # Si on ne peut pas déterminer le DPI, on continue
                    pass
                
                # Vérifier le mode couleur (préférer niveaux de gris ou couleur)
                if img.mode == '1':  # Bitmap noir et blanc
                    print("⚠️ Image en bitmap N&B, peut affecter la qualité de détection")
                
                return True
                
        except Exception as e:
            print(f"❌ Erreur évaluation qualité: {e}")
            return False
    
    def optimize_for_ocr(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Optimise une image pour l'OCR MICR (expérimental)
        
        Args:
            image_path: Chemin de l'image source
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin de l'image optimisée
        """
        try:
            if output_path is None:
                name, ext = os.path.splitext(image_path)
                output_path = f"{name}_optimized{ext}"
            
            with Image.open(image_path) as img:
                # Convertir en niveaux de gris si nécessaire
                if img.mode != 'L' and img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionner si trop petit
                width, height = img.size
                if width < 1200 or height < 600:
                    # Calculer un facteur d'échelle
                    scale_factor = max(1200/width, 600/height)
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Sauvegarder avec haute qualité
                if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
                    img.save(output_path, 'JPEG', quality=95, dpi=(300, 300))
                else:
                    img.save(output_path, dpi=(300, 300))
                
                print(f"✅ Image optimisée sauvée: {output_path}")
                return output_path
                
        except Exception as e:
            print(f"❌ Erreur optimisation: {e}")
            return image_path  # Retourner l'original en cas d'erreur
    
    def batch_validate(self, image_paths: list) -> dict:
        """
        Valide un lot d'images
        
        Args:
            image_paths: Liste des chemins d'images
            
        Returns:
            Dictionnaire {chemin: est_valide}
        """
        results = {}
        valid_count = 0
        
        for image_path in image_paths:
            is_valid = self.validate_image(image_path)
            results[image_path] = is_valid
            if is_valid:
                valid_count += 1
        
        print(f"📊 Validation lot: {valid_count}/{len(image_paths)} images valides")
        return results
    
    def get_supported_formats(self) -> list:
        """Retourne les formats d'image supportés"""
        return self.supported_formats.copy()
    
    def estimate_processing_time(self, image_path: str) -> float:
        """
        Estime le temps de traitement en fonction de la taille de l'image
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            Temps estimé en secondes
        """
        try:
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            
            # Estimation basée sur la taille du fichier
            # Temps de base + temps proportionnel à la taille
            base_time = 1.5  # secondes de base pour l'API
            size_factor = 0.3  # secondes par MB
            
            estimated_time = base_time + (file_size_mb * size_factor)
            
            # Limiter entre 1 et 30 secondes
            return max(1.0, min(estimated_time, 30.0))
            
        except Exception:
            return 3.0  # Estimation par défaut
