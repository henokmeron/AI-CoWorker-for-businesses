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
        try:
            logger.info(f"📊 Ingesting XLSX: {filename} (business_id={business_id}, document_id={document_id})")
            
            xls = pd.ExcelFile(filepath)
            ingested_sheets = []
            
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
                    
                    # Infer schema
                    schema = self._infer_schema(df, filename, sheet_name)
                    
                    # Create storage directory
                    base_dir = self.storage_base / business_id / document_id
                    base_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Safe filename for storage
                    safe_sheet = self._safe_name(sheet_name)
                    parquet_path = base_dir / f"{safe_sheet}.parquet"
                    schema_path = base_dir / f"{safe_sheet}.schema.json"
                    
                    # Save parquet and schema
                    df.to_parquet(str(parquet_path), index=False)
                    with open(schema_path, "w", encoding="utf-8") as f:
                        json.dump(schema, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"   ✅ Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} cols → {parquet_path}")
                    
                    # Index schema embedding
                    embed_text = self._schema_to_embed_text(schema)
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
            
            logger.info(f"✅ Ingested {len(ingested_sheets)} sheets from {filename}")
            return {
                "success": True,
                "sheets_ingested": len(ingested_sheets),
                "sheets": ingested_sheets
            }
            
        except Exception as e:
            logger.error(f"❌ Error ingesting XLSX {filename}: {e}", exc_info=True)
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
    
    def retrieve_relevant_sheets(self, business_id: str, query: str, k: int = 6) -> List[TableHit]:
        """
        Retrieve relevant table sheets using schema embeddings.
        
        Args:
            business_id: Business identifier
            query: User query
            k: Number of sheets to retrieve
            
        Returns:
            List of TableHit objects
        """
        try:
            results = self.vector_store.search_table_sheets(business_id=business_id, query=query, k=k) or []
            hits: List[TableHit] = []
            
            for r in results:
                md = r.get("metadata") or {}
                hits.append(TableHit(
                    document_id=md.get("document_id", ""),
                    filename=md.get("filename", ""),
                    sheet_name=md.get("sheet_name", ""),
                    parquet_path=md.get("parquet_path", ""),
                    schema_path=md.get("schema_path", ""),
                    score=float(r.get("score", 0.0))
                ))
            
            logger.info(f"📊 Retrieved {len(hits)} relevant table sheets for query")
            return hits
            
        except Exception as e:
            logger.error(f"Error retrieving table sheets: {e}", exc_info=True)
            return []
    
    def answer_from_tables(self, business_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Answer query using table reasoning.
        
        Args:
            business_id: Business identifier
            query: User query
            
        Returns:
            Dict with answer, provenance, and metadata, or None if cannot answer
        """
        try:
            # Retrieve relevant sheets
            hits = self.retrieve_relevant_sheets(business_id, query)
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
            
            # Apply common sense rules
            rules = self._common_sense_rules(query, schemas)
            
            # Generate execution plan
            plan = self._llm_plan(query, hits[:3], schemas, rules)
            if not plan or plan.get("needs_clarification"):
                clarification = plan.get("clarification_question") if plan else "I need more information to answer this question."
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.3,
                    "provenance": {"type": "table", "clarification_needed": True}
                }
            
            # Execute plan
            result = self._execute_plan(plan, hits)
            
            # Validate result
            validated = self._validate_result(query, plan, result)
            
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
    
    def _infer_schema(self, df: pd.DataFrame, filename: str, sheet: str) -> Dict[str, Any]:
        """Infer schema from DataFrame."""
        schema = {
            "filename": filename,
            "sheet_name": sheet,
            "row_count": int(len(df)),
            "columns": []
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
        
        for c in schema["columns"]:
            examples = ", ".join(c.get("examples", [])[:3])
            parts.append(f"COL: {c['name']} | type={c.get('hint', c['dtype'])} | uniq={c['unique_count']} | ex={examples}")
        
        return "\n".join(parts)
    
    def _safe_name(self, s: str) -> str:
        """Create safe filename from string."""
        return re.sub(r"[^a-zA-Z0-9_\-]+", "_", s).strip("_")[:80]
    
    def _common_sense_rules(self, query: str, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply common sense rules before planning."""
        q = query.lower()
        rules = {"notes": [], "age_mapping": {}, "la_filtering": {}}
        
        # Rule 1: Carer fee usually not LA-specific if no LA column exists
        if "fee to carer" in q or "carer" in q:
            for sc in schemas:
                cols = [c["name"] for c in sc["columns"]]
                if not any("la" in c or "local authority" in c or "council" in c for c in cols):
                    rules["notes"].append("Carer fee table appears global (no LA column). Do not filter carer fee by LA.")
        
        # Rule 2: Age mapping (13 year old → 11-15 band)
        age_match = re.search(r"(\d+)\s*year\s*old", q)
        if age_match:
            age = int(age_match.group(1))
            # Map to common age bands
            if 0 <= age <= 4:
                rules["age_mapping"]["target_band"] = "0-4"
            elif 5 <= age <= 10:
                rules["age_mapping"]["target_band"] = "5-10"
            elif 11 <= age <= 15:
                rules["age_mapping"]["target_band"] = "11-15"
            elif 16 <= age <= 17:
                rules["age_mapping"]["target_band"] = "16-17"
            else:
                rules["age_mapping"]["target_band"] = str(age)
        
        # Rule 3: LA extraction
        la_match = re.search(r"(?:from|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:LA|local authority|council)", q)
        if la_match:
            rules["la_filtering"]["target_la"] = la_match.group(1)
        
        return rules
    
    def _llm_plan(self, query: str, hits: List[TableHit], schemas: List[Dict[str, Any]], rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate execution plan using LLM."""
        try:
            system_prompt = (
                "You generate a STRICT JSON plan to answer using provided table schemas.\n"
                "No guessing. No other-region estimates. If missing values, output needs_clarification=true.\n"
                "JSON keys: target_sheets (array of sheet indices), filters (array of {column, op, value}), "
                "select (array of column names), aggregation (string: sum/avg/min/max/lookup), "
                "joins (optional), needs_clarification (bool), clarification_question (string).\n"
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
        """Execute plan using pandas (deterministic)."""
        try:
            target_indices = plan.get("target_sheets", [])
            if not target_indices:
                return {"error": "No target sheets specified"}
            
            # Load first target sheet
            hit = hits[target_indices[0]]
            df = pd.read_parquet(hit.parquet_path)
            
            # Apply filters
            filters = plan.get("filters", [])
            for f in filters:
                col = f.get("column")
                op = f.get("op", "==")
                value = f.get("value")
                
                if col not in df.columns:
                    return {"error": f"Column '{col}' not found in table"}
                
                if op == "==":
                    # Handle case-insensitive string matching
                    if df[col].dtype == "object":
                        df = df[df[col].astype(str).str.lower() == str(value).lower()]
                    else:
                        df = df[df[col] == value]
                elif op == "in":
                    df = df[df[col].isin(value)]
                elif op == "contains":
                    df = df[df[col].astype(str).str.contains(str(value), case=False, na=False)]
            
            # Select columns
            select = plan.get("select", [])
            if select:
                available = [c for c in select if c in df.columns]
                if available:
                    df = df[available]
            
            # Apply aggregation
            agg = plan.get("aggregation", "lookup")
            if agg == "sum" and len(df) > 0:
                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) > 0:
                    result_value = df[numeric_cols[0]].sum()
                else:
                    result_value = "No numeric columns to sum"
            elif agg == "lookup" and len(df) > 0:
                # Return first matching row
                result_value = df.iloc[0].to_dict() if len(df) > 0 else "No matching rows"
            else:
                result_value = df.to_dict("records") if len(df) > 0 else "No matching rows"
            
            return {
                "result": result_value,
                "rows_used": len(df),
                "columns_used": list(df.columns),
                "provenance": {
                    "filename": hit.filename,
                    "sheet_name": hit.sheet_name,
                    "filters_applied": filters
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _validate_result(self, query: str, plan: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate result and format answer."""
        if "error" in result:
            error_msg = result["error"]
            
            # Check for "not found" scenarios
            if "not found" in error_msg.lower() or result.get("rows_used", 0) == 0:
                # Try to suggest closest matches
                clarification = f"I couldn't find matching data in the table. {error_msg}"
                return {
                    "answer": clarification,
                    "sources": [],
                    "confidence": 0.3,
                    "provenance": result.get("provenance", {})
                }
            
            return {
                "answer": f"I encountered an error: {error_msg}",
                "sources": [],
                "confidence": 0.2,
                "provenance": result.get("provenance", {})
            }
        
        # Format answer from result
        result_value = result.get("result")
        provenance = result.get("provenance", {})
        
        if isinstance(result_value, dict):
            # Format as key-value pairs
            answer_parts = []
            for k, v in result_value.items():
                if pd.notna(v):
                    answer_parts.append(f"{k}: {v}")
            answer = "\n".join(answer_parts) if answer_parts else "Found matching data but couldn't format it."
        elif isinstance(result_value, (int, float)):
            answer = f"The result is: {result_value}"
        else:
            answer = str(result_value)
        
        return {
            "answer": answer,
            "sources": [{
                "document_name": provenance.get("filename", "Unknown"),
                "page": None,
                "chunk_text": f"Sheet: {provenance.get('sheet_name', 'Unknown')}",
                "relevance_score": 0.9
            }],
            "confidence": 0.85,
            "provenance": provenance
        }


# Global service instance
_table_reasoning_service = None


def get_table_reasoning_service() -> TableReasoningService:
    """Get global table reasoning service instance."""
    global _table_reasoning_service
    if _table_reasoning_service is None:
        _table_reasoning_service = TableReasoningService()
    return _table_reasoning_service

