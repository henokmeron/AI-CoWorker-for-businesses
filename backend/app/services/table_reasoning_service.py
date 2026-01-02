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
                        coverage_entities = schema.get("coverage_entities", [])
                        coverage_count = len(coverage_entities)
                        logger.info(f"   ✅ Schema inferred: {len(schema['columns'])} columns, {coverage_count} coverage entities")
                        if coverage_entities:
                            logger.info(f"   📋 Coverage entities sample: {coverage_entities[:10]}")
                        else:
                            logger.warning(f"   ⚠️  NO coverage entities extracted from sheet '{sheet_name}' - this may cause entity matching to fail!")
                        
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
    
    def _extract_entity_from_query(self, query: str) -> Optional[str]:
        """
        Extract entity (LA/council name) from query.
        Made more aggressive to catch patterns like "from Redbridge", "Redbridge LA", etc.
        """
        # Pattern: "from Redbridge" or "Redbridge LA" or "Redbridge Council"
        patterns = [
            r"(?:from|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:LA|local authority|council)?",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:LA|local authority|council)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:borough|county|authority)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entity = match.group(1).strip()
                if len(entity) > 2:
                    logger.info(f"🔍 Extracted entity from query: '{entity}'")
                    return entity
        
        # Fallback: Look for capitalized words that might be LA names
        words = query.split()
        for i, word in enumerate(words):
            # Check if word is capitalized and might be an LA name
            if word[0].isupper() and len(word) >= 4 and word.lower() not in ["from", "the", "for", "and", "with", "this", "that", "what", "which"]:
                # Check if next word is "LA", "Council", etc.
                if i + 1 < len(words):
                    next_word = words[i + 1].lower()
                    if next_word in ["la", "council", "borough", "authority"]:
                        logger.info(f"🔍 Extracted entity from query (fallback): '{word}'")
                        return word
        
        logger.debug(f"🔍 No entity extracted from query: '{query[:50]}...'")
        return None
    
    def _fuzzy_match_entity(self, entity: str, coverage_list: List[str], threshold: float = 0.6) -> Tuple[bool, List[str]]:
        """Fuzzy match entity against coverage list."""
        from difflib import get_close_matches
        
        entity_lower = entity.lower()
        coverage_lower = [c.lower() for c in coverage_list]
        
        matches = get_close_matches(entity_lower, coverage_lower, n=5, cutoff=threshold)
        
        if matches:
            # Return original case matches
            original_matches = []
            for m in matches:
                for c in coverage_list:
                    if c.lower() == m:
                        original_matches.append(c)
                        break
            return True, original_matches
        
        return False, []
    
    def retrieve_relevant_sheets(self, business_id: str, query: str, k: int = 6) -> List[TableHit]:
        """
        Retrieve relevant table sheets using schema embeddings.
        Enforces coverage matching when query includes named entities.
        
        Args:
            business_id: Business identifier
            query: User query
            k: Number of sheets to retrieve
            
        Returns:
            List of TableHit objects (filtered by coverage if entity found)
        """
        try:
            # Extract entity from query
            entity = self._extract_entity_from_query(query)
            
            # Retrieve candidate sheets
            results = self.vector_store.search_table_sheets(business_id=business_id, query=query, k=k * 2) or []
            hits: List[TableHit] = []
            
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
                
                # If entity found in query, enforce coverage matching
                if entity:
                    try:
                        with open(hit.schema_path, "r", encoding="utf-8") as f:
                            schema = json.load(f)
                            coverage = schema.get("coverage_entities", [])
                            
                            if coverage:
                                matched, closest = self._fuzzy_match_entity(entity, coverage)
                                if matched:
                                    hits.append(hit)
                                    logger.info(f"✅ Sheet '{hit.sheet_name}' matches entity '{entity}' (coverage: {closest[:3]})")
                                else:
                                    logger.info(f"⚠️  Sheet '{hit.sheet_name}' does NOT match entity '{entity}' (coverage: {coverage[:5]})")
                            else:
                                # No coverage data - include it but with lower priority
                                hits.append(hit)
                    except Exception as e:
                        logger.warning(f"Could not check coverage for {hit.schema_path}: {e}")
                        # Include anyway if we can't check
                        hits.append(hit)
                else:
                    # No entity in query - include all
                    hits.append(hit)
                
                if len(hits) >= k:
                    break
            
            logger.info(f"📊 Retrieved {len(hits)} relevant table sheets for query (entity: {entity or 'none'})")
            return hits
            
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
            
            # Retrieve relevant sheets (with coverage filtering)
            hits = self.retrieve_relevant_sheets(business_id, query)
            
            # STRICT: If entity found but no sheets match coverage, return clarification
            if entity and not hits:
                # Try to get closest matches from all sheets
                all_results = self.vector_store.search_table_sheets(business_id=business_id, query=query, k=10) or []
                all_entities = set()
                for r in all_results:
                    md = r.get("metadata") or {}
                    schema_path = md.get("schema_path")
                    if schema_path:
                        try:
                            with open(schema_path, "r", encoding="utf-8") as f:
                                schema = json.load(f)
                                all_entities.update(schema.get("coverage_entities", []))
                        except Exception:
                            pass
                
                closest = self._fuzzy_match_entity(entity, list(all_entities), threshold=0.4)[1]
                if closest:
                    clarification = f"{entity} not found in any sheet coverage list. Closest matches: {', '.join(closest[:5])}"
                else:
                    clarification = f"{entity} not found in any sheet coverage list. Please check the entity name."
                
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": {"type": "table", "coverage_mismatch": True},
                    "needs_clarification": True
                }
            
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
            
            # Check fee-type binding clarification
            fee_mapping = rules.get("fee_type_mapping", {})
            if fee_mapping.get("needs_clarification"):
                options = fee_mapping.get("options", [])
                clarification = f"Do you mean {options[0]} (standard) or {options[1]}?"
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.1,
                    "provenance": {"type": "table", "fee_type_clarification": True},
                    "needs_clarification": True
                }
            
            # Generate execution plan
            plan = self._llm_plan(query, hits[:3], schemas, rules)
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
            
            # Execute plan
            result = self._execute_plan(plan, hits)
            
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
    
    def _extract_coverage_entities(self, df: pd.DataFrame) -> List[str]:
        """
        Extract coverage entities (LA names, councils, etc.) from sheet.
        CRITICAL: Scans ALL unique values in LA/council columns, plus sample rows.
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
        scan_rows = min(100, len(df))
        for i in range(scan_rows):
            for col in df.columns:
                try:
                    val = str(df.iloc[i, col]).strip()
                    if self._looks_like_entity(val):
                        coverage_entities.add(val)
                except:
                    pass
        
        # PRIORITY 3: Scan last 100 rows
        if len(df) > scan_rows:
            for i in range(max(0, len(df) - scan_rows), len(df)):
                for col in df.columns:
                    try:
                        val = str(df.iloc[i, col]).strip()
                        if self._looks_like_entity(val):
                            coverage_entities.add(val)
                    except:
                        pass
        
        entities_list = sorted(list(coverage_entities))[:100]  # Limit to 100 entities
        logger.info(f"   📋 Extracted {len(entities_list)} coverage entities: {entities_list[:10]}..." if len(entities_list) > 10 else f"   📋 Extracted {len(entities_list)} coverage entities: {entities_list}")
        return entities_list
    
    def _looks_like_entity(self, text: str) -> bool:
        """
        Check if text looks like an LA/council/authority name.
        Made more aggressive to catch single-word names like "Redbridge".
        """
        if not text or len(text) < 3:
            return False
        
        # Skip obvious non-entities
        text_lower = text.lower().strip()
        if text_lower in ["nan", "none", "null", "", "n/a", "na"]:
            return False
        
        # Skip pure numbers or dates
        if text_lower.replace(".", "").replace("-", "").replace("/", "").isdigit():
            return False
        
        # Contains council/borough/authority keywords
        if any(kw in text_lower for kw in ["council", "borough", "county", "authority", "alliance", "partnership", "commissioning"]):
            return True
        
        # Title case pattern - ACCEPT SINGLE WORDS (e.g., "Redbridge", "Brent")
        if text[0].isupper() and any(c.islower() for c in text[1:]):
            # Single word in title case (e.g., "Redbridge", "Brent", "Hackney")
            if len(text.split()) == 1 and len(text) >= 4:
                # Common LA name patterns
                if not text_lower.startswith(("col_", "row_", "sheet", "table", "data")):
                    return True
            # Multiple words in title case (e.g., "South Central", "Commissioning Alliance")
            words = text.split()
            if len(words) > 1 and all(w[0].isupper() if w else False for w in words):
                return True
        
        return False
    
    def _infer_schema(self, df: pd.DataFrame, filename: str, sheet: str) -> Dict[str, Any]:
        """Infer schema from DataFrame."""
        schema = {
            "filename": filename,
            "sheet_name": sheet,
            "row_count": int(len(df)),
            "columns": [],
            "coverage_entities": self._extract_coverage_entities(df)
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
        # "standard fee" → "Core" (default mapping)
        if "standard fee" in q or "standard" in q:
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
            
            if "Core" in fee_types_found and "Solo" in fee_types_found:
                # Ambiguous - need clarification
                rules["fee_type_mapping"]["needs_clarification"] = True
                rules["fee_type_mapping"]["options"] = ["Core", "Solo"]
                rules["notes"].append("User asked for 'standard fee' but both 'Core' and 'Solo' exist. Need clarification.")
            elif "Core" in fee_types_found:
                rules["fee_type_mapping"]["target"] = "Core"
            else:
                # No Core found - use first available
                if fee_types_found:
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
    
    def _llm_plan(self, query: str, hits: List[TableHit], schemas: List[Dict[str, Any]], rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
                "rules": rules
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
    
    def _execute_plan(self, plan: Dict[str, Any], hits: List[TableHit]) -> Dict[str, Any]:
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
            
            # Apply filters with range support
            filters = plan.get("filters", [])
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
                            answer_parts.append(f"{k}: £{v:,.2f}")
                        elif "percent" in k.lower() or "%" in k:
                            answer_parts.append(f"{k}: {v:.2f}%")
                        else:
                            answer_parts.append(f"{k}: {v}")
                    else:
                        answer_parts.append(f"{k}: {v}")
            answer = "\n".join(answer_parts) if answer_parts else "Found matching data but couldn't format it."
        elif isinstance(result_value, (int, float)):
            answer = f"The result is: {result_value:,.2f}" if isinstance(result_value, float) else f"The result is: {result_value}"
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

