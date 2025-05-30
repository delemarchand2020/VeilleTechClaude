# examples/batch_processing.py
"""
Exemple de traitement en lot de chèques MICR
"""

import os
import sys
import csv
import json
import time
from typing import Dict, List
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.micr_analyzer import MICRAnalyzer
from core.validator import MICRValidator
from utils.image_utils import ImageProcessor
from models.micr_models import MICRResult

class BatchMICRProcessor:
    """Processeur MICR pour le traitement en lot"""
    
    def __init__(self, api_key: str = None):
        """
        Initialise le processeur de lot
        
        Args:
            api_key: Clé API OpenAI
        """
        self.analyzer = MICRAnalyzer(api_key)
        self.validator = MICRValidator()
        self.image_processor = ImageProcessor()
        
    def process_folder(self, folder_path: str, output_dir: str = None) -> Dict[str, MICRResult]:
        """
        Traite tous les chèques d'un dossier
        
        Args:
            folder_path: Chemin du dossier contenant les images
            output_dir: Dossier de sortie pour les rapports
            
        Returns:
            Dictionnaire {nom_fichier: résultat_micr}
        """
        if not os.path.exists(folder_path):
            raise ValueError(f"Dossier non trouvé: {folder_path}")
        
        # Créer le dossier de sortie si nécessaire
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.join(folder_path, "micr_results")
            os.makedirs(output_dir, exist_ok=True)
        
        # Trouver toutes les images
        image_files = self._find_image_files(folder_path)
        
        if not image_files:
            print(f"❌ Aucune image trouvée dans {folder_path}")
            return {}
        
        print(f"📁 Dossier: {folder_path}")
        print(f"📊 {len(image_files)} images trouvées")
        print(f"📤 Résultats dans: {output_dir}")
        print("=" * 60)
        
        # Traiter chaque image
        results = {}
        success_count = 0
        start_time = time.time()
        
        for i, image_file in enumerate(image_files, 1):
            print(f"\n[{i}/{len(image_files)}] {os.path.basename(image_file)}")
            
            try:
                # Analyser l'image
                result = self.analyzer.analyze_micr(image_file)
                results[image_file] = result
                
                if result.success:
                    success_count += 1
                    status = "✅ SUCCÈS"
                    confidence = result.get_overall_confidence()
                    print(f"  {status} - Confiance: {confidence:.1%}")
                else:
                    status = "❌ ÉCHEC"
                    print(f"  {status} - {result.error_message}")
                
                # Progression
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(image_files) - i) * avg_time
                print(f"  ⏱️  {result.processing_time:.1f}s (reste ~{remaining/60:.1f}min)")
                
            except Exception as e:
                print(f"  ❌ ERREUR: {e}")
                # Créer un résultat d'erreur
                results[image_file] = MICRResult(
                    raw_line="", raw_confidence=0.0, success=False,
                    error_message=str(e), image_path=image_file
                )
        
        # Résumé final
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DU TRAITEMENT EN LOT")
        print("=" * 60)
        print(f"✅ Réussis: {success_count}/{len(image_files)} ({success_count/len(image_files):.1%})")
        print(f"⏱️  Temps total: {total_time/60:.1f} minutes")
        print(f"📈 Temps moyen: {total_time/len(image_files):.1f}s par image")
        
        # Sauvegarder les résultats
        self._save_results(results, output_dir)
        
        return results
    
    def _find_image_files(self, folder_path: str) -> List[str]:
        """Trouve tous les fichiers d'image dans un dossier"""
        image_files = []
        supported_formats = self.image_processor.get_supported_formats()
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in supported_formats:
                    image_files.append(file_path)
        
        return sorted(image_files)
    
    def _save_results(self, results: Dict[str, MICRResult], output_dir: str):
        """Sauvegarde les résultats dans différents formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Rapport CSV détaillé
        csv_path = os.path.join(output_dir, f"micr_results_{timestamp}.csv")
        self.export_to_csv(results, csv_path)
        
        # 2. Rapport JSON complet
        json_path = os.path.join(output_dir, f"micr_results_{timestamp}.json")
        self.export_to_json(results, json_path)
        
        # 3. Rapport texte lisible
        txt_path = os.path.join(output_dir, f"micr_report_{timestamp}.txt")
        self.export_to_text_report(results, txt_path)
        
        print(f"\n📄 Rapports générés:")
        print(f"  📊 CSV: {csv_path}")
        print(f"  🔧 JSON: {json_path}")
        print(f"  📝 Texte: {txt_path}")
    
    def export_to_csv(self, results: Dict[str, MICRResult], csv_path: str):
        """Exporte les résultats en CSV"""
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'filename', 'success', 'raw_line', 'overall_confidence',
                'transit_number', 'transit_confidence', 'transit_valid',
                'institution_number', 'institution_confidence', 'institution_valid', 'bank_name',
                'account_number', 'account_confidence', 'account_valid',
                'cheque_number', 'cheque_confidence',
                'processing_time', 'error_message'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for image_path, result in results.items():
                filename = os.path.basename(image_path)
                validations = self.validator.validate_canadian_micr(result)
                
                # Nom de la banque
                bank_name = ""
                if result.institution_number and result.institution_number.value:
                    bank_name = self.validator.get_institution_name(result.institution_number.value)
                
                row = {
                    'filename': filename,
                    'success': result.success,
                    'raw_line': result.raw_line,
                    'overall_confidence': f"{result.get_overall_confidence():.3f}" if result.success else "0.000",
                    'transit_number': result.transit_number.value if result.transit_number else "",
                    'transit_confidence': f"{result.transit_number.combined_confidence:.3f}" if result.transit_number else "",
                    'transit_valid': validations.transit_valid if result.success else False,
                    'institution_number': result.institution_number.value if result.institution_number else "",
                    'institution_confidence': f"{result.institution_number.combined_confidence:.3f}" if result.institution_number else "",
                    'institution_valid': validations.institution_valid if result.success else False,
                    'bank_name': bank_name,
                    'account_number': result.account_number.value if result.account_number else "",
                    'account_confidence': f"{result.account_number.combined_confidence:.3f}" if result.account_number else "",
                    'account_valid': validations.account_valid if result.success else False,
                    'cheque_number': result.cheque_number.value if result.cheque_number else "",
                    'cheque_confidence': f"{result.cheque_number.combined_confidence:.3f}" if result.cheque_number else "",
                    'processing_time': f"{result.processing_time:.2f}" if result.processing_time else "",
                    'error_message': result.error_message or ""
                }
                
                writer.writerow(row)
    
    def export_to_json(self, results: Dict[str, MICRResult], json_path: str):
        """Exporte les résultats en JSON"""
        json_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_images': len(results),
                'successful_analyses': sum(1 for r in results.values() if r.success),
                'version': '1.0'
            },
            'results': {}
        }
        
        for image_path, result in results.items():
            filename = os.path.basename(image_path)
            validations = self.validator.validate_canadian_micr(result)
            
            json_data['results'][filename] = {
                'micr_result': result.to_dict(),
                'validation': validations.to_dict()
            }
        
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
    
    def export_to_text_report(self, results: Dict[str, MICRResult], txt_path: str):
        """Génère un rapport texte lisible"""
        with open(txt_path, 'w', encoding='utf-8') as txtfile:
            txtfile.write("RAPPORT D'ANALYSE MICR - TRAITEMENT EN LOT\n")
            txtfile.write("=" * 60 + "\n")
            txtfile.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            txtfile.write(f"Images traitées: {len(results)}\n")
            
            successful = sum(1 for r in results.values() if r.success)
            txtfile.write(f"Analyses réussies: {successful}/{len(results)} ({successful/len(results):.1%})\n")
            txtfile.write("\n")
            
            # Statistiques par banque
            bank_stats = {}
            for result in results.values():
                if result.success and result.institution_number:
                    bank_code = result.institution_number.value
                    bank_name = self.validator.get_institution_name(bank_code)
                    bank_stats[bank_name] = bank_stats.get(bank_name, 0) + 1
            
            if bank_stats:
                txtfile.write("RÉPARTITION PAR BANQUE:\n")
                txtfile.write("-" * 30 + "\n")
                for bank, count in sorted(bank_stats.items(), key=lambda x: x[1], reverse=True):
                    txtfile.write(f"{bank}: {count} chèque(s)\n")
                txtfile.write("\n")
            
            # Détails par fichier
            txtfile.write("DÉTAILS PAR FICHIER:\n")
            txtfile.write("-" * 30 + "\n")
            
            for image_path, result in results.items():
                filename = os.path.basename(image_path)
                txtfile.write(f"\n📁 {filename}\n")
                
                if result.success:
                    txtfile.write(f"✅ Statut: SUCCÈS\n")
                    txtfile.write(f"🎯 Confiance: {result.get_overall_confidence():.1%}\n")
                    txtfile.write(f"📝 MICR: {result.raw_line}\n")
                    
                    if result.transit_number:
                        txtfile.write(f"🏦 Transit: {result.transit_number.value} ({result.transit_number.combined_confidence:.1%})\n")
                    
                    if result.institution_number:
                        bank_name = self.validator.get_institution_name(result.institution_number.value)
                        txtfile.write(f"🏢 Institution: {result.institution_number.value} - {bank_name} ({result.institution_number.combined_confidence:.1%})\n")
                    
                    if result.account_number:
                        txtfile.write(f"👤 Compte: {result.account_number.value} ({result.account_number.combined_confidence:.1%})\n")
                    
                    if result.cheque_number:
                        txtfile.write(f"📄 Chèque: {result.cheque_number.value} ({result.cheque_number.combined_confidence:.1%})\n")
                else:
                    txtfile.write(f"❌ Statut: ÉCHEC\n")
                    txtfile.write(f"💬 Erreur: {result.error_message}\n")
                
                if result.processing_time:
                    txtfile.write(f"⏱️  Temps: {result.processing_time:.1f}s\n")
    
    def generate_statistics(self, results: Dict[str, MICRResult]) -> dict:
        """Génère des statistiques détaillées"""
        stats = {
            'total_images': len(results),
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_confidence': 0.0,
            'average_processing_time': 0.0,
            'bank_distribution': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'validation_errors': []
        }
        
        confidences = []
        processing_times = []
        
        for result in results.values():
            if result.success:
                stats['successful_analyses'] += 1
                
                # Confiance
                confidence = result.get_overall_confidence()
                confidences.append(confidence)
                
                # Distribution de confiance
                if confidence >= 0.8:
                    stats['confidence_distribution']['high'] += 1
                elif confidence >= 0.6:
                    stats['confidence_distribution']['medium'] += 1
                else:
                    stats['confidence_distribution']['low'] += 1
                
                # Distribution par banque
                if result.institution_number:
                    bank_name = self.validator.get_institution_name(result.institution_number.value)
                    stats['bank_distribution'][bank_name] = stats['bank_distribution'].get(bank_name, 0) + 1
                
                # Validation
                validations = self.validator.validate_canadian_micr(result)
                if validations.errors:
                    stats['validation_errors'].extend(validations.errors)
            else:
                stats['failed_analyses'] += 1
            
            # Temps de traitement
            if result.processing_time:
                processing_times.append(result.processing_time)
        
        # Moyennes
        if confidences:
            stats['average_confidence'] = sum(confidences) / len(confidences)
        
        if processing_times:
            stats['average_processing_time'] = sum(processing_times) / len(processing_times)
        
        return stats

def main():
    """Fonction principale pour le traitement en lot"""
    
    # Configuration
    FOLDER_PATH = "cheques_a_traiter"  # Modifiez ce chemin
    OUTPUT_DIR = "resultats_micr"      # Dossier de sortie
    
    print("🏭 TRAITEMENT EN LOT - MICR READER")
    print("=" * 60)
    
    # Vérifier que le dossier existe
    if not os.path.exists(FOLDER_PATH):
        print(f"❌ Dossier non trouvé: {FOLDER_PATH}")
        print("💡 Créez un dossier et placez-y vos images de chèques")
        
        # Créer un exemple de structure
        print("\n📁 Création d'un exemple de structure...")
        os.makedirs(FOLDER_PATH, exist_ok=True)
        print(f"✅ Dossier créé: {FOLDER_PATH}")
        print("   Placez vos images de chèques dans ce dossier et relancez le script")
        return
    
    try:
        # Initialiser le processeur
        processor = BatchMICRProcessor()
        
        # Traiter le dossier
        results = processor.process_folder(FOLDER_PATH, OUTPUT_DIR)
        
        if results:
            # Générer des statistiques
            stats = processor.generate_statistics(results)
            
            print("\n📈 STATISTIQUES DÉTAILLÉES")
            print("=" * 40)
            print(f"Taux de réussite: {stats['successful_analyses']}/{stats['total_images']} ({stats['successful_analyses']/stats['total_images']:.1%})")
            print(f"Confiance moyenne: {stats['average_confidence']:.1%}")
            print(f"Temps moyen: {stats['average_processing_time']:.1f}s")
            
            if stats['bank_distribution']:
                print(f"\nRépartition par banque:")
                for bank, count in sorted(stats['bank_distribution'].items(), key=lambda x: x[1], reverse=True):
                    print(f"  {bank}: {count}")
            
            conf_dist = stats['confidence_distribution']
            print(f"\nDistribution de confiance:")
            print(f"  Élevée (≥80%): {conf_dist['high']}")
            print(f"  Moyenne (60-79%): {conf_dist['medium']}")
            print(f"  Faible (<60%): {conf_dist['low']}")
            
        print(f"\n🎉 TRAITEMENT TERMINÉ")
        print(f"📁 Résultats dans: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du traitement: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
