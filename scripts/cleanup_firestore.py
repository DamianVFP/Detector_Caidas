#!/usr/bin/env python3
"""
Script para limpiar documentos de prueba en Firestore.

Uso:
    python scripts/cleanup_firestore.py --collection Prueba_Alertas --query "event_type==fall" --dry-run

Este script es CRÍTICO después de ejecutar v1.0 (frame-by-frame logging) que
crea miles de documentos innecesarios.

IMPORTANTE: Requiere GOOGLE_APPLICATION_CREDENTIALS configurada.
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Agregar raíz del proyecto al path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import firebase_admin
    from firebase_admin import credentials
    from firebase_admin import firestore
except ImportError:
    print("ERROR: firebase-admin no está instalado. Instala con:")
    print("  pip install firebase-admin")
    sys.exit(1)

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


class FirestoreCleanup:
    """Herramienta para limpiar documentos de prueba en Firestore."""

    def __init__(self, collection: str):
        self.collection_name = collection
        self.db = None
        self._init_firebase()

    def _init_firebase(self) -> None:
        """Inicializa Firebase Admin SDK usando GOOGLE_APPLICATION_CREDENTIALS."""
        if firebase_admin._apps:
            self.db = firestore.client()
            LOG.info("✓ Firebase ya inicializado")
            return

        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            LOG.info("✓ Firebase inicializado con GOOGLE_APPLICATION_CREDENTIALS")
        except Exception as e:
            LOG.error("✗ Error inicializando Firebase: %s", e)
            LOG.error("Asegúrate de establecer GOOGLE_APPLICATION_CREDENTIALS")
            raise

    def count_documents(self, filter_str: Optional[str] = None) -> int:
        """Cuenta documentos en la colección (con filtro opcional)."""
        query = self.db.collection(self.collection_name)
        
        if filter_str:
            # Parsing simple: "field==value" o "field<value"
            # Para filtros más complejos, refactoriza esta lógica
            if "==" in filter_str:
                field, value = filter_str.split("==")
                field = field.strip()
                value = value.strip()
                # Intentar parsear como número
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass  # Es string
                query = query.where(field, "==", value)
            elif "<" in filter_str:
                field, value = filter_str.split("<")
                field = field.strip()
                value = float(value.strip())
                query = query.where(field, "<", value)

        docs = list(query.stream())
        return len(docs)

    def delete_documents(self, filter_str: Optional[str] = None, dry_run: bool = True, batch_size: int = 500) -> int:
        """Elimina documentos (con filtro opcional)."""
        query = self.db.collection(self.collection_name)
        
        if filter_str:
            if "==" in filter_str:
                field, value = filter_str.split("==")
                field = field.strip()
                value = value.strip()
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass
                query = query.where(field, "==", value)
            elif "<" in filter_str:
                field, value = filter_str.split("<")
                field = field.strip()
                value = float(value.strip())
                query = query.where(field, "<", value)

        docs = list(query.stream())
        deleted_count = 0

        if dry_run:
            LOG.info("DRY RUN: Se eliminarían %d documentos", len(docs))
            for doc in docs[:10]:  # Mostrar primeros 10
                LOG.info("  - %s", doc.to_dict())
            if len(docs) > 10:
                LOG.info("  ... y %d más", len(docs) - 10)
            return len(docs)

        # Eliminar en batches
        batch = self.db.batch()
        for idx, doc in enumerate(docs):
            batch.delete(doc.reference)
            if (idx + 1) % batch_size == 0:
                LOG.info("Eliminando lote %d/%d (%d documentos)...", 
                        (idx + 1) // batch_size, (len(docs) + batch_size - 1) // batch_size, batch_size)
                batch.commit()
                batch = self.db.batch()
                deleted_count = idx + 1

        # Commit del último lote
        if len(docs) % batch_size != 0:
            batch.commit()
            deleted_count = len(docs)

        LOG.info("✓ %d documentos eliminados", deleted_count)
        return deleted_count

    def export_documents(self, output_file: str, filter_str: Optional[str] = None) -> int:
        """Exporta documentos a JSON antes de eliminar."""
        query = self.db.collection(self.collection_name)
        
        if filter_str:
            if "==" in filter_str:
                field, value = filter_str.split("==")
                field = field.strip()
                value = value.strip()
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass
                query = query.where(field, "==", value)

        docs = list(query.stream())
        exported_docs = [
            {
                "id": doc.id,
                "timestamp": doc.create_time.isoformat() if doc.create_time else None,
                "data": doc.to_dict()
            }
            for doc in docs
        ]

        try:
            with open(output_file, "w", encoding="utf-8") as fh:
                json.dump(exported_docs, fh, indent=2, ensure_ascii=False, default=str)
            LOG.info("✓ %d documentos exportados a %s", len(exported_docs), output_file)
            return len(exported_docs)
        except Exception as e:
            LOG.error("✗ Error exportando: %s", e)
            return 0


def main():
    parser = argparse.ArgumentParser(
        description="Limpiar documentos de prueba en Firestore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ver cuántos documentos hay en la colección
  python scripts/cleanup_firestore.py --count

  # Ver cuántos documentos de tipo "fall"
  python scripts/cleanup_firestore.py --count --query "event_type==fall"

  # Exportar antes de eliminar (RECOMENDADO)
  python scripts/cleanup_firestore.py --export backup.json

  # Eliminar documentos de prueba (DRY RUN)
  python scripts/cleanup_firestore.py --delete --query "event_type==fall" --dry-run

  # Eliminar documentos de prueba (REAL)
  python scripts/cleanup_firestore.py --delete --query "event_type==fall"
        """
    )
    
    parser.add_argument("--collection", default=config.FIRESTORE_COLLECTION,
                       help=f"Colección Firestore (default: {config.FIRESTORE_COLLECTION})")
    parser.add_argument("--query", help="Filtro: 'field==value' o 'field<value'")
    parser.add_argument("--count", action="store_true", help="Contar documentos")
    parser.add_argument("--export", help="Exportar documentos a JSON antes de eliminar")
    parser.add_argument("--delete", action="store_true", help="Eliminar documentos")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Simulación sin eliminar (default: True)")
    parser.add_argument("--force", action="store_true", help="Eliminar sin confirmación (--dry-run se ignora)")

    args = parser.parse_args()

    try:
        cleanup = FirestoreCleanup(collection=args.collection)

        if args.count:
            count = cleanup.count_documents(filter_str=args.query)
            print(f"\n{'='*60}")
            print(f"Colección: {args.collection}")
            if args.query:
                print(f"Filtro: {args.query}")
            print(f"Documentos: {count:,}")
            print(f"{'='*60}\n")

        if args.export:
            exported = cleanup.export_documents(args.export, filter_str=args.query)
            print(f"\n✓ Backup guardado en: {args.export}\n")

        if args.delete:
            count = cleanup.count_documents(filter_str=args.query)
            
            if count == 0:
                LOG.info("No hay documentos para eliminar")
                return

            dry_run = not args.force
            
            if dry_run:
                LOG.info("MODO DRY RUN: Los cambios NO se aplicarán")
                cleanup.delete_documents(filter_str=args.query, dry_run=True)
                print(f"\n{'='*60}")
                print("Para eliminar REALMENTE, ejecuta:")
                print(f"  python scripts/cleanup_firestore.py --delete --force --query \"{args.query or 'sin_filtro'}\"")
                print(f"{'='*60}\n")
            else:
                confirmation = input(f"¿Eliminar {count:,} documentos? (s/N): ")
                if confirmation.lower() == 's':
                    deleted = cleanup.delete_documents(filter_str=args.query, dry_run=False)
                    print(f"\n✓ {deleted:,} documentos eliminados\n")
                else:
                    LOG.info("Operación cancelada")

    except Exception as e:
        LOG.exception("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
