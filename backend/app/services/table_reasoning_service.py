"""
Universal spreadsheet/table reasoning service.
Handles XLSX/CSV ingestion, schema inference, deterministic query execution.
"""
import os
import json
import re
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from decimal import Decimal

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from langchain_core.messages import HumanMessage, SystemMessage

from .vector_store import get_vector_store
from .rag_service import get_rag_service
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TableHit:
    """Represents a retrieved table sheet."""
    document_id: str
    filename: str
    sheet_name: str
    parquet_path: str
    schema_path: str
    score: float


class TableReasoningService:
    """
    Universal table reasoning service for XLSX/CSV files.
    
    Features:
    - Schema-based ingestion (parquet + JSON schema)
    - Semantic sheet retrieval via schema embeddings
    - Deterministic pandas execution
    - Common sense rules (age mapping, LA filtering, etc.)
    - Validation and provenance tracking
    """
    
    def __init__(self):
        """Initialize table reasoning service."""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas is required for table reasoning. Install with: pip install pandas pyarrow")
        
        self.vector_store = get_vector_store()
        self.rag_service = get_rag_service()
        self.storage_base = Path(settings.DATA_DIR) / "tables"
        self.storage_base.mkdir(parents=True, exist_ok=True)
        logger.info("✅ TableReasoningService initialized")
    
    def should_use_table(self, query: str, has_tabular_uploads: bool) -> bool:
        """
        Determine if query should use table reasoning.
        
        Args:
            query: User query
            has_tabular_uploads: Whether user has uploaded XLSX/CSV files
            
        Returns:
            True if table reasoning should be used
        """
        if not has_tabular_uploads:
            return False
        
        q = query.lower()
        triggers = [
            "fee", "rate", "price", "£", "per week", "weekly", "age", "year old",
            "band", "standard", "enhanced", "complex", "total", "sum", "percentage",
            "%", "amount", "cost", "charge", "payment", "la fee", "carer fee",
            "local authority", "council", "tier", "level"
        ]
        return any(t in q for t in triggers)
    
    def ingest_xlsx(self, business_id: str, document_id: str, filename: str, filepath: str) -> Dict[str, Any]:
        """
        Ingest XLSX file into structured table storage.
        
        Args:
            business_id: Business identifier
            document_id: Document identifier
            filename: Original filename
            filepath: Path to XLSX file
            
        Returns:
            Dict with ingestion results
        """
        xls = None
        try:
            logger.info(f"📊 TABLE INGESTION START: {filename} (business_id='{business_id}', document_id='{document_id}')")
            
            # Verify file exists and is readable
            if not os.path.exists(filepath):
                logger.error(f"❌ TABLE INGESTION FAILED: File does not exist: {filepath}")
                return {
                    "success": False,
                    "error": f"File not found: {filepath}",
                    "sheets_ingested": 0
                }
            
            file_size = os.path.getsize(filepath)
            logger.info(f"📊 File exists: {filepath} ({file_size} bytes)")
            
            # Open Excel file - CRITICAL: Must be closed explicitly
            logger.info(f"📊 Opening Excel file with openpyxl engine...")
            xls = pd.ExcelFile(filepath, engine='openpyxl')
            logger.info(f"📊 Excel file opened. Sheet names: {xls.sheet_names}")
            ingested_sheets = []
            
            try:
                for sheet_name in xls.sheet_names:
                    try:
                        # Read raw to detect header
                        df_raw = xls.parse(sheet_name, header=None)
                        
                        # ✅ Extract coverage from RAW sheet (pre-header) so LA lists aren't lost
                        coverage_from_raw = self._extract_coverage_entities_from_raw(df_raw)
                        
                        header_row = self._detect_header_row(df_raw)
                        
                        # Read with detected header
                        df = xls.parse(sheet_name, header=header_row)
                        df = self._normalize_columns(df)
                        
                        # Skip empty sheets
                        if len(df) == 0:
                            logger.warning(f"   ⚠️  Sheet '{sheet_name}' is empty, skipping")
                            continue
                        
                        # Infer schema (includes coverage_entities extraction)
                        logger.info(f"   🔍 Inferring schema for sheet '{sheet_name}' ({len(df)} rows, {len(df.columns)} cols)...")
                        schema = self._infer_schema(df, filename, sheet_name)
                        
                        # Merge raw coverage into schema coverage
                        schema_cov = set(schema.get("coverage_entities", []) or [])
                        schema_cov.update(coverage_from_raw or [])
                        schema["coverage_entities"] = sorted(list(schema_cov))[:200]
                        
                        coverage_entities = schema.get("coverage_entities", [])
                        coverage_count = len(coverage_entities)
                        logger.info(f"   ✅ Schema inferred: {len(schema['columns'])} columns, {coverage_count} coverage entities (merged from raw + processed)")
                        if coverage_entities:
                            logger.info(f"   📋 Coverage entities ({len(coverage_entities)} total): {coverage_entities[:20]}")
                            # CRITICAL: Check if "Redbridge" is in the list (for debugging)
                            if any("redbridge" in str(e).lower() for e in coverage_entities):
                                logger.info(f"   ✅ 'Redbridge' FOUND in coverage entities!")
                            else:
                                logger.warning(f"   ⚠️  'Redbridge' NOT found in coverage entities (check extraction logic)")
                        else:
                            logger.error(f"   ❌ NO coverage entities extracted from sheet '{sheet_name}' - this WILL cause entity matching to fail!")
                        
                        # Create storage directory
                        base_dir = self.storage_base / business_id / document_id
                        base_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"   💾 Storage directory: {base_dir}")
                        
                        # Safe filename for storage
                        safe_sheet = self._safe_name(sheet_name)
                        parquet_path = base_dir / f"{safe_sheet}.parquet"
                        schema_path = base_dir / f"{safe_sheet}.schema.json"
                        
                        # Save parquet and schema
                        logger.info(f"   💾 Saving parquet: {parquet_path}")
                        df.to_parquet(str(parquet_path), index=False)
                        logger.info(f"   💾 Saving schema: {schema_path}")
                        with open(schema_path, "w", encoding="utf-8") as f:
                            json.dump(schema, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"   ✅ Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} cols, {coverage_count} entities → {parquet_path}")
                        
                        # Index schema embedding (includes coverage entities)
                        embed_text = self._schema_to_embed_text(schema)
                        logger.info(f"   🔍 Indexing schema embedding for sheet '{sheet_name}' in vector store...")
                        self.vector_store.upsert_table_sheet(
                            business_id=business_id,
                            text=embed_text,
                            metadata={
                                "document_id": document_id,
                                "filename": filename,
                                "sheet_name": sheet_name,
                                "parquet_path": str(parquet_path),
                                "schema_path": str(schema_path),
                            }
                        )
                        logger.info(f"   ✅ Schema indexed in vector store for business_id='{business_id}'")
                        
                        ingested_sheets.append({
                            "sheet_name": sheet_name,
                            "row_count": len(df),
                            "col_count": len(df.columns),
                            "parquet_path": str(parquet_path),
                            "schema_path": str(schema_path)
                        })
                        
                    except Exception as e:
                        logger.error(f"   ❌ Error processing sheet '{sheet_name}': {e}", exc_info=True)
                        continue
                
                logger.info(f"✅ TABLE INGESTION COMPLETE: {len(ingested_sheets)} sheets ingested from {filename} for business_id='{business_id}'")
                # Log coverage entities summary
                total_entities = 0
                for sheet_info in ingested_sheets:
                    schema_path = sheet_info.get("schema_path")
                    if schema_path and os.path.exists(schema_path):
                        try:
                            with open(schema_path, "r", encoding="utf-8") as f:
                                schema = json.load(f)
                                entities = schema.get("coverage_entities", [])
                                total_entities += len(entities)
                                logger.info(f"   📋 Sheet '{sheet_info['sheet_name']}': {len(entities)} coverage entities")
                        except:
                            pass
                logger.info(f"✅ Total coverage entities extracted: {total_entities}")
                return {
                    "success": True,
                    "sheets_ingested": len(ingested_sheets),
                    "sheets": ingested_sheets
                }
            finally:
                # CRITICAL: Close ExcelFile to release file handle
                if xls is not None:
                    try:
                        xls.close()
                        logger.debug(f"✅ Closed ExcelFile handle for {filename}")
                    except Exception as e:
                        logger.warning(f"Could not close ExcelFile: {e}")
            
        except Exception as e:
            logger.error(f"❌ TABLE INGESTION FAILED for {filename}: {e}", exc_info=True)
            # Ensure file is closed even on error
            if xls is not None:
                try:
                    xls.close()
                    logger.debug(f"✅ Closed ExcelFile handle after error")
                except:
                    pass
            return {
                "success": False,
                "error": str(e),
                "sheets_ingested": 0
            }
    
    def ingest_csv(self, business_id: str, document_id: str, filename: str, filepath: str) -> Dict[str, Any]:
        """
        Ingest CSV file into structured table storage.
        
        Args:
            business_id: Business identifier
            document_id: Document identifier
            filename: Original filename
            filepath: Path to CSV file
            
        Returns:
            Dict with ingestion results
        """
        try:
            logger.info(f"📊 Ingesting CSV: {filename} (business_id={business_id}, document_id={document_id})")
            
            # Read CSV
            df_raw = pd.read_csv(filepath, header=None, nrows=20)
            header_row = self._detect_header_row(df_raw)
            
            df = pd.read_csv(filepath, header=header_row)
            df = self._normalize_columns(df)
            
            if len(df) == 0:
                logger.warning(f"   ⚠️  CSV '{filename}' is empty")
                return {"success": False, "error": "Empty CSV", "sheets_ingested": 0}
            
            # Infer schema
            schema = self._infer_schema(df, filename, "Sheet1")
            
            # Create storage directory
            base_dir = self.storage_base / business_id / document_id
            base_dir.mkdir(parents=True, exist_ok=True)
            
            safe_name = self._safe_name(filename.replace(".csv", ""))
            parquet_path = base_dir / f"{safe_name}.parquet"
            schema_path = base_dir / f"{safe_name}.schema.json"
            
            # Save parquet and schema
            df.to_parquet(str(parquet_path), index=False)
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            
            logger.info(f"   ✅ CSV: {len(df)} rows, {len(df.columns)} cols → {parquet_path}")
            
            # Index schema embedding
            embed_text = self._schema_to_embed_text(schema)
            self.vector_store.upsert_table_sheet(
                business_id=business_id,
                text=embed_text,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "sheet_name": "Sheet1",
                    "parquet_path": str(parquet_path),
                    "schema_path": str(schema_path),
                }
            )
            
            return {
                "success": True,
                "sheets_ingested": 1,
                "sheets": [{
                    "sheet_name": "Sheet1",
                    "row_count": len(df),
                    "col_count": len(df.columns),
                    "parquet_path": str(parquet_path),
                    "schema_path": str(schema_path)
                }]
            }
            
        except Exception as e:
            logger.error(f"❌ Error ingesting CSV {filename}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "sheets_ingested": 0
            }
    
    def _normalize_entity_name(self, entity: str) -> str:
        """
        Normalize entity name by stripping suffixes like "LA", "Local Authority", etc.
        Also handles common variations.
        """
        if not entity:
            return entity
        
        entity = entity.strip()
        # Remove common suffixes (case-insensitive)
        suffixes = [" la", " local authority", " council", " borough", " county", " authority"]
        for suffix in suffixes:
            if entity.lower().endswith(suffix):
                entity = entity[:-len(suffix)].strip()
        
        # Remove punctuation
        entity = re.sub(r'[^\w\s]', '', entity)
        
        return entity.strip()
    
    def _extract_entity_from_query(self, query: str) -> Optional[str]:
        """
        Extract entity (LA/council name) from query.
        FIXED: More robust patterns, fuzzy normalization, and better fallback logic.
        """
        if not query:
            return None
        
        # Pattern 1: "from Redbridge" or "for Redbridge" (case-insensitive)
        patterns = [
            r"(?:from|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:LA|local authority|council)?",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:LA|local authority|council)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:borough|county|authority)",
            # More flexible: "Redbridge" anywhere before "LA"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:LA|council|borough)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entity = match.group(1).strip()
                if len(entity) > 2:
                    # ✅ Normalize entity name (strip "LA", etc.)
                    entity = self._normalize_entity_name(entity)
                    logger.info(f"🔍 Extracted entity from query (pattern): '{entity}'")
                    return entity
        
        # Fallback 1: Look for capitalized words before "LA", "Council", etc.
        words = query.split()
        for i, word in enumerate(words):
            # Check if word is capitalized and might be an LA name
            if word and word[0].isupper() and len(word) >= 4:
                word_lower = word.lower()
                # Skip common words
                if word_lower not in ["from", "the", "for", "and", "with", "this", "that", "what", "which", "local", "authority", "standard", "enhanced", "complex"]:
                    # Check if next word is "LA", "Council", etc.
                    if i + 1 < len(words):
                        next_word = words[i + 1].lower()
                        if next_word in ["la", "council", "borough", "authority"]:
                            entity = self._normalize_entity_name(word)
                            logger.info(f"🔍 Extracted entity from query (fallback 1): '{entity}'")
                            return entity
        
        # Fallback 2: Look for capitalized words after "from" or "for"
        for i, word in enumerate(words):
            word_lower = word.lower()
            if word_lower in ["from", "for"] and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word and next_word[0].isupper() and len(next_word) >= 4:
                    next_lower = next_word.lower()
                    if next_lower not in ["the", "local", "authority", "standard", "enhanced"]:
                        entity = self._normalize_entity_name(next_word)
                        logger.info(f"🔍 Extracted entity from query (fallback 2): '{entity}'")
                        return entity
        
        logger.warning(f"🔍 No entity extracted from query: '{query[:100]}'")
        return None
    
    def _normalize_entity(self, s: str) -> str:
        """Normalize entity name for matching (strip common suffixes/prefixes)."""
        if not s:
            return ""
        s = s.strip().lower()
        # common suffixes/prefixes users add
        for junk in [" local authority", " la", " council", " borough", " london borough of", " city of"]:
            s = s.replace(junk, "")
        return " ".join(s.split())
    
    def _sheet_contains_entity_fallback(self, df: pd.DataFrame, entity: str) -> bool:
        """
        Robust fallback: scan a reasonable slice of the sheet for the entity
        (works even when coverage_entities extraction missed it).
        """
        ent = self._normalize_entity(entity)
        if not ent:
            return False

        # limit scan to avoid huge cost; still covers most real spreadsheets
        max_rows = min(len(df), 2500)
        max_cols = min(len(df.columns), 60)
        sub = df.iloc[:max_rows, :max_cols].astype(str)

        # normalize cell strings lightly for matching
        hay = sub.applymap(lambda x: self._normalize_entity(x))
        return hay.apply(lambda col: col.str.contains(ent, na=False)).any().any()
    
    def _fuzzy_match_entity(self, entity: str, coverage_list: List[str], threshold: float = 0.5) -> Tuple[bool, List[str], Optional[str]]:
        """
        Match entity against coverage list with fuzzy normalization and typo handling.
        FIXED: Now does exact case-insensitive matching FIRST, then fuzzy matching.
        Returns: (matched, matches, suggestion)
        """
        from difflib import get_close_matches
        
        if not entity or not coverage_list:
            return False, [], None
        
        # ✅ Normalize entity (strip "LA", etc.)
        entity_normalized = self._normalize_entity_name(entity)
        entity_lower = entity_normalized.lower().strip()
        
        # Normalize coverage list too
        coverage_normalized = [self._normalize_entity_name(c) if c else "" for c in coverage_list]
        coverage_lower = [c.lower().strip() if c else "" for c in coverage_normalized]
        
        # ✅ STEP 1: Exact case-insensitive match (most reliable)
        exact_matches = []
        for i, cov_lower in enumerate(coverage_lower):
            if cov_lower == entity_lower:
                exact_matches.append(coverage_list[i])
        
        if exact_matches:
            logger.info(f"   ✅ EXACT match found: '{entity_normalized}' = '{exact_matches[0]}'")
            return True, exact_matches, None
        
        # ✅ STEP 2: Substring match (entity contained in coverage or vice versa)
        substring_matches = []
        for i, cov_lower in enumerate(coverage_lower):
            if entity_lower in cov_lower or cov_lower in entity_lower:
                substring_matches.append(coverage_list[i])
        
        if substring_matches:
            logger.info(f"   ✅ SUBSTRING match found: '{entity_normalized}' in '{substring_matches[0]}'")
            return True, substring_matches, None
        
        # ✅ STEP 3: Fuzzy match with typo handling (lowered threshold to 0.4 for typos like "Rainbridge")
        matches = get_close_matches(entity_lower, coverage_lower, n=5, cutoff=0.4)
        
        if matches:
            # Return original case matches
            original_matches = []
            for m in matches:
                for i, c in enumerate(coverage_list):
                    if coverage_normalized[i] and coverage_normalized[i].lower().strip() == m:
                        original_matches.append(c)
                        break
            
            # If fuzzy match is close but not exact, suggest correction
            best_match = original_matches[0] if original_matches else None
            if best_match and best_match.lower() != entity_lower:
                suggestion = f"Did you mean: {best_match}?"
                logger.info(f"   ✅ FUZZY match found: '{entity_normalized}' ≈ '{best_match}' (typo correction)")
                return True, original_matches, suggestion
            
            logger.info(f"   ✅ FUZZY match found: '{entity_normalized}' ≈ '{original_matches[0]}'")
            return True, original_matches, None
        
        logger.warning(f"   ❌ NO match found for '{entity_normalized}' in coverage list: {coverage_list[:10]}")
        return False, [], None
    
    def retrieve_relevant_sheets(self, business_id: str, query: str, k: int = 6) -> List[TableHit]:
        """
        Retrieve relevant table sheets using schema embeddings.
        FIXED: Two-pass ranking - coverage-matched sheets prioritized over similarity-only matches.
        
        Args:
            business_id: Business identifier
            query: User query
            k: Number of sheets to retrieve
            
        Returns:
            List of TableHit objects (coverage-matched first, then fallback)
        """
        try:
            # Extract entity from query
            entity = self._extract_entity_from_query(query)
            logger.info(f"🔍 Entity extraction result: '{entity}' from query: '{query[:100]}'")
            
            # ✅ FIX: Retrieve more candidate sheets (k * 6) to ensure we find coverage matches
            results = self.vector_store.search_table_sheets(business_id=business_id, query=query, k=k * 6) or []
            logger.info(f"📊 Retrieved {len(results)} candidate sheets from vector store")
            
            # ✅ FIX: Two-pass ranking - collect all, then prioritize
            matched_hits: List[TableHit] = []  # Sheets with coverage match
            unknown_hits: List[TableHit] = []  # Sheets with no coverage data
            plain_hits: List[TableHit] = []    # Sheets when no entity in query
            
            for r in results:
                md = r.get("metadata") or {}
                hit = TableHit(
                    document_id=md.get("document_id", ""),
                    filename=md.get("filename", ""),
                    sheet_name=md.get("sheet_name", ""),
                    parquet_path=md.get("parquet_path", ""),
                    schema_path=md.get("schema_path", ""),
                    score=float(r.get("score", 0.0))
                )
                
                # If no entity in query, collect all sheets
                if not entity:
                    plain_hits.append(hit)
                    continue
                
                # If entity found, check coverage matching
                try:
                    with open(hit.schema_path, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                    coverage = schema.get("coverage_entities", []) or []
                    
                    logger.info(f"   🔍 Checking sheet '{hit.sheet_name}' for entity '{entity}'")
                    logger.info(f"   📋 Sheet has {len(coverage)} coverage entities: {coverage[:10]}")
                    
                    if coverage:
                        matched, closest, suggestion = self._fuzzy_match_entity(entity, coverage)
                        if matched:
                            matched_hits.append(hit)
                            if suggestion:
                                logger.info(f"✅ Sheet '{hit.sheet_name}' matches entity '{entity}' (typo correction: {suggestion})")
                            else:
                                logger.info(f"✅ Sheet '{hit.sheet_name}' matches entity '{entity}' (matched: {closest[:3]})")
                        else:
                            logger.warning(f"⚠️  Sheet '{hit.sheet_name}' does NOT match entity '{entity}' in coverage list")
                            logger.warning(f"   Coverage list: {coverage[:10]}")
                            # ✅ CRITICAL FIX: Still add to unknown_hits as fallback - entity might be in data even if not in coverage
                            unknown_hits.append(hit)
                            logger.info(f"   ⚠️  Keeping as fallback - will search data directly for '{entity}'")
                    else:
                        # No coverage data - keep as fallback only
                        unknown_hits.append(hit)
                        logger.warning(f"⚠️  Sheet '{hit.sheet_name}' has NO coverage_entities - keeping as fallback")
                except Exception as e:
                    logger.error(f"❌ Error checking coverage for {hit.schema_path}: {e}", exc_info=True)
                    # Include anyway if we can't check (fallback)
                    unknown_hits.append(hit)
            
            # ✅ Priority: coverage-matched sheets first
            if entity and matched_hits:
                logger.info(f"📊 Returning {len(matched_hits[:k])} coverage-matched sheets (entity: '{entity}')")
                return matched_hits[:k]
            
            # ✅ CRITICAL FIX: If coverage doesn't match, scan actual sheet content (never hard-fail)
            # Coverage list can be incomplete. If nothing matched, scan the actual sheets.
            if entity and unknown_hits:
                logger.warning(f"⚠️  No coverage match for '{entity}' - scanning actual sheet content as fallback")
                verified_hits = []
                for hit in unknown_hits:
                    try:
                        # Load parquet data (actual sheet content)
                        df = pd.read_parquet(hit.parquet_path)
                        if self._sheet_contains_entity_fallback(df, entity):
                            verified_hits.append(hit)
                            logger.info(f"✅ Sheet '{hit.sheet_name}' contains '{entity}' (verified by content scan)")
                    except Exception as e:
                        logger.warning(f"Could not scan sheet '{hit.sheet_name}' for entity: {e}")
                        # Include anyway as last resort
                        verified_hits.append(hit)
                
                if verified_hits:
                    logger.info(f"📊 Returning {len(verified_hits[:k])} sheets verified by content scan (entity: '{entity}')")
                    return verified_hits[:k]
                else:
                    # Still return unknown_hits as last resort - don't block
                    logger.warning(f"⚠️  Entity '{entity}' not found in content scan, but using all sheets anyway (coverage may be incomplete)")
                    return unknown_hits[:k]
            
            # No entity: return all sheets
            logger.info(f"📊 Returning {len(plain_hits[:k])} sheets (no entity in query)")
            return plain_hits[:k]
            
        except Exception as e:
            logger.error(f"Error retrieving table sheets: {e}", exc_info=True)
            return []
    
    def answer_from_tables(self, business_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Answer query using table reasoning.
        Enforces coverage matching and strict "no guessing".
        
        Args:
            business_id: Business identifier
            query: User query
            
        Returns:
            Dict with answer, provenance, and metadata, or None if cannot answer
        """
        try:
            # Extract entity from query
            entity = self._extract_entity_from_query(query)
            
            # ✅ FIX: Coverage is a ranking signal, NOT a hard block
            # Retrieve ALL candidate sheets first (no coverage filtering)
            all_results = self.vector_store.search_table_sheets(business_id=business_id, query=query, k=10) or []
            logger.info(f"📊 Retrieved {len(all_results)} candidate sheets from vector store")
            
            # Retrieve relevant sheets (with coverage filtering for ranking)
            hits = self.retrieve_relevant_sheets(business_id, query)
            
            # ✅ CRITICAL FIX: If no coverage matches, scan actual sheet content (never hard-fail)
            if entity and not hits:
                logger.warning(f"⚠️  Entity '{entity}' found but no sheets matched coverage - scanning actual content as fallback")
                
                # Scan actual sheet content to verify entity exists
                verified_hits = []
                for r in all_results[:10]:  # Top 10 sheets
                    md = r.get("metadata") or {}
                    parquet_path = md.get("parquet_path")
                    if not parquet_path:
                        continue
                    
                    try:
                        # Load parquet data (actual sheet content)
                        df = pd.read_parquet(parquet_path)
                        if self._sheet_contains_entity_fallback(df, entity):
                            verified_hits.append(TableHit(
                                document_id=md.get("document_id", ""),
                                filename=md.get("filename", ""),
                                sheet_name=md.get("sheet_name", ""),
                                parquet_path=parquet_path,
                                schema_path=md.get("schema_path", ""),
                                score=float(r.get("score", 0.0)) * 0.8  # Good score for verified match
                            ))
                            logger.info(f"✅ Sheet '{md.get('sheet_name')}' contains '{entity}' (verified by content scan)")
                    except Exception as e:
                        logger.warning(f"Could not scan sheet '{md.get('sheet_name')}' for entity: {e}")
                        # Include anyway as last resort
                        verified_hits.append(TableHit(
                            document_id=md.get("document_id", ""),
                            filename=md.get("filename", ""),
                            sheet_name=md.get("sheet_name", ""),
                            parquet_path=parquet_path,
                            schema_path=md.get("schema_path", ""),
                            score=float(r.get("score", 0.0)) * 0.5  # Lower score for unverified
                        ))
                
                if verified_hits:
                    hits = verified_hits
                    logger.info(f"✅ Continuing with {len(hits)} sheets verified by content scan for '{entity}'")
                else:
                    # Last resort: use all sheets anyway (coverage may be incomplete)
                    logger.warning(f"⚠️  Entity '{entity}' not found in content scan, but using all sheets anyway")
                    for r in all_results[:5]:  # Top 5 sheets as last resort
                        md = r.get("metadata") or {}
                        hits.append(TableHit(
                            document_id=md.get("document_id", ""),
                            filename=md.get("filename", ""),
                            sheet_name=md.get("sheet_name", ""),
                            parquet_path=md.get("parquet_path", ""),
                            schema_path=md.get("schema_path", ""),
                            score=float(r.get("score", 0.0)) * 0.3  # Very low score but still use
                        ))
            
            if not hits:
                logger.info("No relevant table sheets found")
                return None
            
            # Load schemas
            schemas = []
            for h in hits[:3]:  # Top 3 sheets
                try:
                    with open(h.schema_path, "r", encoding="utf-8") as f:
                        schemas.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Could not load schema from {h.schema_path}: {e}")
                    continue
            
            if not schemas:
                return None
            
            # Apply common sense rules (including fee-type binding)
            rules = self._common_sense_rules(query, schemas)
            
            # ✅ FIX: "standard fee" never needs clarification - it means Core, exclude Solo
            # Only ask for clarification if user explicitly mentions both or is ambiguous
            fee_mapping = rules.get("fee_type_mapping", {})
            # Remove needs_clarification check - standard fee = Core, period
            
            # Generate execution plan
            plan = self._llm_plan(query, hits[:3], schemas, rules, entity=entity)
            
            # ✅ CRITICAL FIX: Auto-add entity filter if entity found and not in plan
            if entity and plan:
                # Check if entity filter already exists
                filters = plan.get("filters", [])
                has_entity_filter = any(
                    f.get("value", "").lower() == entity.lower() or 
                    entity.lower() in str(f.get("value", "")).lower()
                    for f in filters
                )
                
                if not has_entity_filter:
                    # Find LA/council column in schemas
                    la_column = None
                    for schema in schemas:
                        for col_info in schema.get("columns", []):
                            col_name = col_info.get("name", "").lower()
                            if any(kw in col_name for kw in ["la", "local authority", "council", "authority", "borough"]):
                                la_column = col_info.get("name")
                                break
                        if la_column:
                            break
                    
                    if la_column:
                        # Add entity filter to plan
                        if "filters" not in plan:
                            plan["filters"] = []
                        plan["filters"].append({
                            "column": la_column,
                            "op": "contains",  # Use contains for fuzzy matching
                            "value": entity
                        })
                        logger.info(f"✅ Auto-added entity filter: {la_column} contains '{entity}'")
                    else:
                        logger.warning(f"⚠️  Entity '{entity}' found but no LA column found in schemas - will search all columns")
            
            if not plan or plan.get("needs_clarification"):
                clarification = plan.get("clarification_question") if plan else "I need more information to answer this question."
                # Include column warnings in clarification
                if rules.get("column_warnings"):
                    clarification += " " + " ".join(rules["column_warnings"])
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": {"type": "table", "clarification_needed": True},
                    "needs_clarification": True
                }
            
            # Execute plan (pass rules for exclude filtering)
            result = self._execute_plan(plan, hits, entity=entity, rules=rules)
            
            # STRICT: If result rows == 0, return clarification (no guessing)
            if result.get("rows_used", 0) == 0:
                clarification = "I couldn't find matching data in the selected sheet."
                if entity:
                    clarification += f" {entity} may not be in this sheet's coverage."
                clarification += " Please check your query or try a different sheet."
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": result.get("provenance", {}),
                    "needs_clarification": True
                }
            
            # Validate result with strict "no guessing" enforcement
            validated = self._validate_result(query, plan, result, hits)
            
            # STRICT: If confidence too low or needs clarification, return clarification
            if validated.get("needs_clarification") or validated.get("confidence", 0) < 0.5:
                return validated
            
            return validated
            
        except Exception as e:
            logger.error(f"Error in table reasoning: {e}", exc_info=True)
            return None
    
    # -----------------------------
    # Helper methods
    # -----------------------------
    
    def _detect_header_row(self, df: pd.DataFrame) -> int:
        """Detect header row by finding row with max non-null string density."""
        best_idx, best_score = 0, -1
        
        for i in range(min(15, len(df))):
            row = df.iloc[i].astype(str).fillna("")
            non_empty = sum(1 for v in row if v and v != "nan" and v.strip())
            uniq = len(set(v for v in row if v and v != "nan" and v.strip()))
            score = non_empty + (uniq * 0.5)
            
            if score > best_score:
                best_idx, best_score = i, score
        
        return best_idx
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names."""
        cols = []
        for c in df.columns:
            name = re.sub(r"\s+", " ", str(c)).strip().lower()
            name = re.sub(r"[^a-z0-9 _\-/%£]", "", name)
            cols.append(name or f"col_{len(cols)}")
        
        df.columns = cols
        return df
    
    def _extract_coverage_entities(self, df: pd.DataFrame, sheet_name: str = "unknown") -> List[str]:
        """
        Extract coverage entities (LA names, councils, etc.) from sheet.
        CRITICAL: Scans ALL unique values in LA/council columns, plus sample rows.
        FIXED: Uses label-based indexing (df.at) instead of iloc with string column names.
        
        Args:
            df: DataFrame to scan
            sheet_name: Sheet name for logging
        """
        coverage_entities = set()
        
        # PRIORITY 1: Check ALL unique values in LA/council columns (most reliable)
        for col in df.columns:
            col_lower = col.lower()
            # Match columns that might contain LA names
            if any(kw in col_lower for kw in ["la", "local authority", "council", "authority", "borough", "county", "commissioning", "region", "area"]):
                try:
                    unique_vals = df[col].dropna().astype(str).unique()
                    logger.debug(f"   Checking column '{col}': {len(unique_vals)} unique values")
                    for val in unique_vals:
                        val = str(val).strip()
                        if self._looks_like_entity(val) and len(val) > 2:
                            coverage_entities.add(val)
                            logger.debug(f"   ✅ Found entity: '{val}' in column '{col}'")
                except Exception as e:
                    logger.warning(f"   Error checking column '{col}': {e}")
        
        # PRIORITY 2: Scan first 100 rows × all cols (broader search)
        # ✅ FIX: Use label-based indexing (df.at) instead of iloc with string column names
        scan_rows = min(100, len(df))
        for i in range(scan_rows):
            for col in df.columns:
                try:
                    # ✅ FIX: use label-based indexing, not iloc with a string
                    val = str(df.at[df.index[i], col]).strip()
                    if self._looks_like_entity(val):
                        coverage_entities.add(val)
                except Exception:
                    pass

        # PRIORITY 3: Scan last 100 rows
        if len(df) > scan_rows:
            start = max(0, len(df) - scan_rows)
            for i in range(start, len(df)):
                for col in df.columns:
                    try:
                        val = str(df.at[df.index[i], col]).strip()
                        if self._looks_like_entity(val):
                            coverage_entities.add(val)
                    except Exception:
                        pass
        
        entities_list = sorted(list(coverage_entities))[:200]  # Limit to 200 entities (increased from 100)
        # ✅ Add diagnostic log with sheet name
        logger.info(f"✅ COVERAGE_ENTITIES[{sheet_name}]: {len(entities_list)} sample={entities_list[:20]}")
        return entities_list
    
    def _extract_coverage_entities_from_raw(self, df_raw: pd.DataFrame) -> List[str]:
        """
        Extract coverage entities from RAW sheet (header=None).
        Scans a larger grid and samples the middle to catch LA lists anywhere.
        FIXED: This catches entities in header rows or outside the main table structure.
        """
        coverage = set()

        if df_raw is None or len(df_raw) == 0:
            return []

        rows = len(df_raw)
        cols = len(df_raw.columns)

        # scan up to 30 cols (not 10)
        scan_cols = min(30, cols)

        # first 80 rows
        for i in range(min(80, rows)):
            for j in range(scan_cols):
                try:
                    v = str(df_raw.iloc[i, j]).strip()
                    if self._looks_like_entity(v):
                        coverage.add(v)
                except:
                    pass

        # middle sample (40 rows around the middle)
        mid = rows // 2
        start = max(0, mid - 20)
        end = min(rows, mid + 20)
        for i in range(start, end):
            for j in range(scan_cols):
                try:
                    v = str(df_raw.iloc[i, j]).strip()
                    if self._looks_like_entity(v):
                        coverage.add(v)
                except:
                    pass

        # last 80 rows
        for i in range(max(0, rows - 80), rows):
            for j in range(scan_cols):
                try:
                    v = str(df_raw.iloc[i, j]).strip()
                    if self._looks_like_entity(v):
                        coverage.add(v)
                except:
                    pass

        entities_list = sorted(list(coverage))[:200]
        if entities_list:
            logger.info(f"   📋 Extracted {len(entities_list)} coverage entities from RAW sheet: {entities_list[:10]}..." if len(entities_list) > 10 else f"   📋 Extracted {len(entities_list)} coverage entities from RAW sheet: {entities_list}")
        return entities_list
    
    def _looks_like_entity(self, text: str) -> bool:
        """
        Check if text looks like an LA/council/authority name.
        FIXED: Now accepts single-word Title Case entities like "Redbridge", "Camden", etc.
        """
        if not text:
            return False

        t = str(text).strip()
        if len(t) < 3 or len(t) > 60:
            return False

        # Reject obvious junk
        if any(ch.isdigit() for ch in t):
            return False
        if t.lower() in {"nan", "none", "null"}:
            return False
        if len(t) <= 2:
            return False

        tl = t.lower()

        # Strong keyword signals
        if any(kw in tl for kw in ["council", "borough", "county", "authority", "alliance", "partnership"]):
            return True

        # ✅ NEW: single-word Title Case entities (e.g., "Redbridge")
        # Accept if it looks like a proper noun and not a generic header word.
        if " " not in t and t[0].isupper() and any(c.islower() for c in t[1:]):
            if tl not in {"standard", "enhanced", "complex", "solo", "core", "fees", "rates", "sheet", "table"}:
                return True

        # Multi-word Title Case (e.g., "South Central")
        words = t.split()
        if len(words) > 1 and all(w and w[0].isupper() for w in words):
            return True

        return False
    
    def _infer_schema(self, df: pd.DataFrame, filename: str, sheet: str) -> Dict[str, Any]:
        """Infer schema from DataFrame."""
        schema = {
            "filename": filename,
            "sheet_name": sheet,
            "row_count": int(len(df)),
            "columns": [],
            "coverage_entities": self._extract_coverage_entities(df, sheet_name=sheet)
        }
        
        for col in df.columns:
            s = df[col]
            colinfo = {
                "name": col,
                "dtype": str(s.dtype),
                "null_pct": float(s.isna().mean()),
                "unique_count": int(s.nunique(dropna=True)),
                "examples": [str(x) for x in s.dropna().astype(str).head(8).tolist()]
            }
            
            # Detect column type hints
            col_lower = col.lower()
            if any(kw in col_lower for kw in ["fee", "rate", "price", "£", "cost", "amount"]):
                colinfo["hint"] = "currency"
            elif any(kw in col_lower for kw in ["age", "year"]):
                colinfo["hint"] = "age"
            elif any(kw in col_lower for kw in ["la", "local authority", "council", "authority"]):
                colinfo["hint"] = "local_authority"
            elif any(kw in col_lower for kw in ["effective", "from", "date"]):
                colinfo["hint"] = "date"
            
            schema["columns"].append(colinfo)
        
        return schema
    
    def _schema_to_embed_text(self, schema: Dict[str, Any]) -> str:
        """Convert schema to text for embedding."""
        parts = [f"FILE: {schema['filename']}", f"SHEET: {schema['sheet_name']}"]
        
        # Include coverage entities
        coverage = schema.get("coverage_entities", [])
        if coverage:
            parts.append(f"COVERAGE: {', '.join(coverage[:20])}")  # First 20 entities
        
        for c in schema["columns"]:
            examples = ", ".join(c.get("examples", [])[:3])
            parts.append(f"COL: {c['name']} | type={c.get('hint', c['dtype'])} | uniq={c['unique_count']} | ex={examples}")
        
        return "\n".join(parts)
    
    def _safe_name(self, s: str) -> str:
        """Create safe filename from string."""
        return re.sub(r"[^a-zA-Z0-9_\-]+", "_", s).strip("_")[:80]
    
    def _common_sense_rules(self, query: str, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply schema-driven common sense rules (universal, not domain-specific).
        Includes fee-type binding.
        """
        q = query.lower()
        rules = {"notes": [], "age_mapping": {}, "column_warnings": [], "fee_type_mapping": {}}
        
        # Rule 1: Fee-type binding
        # Fee-type disambiguation (do NOT default to Solo unless user asks for Solo)
        query_lower = (query or "").lower()
        
        # Check what fee types exist in schemas
        fee_types_found = set()
        for sc in schemas:
            cols = [c["name"].lower() for c in sc["columns"]]
            for col in cols:
                if any(kw in col for kw in ["fee", "rate", "type"]):
                    # Get examples from this column
                    for c_info in sc["columns"]:
                        if c_info["name"].lower() == col:
                            examples = c_info.get("examples", [])
                            for ex in examples:
                                ex_lower = str(ex).lower()
                                if "core" in ex_lower:
                                    fee_types_found.add("Core")
                                if "solo" in ex_lower:
                                    fee_types_found.add("Solo")
                                if "enhanced" in ex_lower:
                                    fee_types_found.add("Enhanced")
                                if "complex" in ex_lower:
                                    fee_types_found.add("Complex")
        
        if "solo" in query_lower:
            # User explicitly wants Solo placement
            if "Solo" in fee_types_found:
                rules["fee_type_mapping"]["target"] = "Solo"
        elif "standard" in query_lower or "core" in query_lower:
            # "Standard" means standard/core, NOT Solo
            if "Core" in fee_types_found:
                rules["fee_type_mapping"]["target"] = "Core"
            # Exclude Solo results unless explicitly requested
            rules["fee_type_mapping"]["exclude"] = ["Solo"]
        else:
            # Default preference: Core over Solo when both exist
            if "Core" in fee_types_found:
                rules["fee_type_mapping"]["target"] = "Core"
                rules["fee_type_mapping"]["exclude"] = ["Solo"]
            elif fee_types_found:
                rules["fee_type_mapping"]["target"] = list(fee_types_found)[0]
        
        # Rule 2: Check if user asks to filter by X but no column resembles X
        filter_keywords = []
        if "from" in q or "for" in q:
            patterns = [
                r"(?:from|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"(\w+\s+\w+)\s+(?:LA|local authority|council)",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, q)
                filter_keywords.extend(matches)
        
        # Check each schema for missing columns
        for sc in schemas:
            cols = [c["name"].lower() for c in sc["columns"]]
            
            # Check if user mentions LA/council but no LA column exists
            if any(kw in q for kw in ["la", "local authority", "council"]) and \
               not any("la" in c or "local authority" in c or "council" in c or "authority" in c for c in cols):
                rules["column_warnings"].append(f"Table '{sc.get('filename', 'unknown')}' has no LA/local authority column. Cannot filter by LA.")
            
            # Check if user mentions age but no age column exists
            if any(kw in q for kw in ["age", "year old", "years old"]) and \
               not any("age" in c or "year" in c for c in cols):
                has_bands = any("band" in c or "range" in c or "-" in c for c in cols)
                if not has_bands:
                    rules["column_warnings"].append(f"Table '{sc.get('filename', 'unknown')}' has no age or age band column.")
        
        # Rule 3: Age mapping (only if band columns exist)
        age_match = re.search(r"(\d+)\s*year\s*old", q)
        if age_match:
            age = int(age_match.group(1))
            has_bands = False
            for sc in schemas:
                cols = [c["name"].lower() for c in sc["columns"]]
                if any("band" in c or "range" in c or "-" in c for c in cols):
                    has_bands = True
                    # Try to map age to band
                    for col in cols:
                        if "-" in col:
                            band_match = re.search(r"(\d+)\s*-\s*(\d+)", col)
                            if band_match:
                                low, high = int(band_match.group(1)), int(band_match.group(2))
                                if low <= age <= high:
                                    rules["age_mapping"]["target_band"] = f"{low}-{high}"
                                    break
                    break
            
            if not has_bands:
                rules["age_mapping"]["target_band"] = str(age)
        
        # Rule 4: Warn if user asks to filter by something that doesn't exist
        for keyword in filter_keywords:
            keyword_lower = keyword.lower()
            found = False
            for sc in schemas:
                cols = [c["name"].lower() for c in sc["columns"]]
                if any(keyword_lower in c or c in keyword_lower for c in cols):
                    found = True
                    break
            if not found and len(keyword) > 2:
                rules["column_warnings"].append(f"Could not find column matching '{keyword}' in any table.")
        
        return rules
    
    def _llm_plan(self, query: str, hits: List[TableHit], schemas: List[Dict[str, Any]], rules: Dict[str, Any], entity: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generate execution plan using LLM."""
        try:
            system_prompt = (
                "You generate a STRICT JSON plan to answer using provided table schemas.\n"
                "No guessing. No other-region estimates. If missing values, output needs_clarification=true.\n"
                "JSON keys:\n"
                "- target_sheets: array of sheet indices (0-based)\n"
                "- filters: array of {column, op, value} where op can be: ==, !=, in, contains, >, <, >=, <=, between\n"
                "- select: array of column names to return\n"
                "- aggregation: string - sum/mean/avg/min/max/count/lookup\n"
                "- groupby: array of column names for grouping\n"
                "- sort_by: column name to sort by\n"
                "- sort_order: 'asc' or 'desc'\n"
                "- top_n: number of top results to return\n"
                "- joins: optional array of {left_sheet, right_sheet, left_key, right_key, join_type}\n"
                "- needs_clarification: bool\n"
                "- clarification_question: string if needs_clarification=true\n"
                "Return ONLY valid JSON, no markdown, no commentary."
            )
            
            payload = {
                "question": query,
                "tables": [{"filename": h.filename, "sheet_name": h.sheet_name, "index": i} for i, h in enumerate(hits)],
                "schemas": schemas,
                "rules": rules,
                "entity": entity  # ✅ Pass entity to LLM so it can add filter
            }
            
            user_prompt = json.dumps(payload, indent=2)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            resp = self.rag_service.llm.invoke(messages)
            raw = (resp.content if hasattr(resp, "content") else str(resp)).strip()
            
            # Strip code fences
            raw = re.sub(r"^```(json)?\s*", "", raw, flags=re.IGNORECASE).strip()
            raw = re.sub(r"\s*```$", "", raw).strip()
            
            plan = json.loads(raw)
            logger.info(f"📋 Generated plan: {plan.get('target_sheets', [])} sheets, {len(plan.get('filters', []))} filters")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating plan: {e}", exc_info=True)
            return None
    
    def _execute_plan(self, plan: Dict[str, Any], hits: List[TableHit], entity: Optional[str] = None, rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute plan using pandas (deterministic, universal operations).
        
        Supports:
        - Filters: ==, !=, in, contains, >, <, >=, <=, between
        - Aggregations: sum, min, max, mean/avg, count
        - Groupby operations
        - Sorting (top N, highest/lowest)
        - Numeric column selection
        - Joins across sheets
        - Type casting (currency, percent, date)
        """
        try:
            target_indices = plan.get("target_sheets", [])
            if not target_indices:
                return {"error": "No target sheets specified", "rows_used": 0}
            
            # Load target sheets
            dfs = {}
            for idx in target_indices:
                if idx >= len(hits):
                    continue
                hit = hits[idx]
                try:
                    dfs[idx] = pd.read_parquet(hit.parquet_path)
                except Exception as e:
                    logger.error(f"Error loading sheet {idx}: {e}")
                    return {"error": f"Cannot load sheet {idx}: {str(e)}", "rows_used": 0}
            
            if not dfs:
                return {"error": "No sheets could be loaded", "rows_used": 0}
            
            # Start with first sheet as primary
            primary_idx = target_indices[0]
            df = dfs[primary_idx].copy()
            hit = hits[primary_idx]
            
            # ✅ Apply joins across sheets (allowlisted only)
            joins = plan.get("joins", [])
            for j in joins:
                try:
                    left_idx = j.get("left_sheet")
                    right_idx = j.get("right_sheet")
                    left_key = j.get("left_key")
                    right_key = j.get("right_key")
                    how = (j.get("join_type") or j.get("how") or "inner").lower()
                    if how not in ["inner", "left", "right", "outer"]:
                        how = "inner"

                    if left_idx not in dfs or right_idx not in dfs:
                        return {"error": f"Join refers to unloaded sheets: {left_idx}, {right_idx}", "rows_used": 0}

                    left_df = dfs[left_idx].copy()
                    right_df = dfs[right_idx].copy()

                    # Fuzzy key matching if exact key not found
                    if left_key not in left_df.columns:
                        lk = left_key.lower()
                        candidates = [c for c in left_df.columns if lk in c.lower() or c.lower() in lk]
                        if candidates:
                            left_key = candidates[0]
                        else:
                            return {"error": f"Left join key '{j.get('left_key')}' not found", "available_columns": list(left_df.columns), "rows_used": 0}

                    if right_key not in right_df.columns:
                        rk = right_key.lower()
                        candidates = [c for c in right_df.columns if rk in c.lower() or c.lower() in rk]
                        if candidates:
                            right_key = candidates[0]
                        else:
                            return {"error": f"Right join key '{j.get('right_key')}' not found", "available_columns": list(right_df.columns), "rows_used": 0}

                    # Safety caps
                    if len(left_df) > 2_000_000 or len(right_df) > 2_000_000:
                        return {"error": "Join aborted: sheet too large for safe merge", "rows_used": 0}

                    merged = pd.merge(left_df, right_df, how=how, left_on=left_key, right_on=right_key)

                    if merged.empty:
                        return {"error": f"Join produced 0 rows using {left_key} ↔ {right_key}", "rows_used": 0}

                    # After first join, merged becomes primary df
                    df = merged
                    hit = hits[left_idx]  # keep provenance anchored to left for now

                except Exception as e:
                    return {"error": f"Join failed: {str(e)}", "rows_used": 0}
            
            # ✅ CRITICAL FIX: If entity found but not in filters, search for it in LA columns
            # (Do this AFTER dataframes are loaded)
            filters = plan.get("filters", [])
            if entity:
                has_entity_filter = any(
                    entity.lower() in str(f.get("value", "")).lower() 
                    for f in filters
                )
                
                if not has_entity_filter:
                    # Find LA/council column and add entity filter
                    la_columns = [c for c in df.columns if any(kw in c.lower() for kw in ["la", "local authority", "council", "authority", "borough"])]
                    if la_columns:
                        la_col = la_columns[0]
                        filters.append({
                            "column": la_col,
                            "op": "contains",
                            "value": entity
                        })
                        logger.info(f"✅ Auto-adding entity filter in executor: {la_col} contains '{entity}'")
                    else:
                        # Search ALL columns for entity (last resort)
                        logger.warning(f"⚠️  No LA column found - searching all columns for '{entity}'")
                        # Search all string columns for entity
                        found_col = None
                        for col in df.columns:
                            if df[col].dtype == "object":
                                # Check if entity appears in this column
                                matches = df[df[col].astype(str).str.contains(entity, case=False, na=False)]
                                if len(matches) > 0:
                                    found_col = col
                                    break
                        
                        if found_col:
                            filters.append({
                                "column": found_col,
                                "op": "contains",
                                "value": entity
                            })
                            logger.info(f"✅ Found '{entity}' in column '{found_col}' - adding filter")
                        else:
                            logger.warning(f"⚠️  Entity '{entity}' not found in any column - will search without filter")
            
            # ✅ Apply exclude filters from fee_type_mapping (e.g., exclude Solo when user asks for "standard fee")
            if rules:
                fee_mapping = rules.get("fee_type_mapping", {})
                exclude_list = fee_mapping.get("exclude", [])
                if exclude_list:
                    # Find fee-type columns (columns that might contain fee types like "Solo", "Core", etc.)
                    fee_type_columns = []
                    for col in df.columns:
                        col_lower = str(col).lower()
                        if any(kw in col_lower for kw in ["fee", "type", "placement", "category"]):
                            # Check if this column contains any of the exclude values
                            col_values = df[col].astype(str).str.lower()
                            for exclude_val in exclude_list:
                                if col_values.str.contains(exclude_val.lower(), case=False, na=False).any():
                                    fee_type_columns.append(col)
                                    break
                    
                    # Filter out rows containing excluded values
                    for col in fee_type_columns:
                        initial_count = len(df)
                        for exclude_val in exclude_list:
                            df = df[~df[col].astype(str).str.contains(exclude_val, case=False, na=False)]
                        if len(df) < initial_count:
                            logger.info(f"✅ Excluded {initial_count - len(df)} rows containing '{exclude_val}' from column '{col}'")
            
            # Apply filters with range support
            filters_applied = []
            filter_matches = {}
            
            for f in filters:
                col = f.get("column")
                op = f.get("op", "==")
                value = f.get("value")
                
                if col not in df.columns:
                    # Try fuzzy column matching
                    col_lower = col.lower()
                    matches = [c for c in df.columns if col_lower in c.lower() or c.lower() in col_lower]
                    if matches:
                        col = matches[0]
                        logger.info(f"Fuzzy matched column '{f.get('column')}' to '{col}'")
                    else:
                        return {
                            "error": f"Column '{f.get('column')}' not found in table",
                            "available_columns": list(df.columns),
                            "rows_used": 0
                        }
                
                # Type casting for numeric operations
                if op in [">", "<", ">=", "<=", "between"]:
                    try:
                        if df[col].dtype == "object":
                            # Try to convert to numeric
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                        value = float(value) if isinstance(value, str) and value.replace(".", "").isdigit() else value
                    except Exception:
                        pass
                
                # Apply filter
                initial_count = len(df)
                if op == "==":
                    if df[col].dtype == "object":
                        df = df[df[col].astype(str).str.lower() == str(value).lower()]
                    else:
                        df = df[df[col] == value]
                elif op == "!=":
                    if df[col].dtype == "object":
                        df = df[df[col].astype(str).str.lower() != str(value).lower()]
                    else:
                        df = df[df[col] != value]
                elif op == "in":
                    df = df[df[col].isin(value)]
                elif op == "contains":
                    df = df[df[col].astype(str).str.contains(str(value), case=False, na=False)]
                elif op == ">":
                    df = df[df[col] > value]
                elif op == "<":
                    df = df[df[col] < value]
                elif op == ">=":
                    df = df[df[col] >= value]
                elif op == "<=":
                    df = df[df[col] <= value]
                elif op == "between":
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        df = df[(df[col] >= value[0]) & (df[col] <= value[1])]
                    else:
                        return {"error": f"Between filter requires [min, max] list", "rows_used": 0}
                
                matches_after = len(df)
                filter_matches[col] = {
                    "op": op,
                    "value": value,
                    "matched": matches_after,
                    "initial": initial_count
                }
                filters_applied.append(f"{col} {op} {value}")
            
            # Apply groupby if specified
            groupby_cols = plan.get("groupby", [])
            if groupby_cols:
                available_groupby = [c for c in groupby_cols if c in df.columns]
                if available_groupby:
                    df = df.groupby(available_groupby)
            
            # Select columns
            select = plan.get("select", [])
            if select:
                available = [c for c in select if c in df.columns]
                if available:
                    if isinstance(df, pd.core.groupby.DataFrameGroupBy):
                        df = df[available].agg(plan.get("aggregation", "first"))
                    else:
                        df = df[available]
            
            # Apply aggregation
            agg = plan.get("aggregation", "lookup")
            result_value = None
            numeric_col = None
            
            # Find numeric column if not specified
            if select:
                numeric_cols = [c for c in select if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
            else:
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            
            if numeric_cols:
                numeric_col = numeric_cols[0]  # Use first numeric column
            
            if isinstance(df, pd.core.groupby.DataFrameGroupBy):
                # Groupby aggregation
                if agg == "sum" and numeric_col:
                    result_value = df[numeric_col].sum().to_dict()
                elif agg == "mean" or agg == "avg" and numeric_col:
                    result_value = df[numeric_col].mean().to_dict()
                elif agg == "min" and numeric_col:
                    result_value = df[numeric_col].min().to_dict()
                elif agg == "max" and numeric_col:
                    result_value = df[numeric_col].max().to_dict()
                elif agg == "count":
                    result_value = df.size().to_dict()
                else:
                    result_value = df.first().to_dict()
            elif len(df) > 0:
                if agg == "sum" and numeric_col:
                    result_value = float(df[numeric_col].sum())
                elif agg == "mean" or agg == "avg" and numeric_col:
                    result_value = float(df[numeric_col].mean())
                elif agg == "min" and numeric_col:
                    result_value = float(df[numeric_col].min())
                elif agg == "max" and numeric_col:
                    result_value = float(df[numeric_col].max())
                elif agg == "count":
                    result_value = int(len(df))
                elif agg == "lookup":
                    # Return first matching row
                    result_value = df.iloc[0].to_dict()
                else:
                    # Return all matching rows (limited)
                    max_rows = plan.get("max_rows", 100)
                    result_value = df.head(max_rows).to_dict("records")
            else:
                result_value = None
            
            # Apply sorting if specified
            sort_col = plan.get("sort_by")
            sort_order = plan.get("sort_order", "desc")  # desc or asc
            top_n = plan.get("top_n")
            
            if sort_col and sort_col in df.columns and isinstance(result_value, list):
                reverse = sort_order == "desc"
                result_value = sorted(result_value, key=lambda x: x.get(sort_col, 0), reverse=reverse)
                if top_n:
                    result_value = result_value[:top_n]
            
            # Get sample rows for provenance
            sample_rows = []
            if len(df) > 0:
                sample_size = min(3, len(df))
                for i in range(sample_size):
                    row = df.iloc[i].to_dict()
                    sample_rows.append({k: str(v) for k, v in row.items()})
            
            return {
                "result": result_value,
                "rows_used": len(df),
                "columns_used": list(df.columns) if not isinstance(df, pd.core.groupby.DataFrameGroupBy) else list(df.columns),
                "filter_matches": filter_matches,
                "provenance": {
                    "filename": hit.filename,
                    "sheet_name": hit.sheet_name,
                    "filters_applied": filters_applied,
                    "columns_used": list(df.columns) if not isinstance(df, pd.core.groupby.DataFrameGroupBy) else [],
                    "sample_rows": sample_rows,
                    "aggregation": agg,
                    "numeric_column_used": numeric_col
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}", exc_info=True)
            return {"error": str(e), "rows_used": 0}
    
    def _compute_confidence(self, hits: List[TableHit], result: Dict[str, Any], filter_matches: Dict[str, Any]) -> float:
        """
        Compute real confidence from:
        - Sheet retrieval scores
        - Filter match success
        - Rows found
        - Deterministic operation success
        """
        if "error" in result or result.get("rows_used", 0) == 0:
            return 0.1
        
        confidence = 0.2  # Base
        
        # Factor 1: Retrieval scores (top hit)
        if hits:
            top_score = hits[0].score
            if top_score >= 0.7:
                confidence += 0.3
            elif top_score >= 0.5:
                confidence += 0.2
            elif top_score >= 0.3:
                confidence += 0.1
        
        # Factor 2: Filter matches
        if filter_matches:
            all_matched = all(fm.get("matched", 0) > 0 for fm in filter_matches.values())
            if all_matched:
                confidence += 0.25
            else:
                # Some filters didn't match
                matched_count = sum(1 for fm in filter_matches.values() if fm.get("matched", 0) > 0)
                total_filters = len(filter_matches)
                confidence += 0.15 * (matched_count / max(total_filters, 1))
        
        # Factor 3: Rows found
        rows_used = result.get("rows_used", 0)
        if rows_used > 0:
            confidence += 0.15
            if rows_used == 1:
                confidence += 0.05  # Exact match bonus
        
        # Factor 4: Deterministic operation
        agg = result.get("provenance", {}).get("aggregation", "lookup")
        if agg in ["sum", "min", "max", "mean", "avg", "count", "lookup"]:
            confidence += 0.1  # Deterministic operation bonus
        
        return min(1.0, max(0.0, confidence))
    
    def _get_closest_matches(self, column: str, value: str, df: pd.DataFrame, max_matches: int = 5) -> List[str]:
        """
        Get closest matches for a filter value using fuzzy matching.
        """
        if column not in df.columns:
            return []
        
        from difflib import get_close_matches
        
        # Get unique values from column
        unique_vals = df[column].dropna().astype(str).unique().tolist()
        
        # Find closest matches
        matches = get_close_matches(str(value), unique_vals, n=max_matches, cutoff=0.6)
        return matches
    
    def _validate_result(self, query: str, plan: Dict[str, Any], result: Dict[str, Any], hits: List[TableHit]) -> Dict[str, Any]:
        """
        Validate result with strict "no guessing" enforcement.
        Returns clarification questions if no deterministic match.
        """
        if "error" in result:
            error_msg = result["error"]
            
            # Check for column not found
            if "not found" in error_msg.lower() and "column" in error_msg.lower():
                available = result.get("available_columns", [])
                clarification = f"I couldn't find the column you mentioned. Available columns: {', '.join(available[:10])}"
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": result.get("provenance", {}),
                    "needs_clarification": True
                }
            
            # Check for "not found" scenarios - suggest closest matches
            if result.get("rows_used", 0) == 0:
                # Try to get closest matches for filter values
                filters = plan.get("filters", [])
                closest_suggestions = []
                
                # Load sheet to get column values
                if hits:
                    try:
                        hit = hits[0]
                        df = pd.read_parquet(hit.parquet_path)
                        
                        for f in filters:
                            col = f.get("column")
                            value = f.get("value")
                            if col in df.columns:
                                matches = self._get_closest_matches(col, str(value), df)
                                if matches:
                                    closest_suggestions.append(f"'{col}' column: {', '.join(matches)}")
                    except Exception:
                        pass
                
                clarification = "I couldn't find matching data in the table."
                if closest_suggestions:
                    clarification += f" Did you mean: {'; '.join(closest_suggestions)}?"
                else:
                    clarification += " Please check the filter values and try again."
                
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": result.get("provenance", {}),
                    "needs_clarification": True
                }
            
            return {
                "answer": f"I encountered an error: {error_msg}",
                "sources": [],
                "confidence": 0.1,
                "provenance": result.get("provenance", {}),
                "needs_clarification": True
            }
        
        # STRICT RULE: No deterministic match = ask clarification
        rows_used = result.get("rows_used", 0)
        if rows_used == 0:
            return {
                "answer": "I couldn't find any matching data. Please check your query and try again, or provide more specific details.",
                "sources": [],
                "confidence": 0.1,
                "provenance": result.get("provenance", {}),
                "needs_clarification": True
            }
        
        # Compute real confidence
        filter_matches = result.get("filter_matches", {})
        confidence = self._compute_confidence(hits, result, filter_matches)
        
        # Format answer from result
        result_value = result.get("result")
        provenance = result.get("provenance", {})
        
        if isinstance(result_value, dict):
            # Format as key-value pairs
            answer_parts = []
            for k, v in result_value.items():
                if pd.notna(v):
                    # Format currency/percent if detected
                    if isinstance(v, (int, float)):
                        if "fee" in k.lower() or "rate" in k.lower() or "price" in k.lower() or "cost" in k.lower():
                            answer_parts.append(f"{k}: {self._format_money_exact(v)}")
                        elif "percent" in k.lower() or "%" in k:
                            answer_parts.append(f"{k}: {v:.2f}%")
                        else:
                            answer_parts.append(f"{k}: {v}")
                    else:
                        answer_parts.append(f"{k}: {v}")
            answer = "\n".join(answer_parts) if answer_parts else "Found matching data but couldn't format it."
        elif isinstance(result_value, (int, float)):
            # Preserve exact decimals for currency values
            if isinstance(result_value, float):
                answer = f"The result is: {self._format_money_exact(result_value)}"
            else:
                answer = f"The result is: {result_value}"
        elif isinstance(result_value, list):
            if len(result_value) == 1:
                answer = f"Found 1 matching result: {result_value[0]}"
            else:
                answer = f"Found {len(result_value)} matching results. First result: {result_value[0] if result_value else 'None'}"
        else:
            answer = str(result_value) if result_value is not None else "No result found"
        
        # Build comprehensive provenance
        provenance_details = {
            "filename": provenance.get("filename", "Unknown"),
            "sheet_name": provenance.get("sheet_name", "Unknown"),
            "columns_used": provenance.get("columns_used", []),
            "filters_applied": provenance.get("filters_applied", []),
            "rows_used": rows_used,
            "sample_rows": provenance.get("sample_rows", [])[:2],  # First 2 sample rows
            "aggregation": provenance.get("aggregation", "lookup"),
            "numeric_column_used": provenance.get("numeric_column_used")
        }
        
        # Build source citation with full details
        source_text = f"Sheet: {provenance_details['sheet_name']}"
        if provenance_details.get("columns_used"):
            source_text += f" | Columns: {', '.join(provenance_details['columns_used'][:5])}"
        if provenance_details.get("filters_applied"):
            source_text += f" | Filters: {', '.join(provenance_details['filters_applied'])}"
        source_text += f" | Rows: {rows_used}"
        
        return {
            "answer": answer,
            "sources": [{
                "document_name": provenance_details["filename"],
                "page": None,
                "chunk_text": source_text,
                "relevance_score": confidence
            }],
            "confidence": confidence,
            "provenance": provenance_details
        }


# Global service instance
_table_reasoning_service = None


def get_table_reasoning_service() -> TableReasoningService:
    """Get global table reasoning service instance."""
    global _table_reasoning_service
    if _table_reasoning_service is None:
        _table_reasoning_service = TableReasoningService()
    return _table_reasoning_service

