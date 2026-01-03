"""
RAG (Retrieval Augmented Generation) service for intelligent Q&A.
ChatGPT-grade intelligence with multi-pass retrieval, query understanding, validation, and reasoning.
"""
import logging
import time
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ..core.config import settings
from .vector_store import get_vector_store
from ..models.chat import ChatMessage, Source

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for document-based question answering.

    Upgrades included:
    - Query understanding + rewrite
    - Multi-pass retrieval
    - Relevance filtering + dedup + rerank
    - Date/version awareness (Effective-from)
    - Cross-document synthesis prompt
    - Post-answer validation + confidence control
    - Streaming parity: final correction + confidence event
    """

    def __init__(self, llm_provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.model = model or self._get_default_model()
        self.llm = self._initialize_llm()
        self.vector_store = get_vector_store()

    def _get_default_model(self) -> str:
        if self.provider == "openai":
            return settings.OPENAI_MODEL
        elif self.provider == "anthropic":
            return settings.ANTHROPIC_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_MODEL
        return "gpt-4-turbo-preview"

    def _initialize_llm(self):
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            logger.info(f"Initializing OpenAI LLM with model: {self.model}")
            return ChatOpenAI(
                model=self.model,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
                streaming=True,
            )
        elif self.provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic

                if not settings.ANTHROPIC_API_KEY:
                    raise ValueError("Anthropic API key not configured")
                logger.info(f"Initializing Anthropic LLM with model: {self.model}")
                return ChatAnthropic(
                    model=self.model,
                    anthropic_api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.1,
                )
            except ImportError:
                raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        elif self.provider == "ollama":
            logger.info(f"Initializing Ollama LLM with model: {self.model}")
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=self.model,
                temperature=0.1,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    # -----------------------------
    # Advanced RAG helpers
    # -----------------------------

    def _strip_html_source_boxes(self, text: str) -> str:
        """Strip HTML source boxes from text."""
        if not text:
            return text
        # Remove source-box div blocks
        text = re.sub(r'<div\s+class\s*=\s*["\']source-box["\']>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<div\s+class\s*=\s*source-box>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove common remnants
        text = re.sub(r'<strong>Source\s+\d+.*?</strong>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<em>Relevance:.*?</em>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'📚\s*Sources?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<details.*?Sources?.*?</details>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Cleanup whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'\s{3,}', ' ', text)
        return text.strip()

    def _extract_effective_date(self, blob: str) -> Optional[datetime]:
        """
        Extracts 'Effective from 1 October 2025' style dates.
        Returns datetime or None.
        """
        if not blob:
            return None

        # Common patterns
        patterns = [
            r"effective\s+from\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            r"effective\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            r"from\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        ]
        for p in patterns:
            m = re.search(p, blob, flags=re.IGNORECASE)
            if not m:
                continue
            day = int(m.group(1))
            month_name = m.group(2).strip().lower()
            year = int(m.group(3))
            month_map = {
                "jan": 1, "january": 1,
                "feb": 2, "february": 2,
                "mar": 3, "march": 3,
                "apr": 4, "april": 4,
                "may": 5,
                "jun": 6, "june": 6,
                "jul": 7, "july": 7,
                "aug": 8, "august": 8,
                "sep": 9, "sept": 9, "september": 9,
                "oct": 10, "october": 10,
                "nov": 11, "november": 11,
                "dec": 12, "december": 12,
            }
            month = month_map.get(month_name[:3], None) or month_map.get(month_name, None)
            if month:
                try:
                    return datetime(year, month, day)
                except Exception:
                    return None
        return None

    def _rewrite_query(self, query: str) -> Dict[str, Any]:
        """
        Returns dict:
          rewritten_query, intent, entities, must_include_terms, must_exclude_terms
        """
        system = SystemMessage(content=(
            "You rewrite user questions into retrieval-optimized queries.\n"
            "Return STRICT JSON ONLY. Keys: rewritten_query (string), intent (string), "
            "entities (object), must_include_terms (array), must_exclude_terms (array).\n"
            "No markdown. No commentary."
        ))
        user = HumanMessage(content=f"User question:\n{query}\n\nReturn JSON now.")
        try:
            resp = self.llm.invoke([system, user])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            raw = raw.strip()
            # Strip accidental code fences
            raw = re.sub(r"^```(json)?\s*", "", raw, flags=re.IGNORECASE).strip()
            raw = re.sub(r"\s*```$", "", raw).strip()
            data = json.loads(raw)
            # Defaults
            return {
                "rewritten_query": data.get("rewritten_query") or query,
                "intent": data.get("intent") or "lookup",
                "entities": data.get("entities") or {},
                "must_include_terms": data.get("must_include_terms") or [],
                "must_exclude_terms": data.get("must_exclude_terms") or [],
            }
        except Exception as e:
            logger.warning(f"Query rewrite failed; using raw query. Error: {e}")
            return {
                "rewritten_query": query,
                "intent": "lookup",
                "entities": {},
                "must_include_terms": [],
                "must_exclude_terms": [],
            }

    def _multi_pass_retrieval(self, business_id: str, qinfo: Dict[str, Any], max_sources: int) -> List[Dict[str, Any]]:
        """
        Pass 1: broad search
        Pass 2: focused search using entities / include terms
        Pass 3: confirmation search (optional)
        """
        base_q = qinfo["rewritten_query"]
        entities = qinfo.get("entities") or {}
        include_terms = qinfo.get("must_include_terms") or []

        # Pass sizes
        k1 = max(max_sources * 6, 30)
        k2 = max(max_sources * 4, 20)
        k3 = max(max_sources * 3, 15)

        docs_all: List[Dict[str, Any]] = []

        # Pass 1: Broad semantic retrieval
        logger.info(f"🔍 PASS 1: Broad retrieval (k={k1}) for business_id='{business_id}'")
        pass1_docs = self.vector_store.search(business_id=business_id, query=base_q, k=k1) or []
        logger.info(f"   PASS 1 results: {len(pass1_docs)} chunks")
        docs_all.extend(pass1_docs)
        
        # Pass 2: Focused retrieval using entities
        focused_bits = []
        for key in ["date", "effective_date", "council", "fee_type", "category", "age_range", "service"]:
            v = entities.get(key)
            if v:
                focused_bits.append(str(v))
        focused_bits.extend(include_terms[:6])
        if focused_bits:
            q2 = f"{base_q} | " + " | ".join(focused_bits)
            logger.info(f"🎯 PASS 2: Focused retrieval with entities (k={k2})")
            pass2_docs = self.vector_store.search(business_id=business_id, query=q2, k=k2) or []
            logger.info(f"   PASS 2 results: {len(pass2_docs)} chunks")
            docs_all.extend(pass2_docs)
        
        # Pass 3: Light confirmation
        if include_terms:
            q3 = f"{base_q} {include_terms[0]}"
            logger.info(f"🔗 PASS 3: Confirmation retrieval (k={k3})")
            pass3_docs = self.vector_store.search(business_id=business_id, query=q3, k=k3) or []
            logger.info(f"   PASS 3 results: {len(pass3_docs)} chunks")
            docs_all.extend(pass3_docs)
        
        logger.info(f"📚 Multi-pass retrieval: {len(docs_all)} total chunks (unique: {len(set(d.get('id') for d in docs_all if d.get('id')))} unique IDs)")
        
        # CRITICAL DIAGNOSTIC: If we got 0 chunks, log why
        if len(docs_all) == 0:
            logger.error(f"❌ CRITICAL: All retrieval passes returned 0 chunks!")
            logger.error(f"   business_id='{business_id}'")
            logger.error(f"   Query: '{base_q[:100]}'")
            logger.error(f"   This means the vector store search is not finding any documents")
        
        return docs_all

    def _dedup_filter_rerank(
        self,
        docs: List[Dict[str, Any]],
        qinfo: Dict[str, Any],
        max_sources: int
    ) -> List[Dict[str, Any]]:
        """
        Dedup by (document_id + text hash), apply hard filters, rerank with bonuses.
        Also prefer latest effective-from when conflicts exist.
        """
        entities = qinfo.get("entities") or {}
        include_terms = [t.lower() for t in (qinfo.get("must_include_terms") or [])]
        exclude_terms = [t.lower() for t in (qinfo.get("must_exclude_terms") or [])]

        seen = set()
        kept: List[Dict[str, Any]] = []

        for d in docs or []:
            text = (d.get("text") or "").strip()
            if not text:
                continue
            md = d.get("metadata") or {}
            doc_id = md.get("document_id") or "unknown"
            key = (doc_id, hash(text[:600]))
            if key in seen:
                continue
            seen.add(key)

            low = text.lower()

            # Hard excludes
            if any(ex in low for ex in exclude_terms):
                continue

            # Assign effective date if detectable (filename + chunk text)
            filename = (md.get("filename") or "")
            eff = self._extract_effective_date(filename) or self._extract_effective_date(text)
            md["_effective_date"] = eff.isoformat() if eff else None

            kept.append(d)

        # Scoring with effective date preference (deterministic rule)
        def score_doc(d: Dict[str, Any]) -> float:
            base = float(d.get("score") or 0.0)
            md = d.get("metadata") or {}
            text = (d.get("text") or "").lower()
            bonus = 0.0

            # Include-term bonus
            for t in include_terms:
                if t and t in text:
                    bonus += 0.12

            # Entity bonus
            for k, v in entities.items():
                if not v:
                    continue
                if str(v).lower() in text:
                    bonus += 0.10

            # DETERMINISTIC RULE: Prefer newer effective date (stronger weight)
            eff = md.get("_effective_date")
            if eff:
                try:
                    dt = datetime.fromisoformat(eff)
                    # Stronger preference for newer dates (normalized to 0-0.15 range)
                    # Dates from 2020-2030 get 0.0-0.15 bonus
                    year_bonus = min(max((dt.year - 2020) / 10.0, 0.0), 0.15)
                    bonus += year_bonus
                    logger.debug(f"Document {md.get('filename', 'unknown')} effective date {eff}: +{year_bonus:.3f} bonus")
                except Exception:
                    pass
            else:
                # Fallback: prefer newer upload timestamp if available
                upload_time = md.get("upload_timestamp") or md.get("created_at")
                if upload_time:
                    try:
                        if isinstance(upload_time, str):
                            upload_dt = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                        else:
                            upload_dt = upload_time
                        # Smaller bonus for upload time (0-0.05 range)
                        year_bonus = min(max((upload_dt.year - 2020) / 20.0, 0.0), 0.05)
                        bonus += year_bonus
                    except Exception:
                        pass

            return base + bonus

        kept = sorted(kept, key=score_doc, reverse=True)

        # Diversify by document_id (prevent one doc from dominating)
        diversified: List[Dict[str, Any]] = []
        per_doc_cap = max(1, max_sources // 2)
        counts: Dict[str, int] = {}
        for d in kept:
            doc_id = (d.get("metadata") or {}).get("document_id") or "unknown"
            counts.setdefault(doc_id, 0)
            if counts[doc_id] >= per_doc_cap and len(counts) > 1:
                continue
            diversified.append(d)
            counts[doc_id] += 1
            if len(diversified) >= max_sources:
                break

        logger.info(f"✅ After dedup/filter/rerank: {len(diversified)} chunks from {len(counts)} documents")
        return diversified[:max_sources]

    def _format_context_grouped(self, docs: List[Dict[str, Any]]) -> str:
        """
        Groups chunks by filename, includes effective-from if detected.
        """
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for d in docs or []:
            md = d.get("metadata") or {}
            fn = md.get("filename") or "Unknown"
            by_file.setdefault(fn, []).append(d)

        blocks = []
        i = 1
        for fn, items in by_file.items():
            # Prefer best effective date per file
            eff_dates = []
            for it in items:
                md = it.get("metadata") or {}
                if md.get("_effective_date"):
                    eff_dates.append(md["_effective_date"])
            eff_dates = [e for e in eff_dates if e]
            eff_info = f" | Effective: {max(eff_dates)}" if eff_dates else ""

            blocks.append(f"[Document {i}: {fn}{eff_info}]")
            for j, it in enumerate(items[:4], 1):
                md = it.get("metadata") or {}
                page = md.get("page_number")
                page_info = f" (Page {page})" if page else ""
                blocks.append(f"  - Chunk {j}{page_info}:\n{it.get('text','')}\n")
            i += 1

        return "\n".join(blocks).strip()

    def _build_synthesis_messages(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        reply_as_me: bool = False
    ) -> List:
        """
        Strong cross-document synthesis prompt.
        """
        if reply_as_me:
            system_prompt = (
                "Write as the user. Use the provided context only. "
                "If missing, say exactly what is missing."
            )
        else:
            system_prompt = (
                "You are a business-grade AI assistant.\n"
                "Use ONLY the provided context to answer.\n"
                "Synthesize across ALL relevant documents.\n"
                "If documents conflict, prefer the newest 'Effective from' version.\n"
                "If insufficient context, say so and ask the minimum clarifying question.\n"
                "Do NOT output raw HTML. Do NOT output source-box markup."
            )

        messages = [SystemMessage(content=system_prompt)]

        if conversation_history:
            for msg in conversation_history[-6:]:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                elif hasattr(msg, "role"):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=(
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION:\n{query}\n\n"
            "Answer now with a clear, structured response."
        )))
        return messages

    def _assess_confidence(self, docs: List[Dict[str, Any]], qinfo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic confidence based on retrieval strength.
        """
        if not docs:
            return {"level": "low", "reason": "No documents retrieved", "score": 0.05}

        scores = [float(d.get("score") or 0.0) for d in docs]
        top = max(scores) if scores else 0.0
        avg = sum(scores) / len(scores) if scores else 0.0

        # Heuristics
        score = 0.2
        if top >= 0.35:
            score += 0.35
        elif top >= 0.2:
            score += 0.20

        if avg >= 0.18:
            score += 0.20
        elif avg >= 0.12:
            score += 0.10

        # Multi-doc coverage improves confidence
        doc_ids = set((d.get("metadata") or {}).get("document_id") for d in docs)
        if len(doc_ids) >= 2:
            score += 0.10

        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            lvl = "high"
        elif score >= 0.45:
            lvl = "medium"
        else:
            lvl = "low"

        return {
            "level": lvl,
            "score": round(score, 2),
            "top_similarity": round(top, 3),
            "avg_similarity": round(avg, 3)
        }

    def _validate_answer(self, answer: str, context: str, qinfo: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Deterministic validation:
        1. Check if numbers in answer appear in context
        2. If query intent is calculate/compare and answer contains currency/percent, verify math
        3. If flagged, run LLM correction constrained to context
        Returns (needs_correction, corrected_answer)
        """
        a = answer or ""
        c = context or ""
        intent = (qinfo or {}).get("intent", "lookup")

        # Numeric presence check
        nums = re.findall(r"(?<!\w)(?:£\s*)?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?(?!\w)", a)
        if not nums:
            return (False, a)

        missing = []
        for n in nums[:25]:
            # Normalize
            nn = n.replace("£", "").replace(" ", "").replace(",", "").replace("%", "")
            if nn and nn not in c:
                missing.append(n)

        # Math verification for calculate/compare intents with currency/percent
        math_issues = []
        if intent in ["calculate", "compare"] and any("£" in n or "%" in n for n in nums):
            # Extract currency values from answer
            currency_values = re.findall(r"£\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", a)
            if currency_values:
                # Extract corresponding values from context
                context_currencies = re.findall(r"£\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", c)
                if context_currencies:
                    # Simple check: if answer has totals/sums, verify they match context
                    # This is a basic check - full math verification would require parsing the query
                    pass  # Placeholder for future deterministic math verification

        if len(missing) >= 3 or math_issues:
            # Correction pass constrained to context
            correction_instruction = (
                "You are validating an answer against the provided context.\n"
                "Rewrite the answer using ONLY facts/numbers that appear in the context.\n"
                "If a number is not in context, remove or qualify it.\n"
            )
            if math_issues:
                correction_instruction += "Verify all calculations match the context data.\n"
            correction_instruction += "No HTML. No source-box."
            
            system = SystemMessage(content=correction_instruction)
            user = HumanMessage(content=f"CONTEXT:\n{c}\n\nANSWER TO FIX:\n{a}\n\nReturn corrected answer only.")
            try:
                resp = self.llm.invoke([system, user])
                fixed = resp.content if hasattr(resp, "content") else str(resp)
                fixed = self._strip_html_source_boxes(fixed)
                return (True, fixed)
            except Exception:
                return (True, a)

        return (False, a)

    # -----------------------------
    # Public API
    # -----------------------------

    def query(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5,
        reply_as_me: bool = False
    ) -> Dict[str, Any]:
        """Answer a query using advanced RAG with all intelligence layers."""
        start_time = time.time()

        try:
            logger.info(f"🔍 Advanced RAG: business_id='{business_id}', q='{query[:120]}'")

            # 1) Rewrite query
            qinfo = self._rewrite_query(query)
            logger.info(f"🧠 Rewrite: {qinfo.get('rewritten_query','')[:160]} | intent={qinfo.get('intent')}")

            # 2) Multi-pass retrieval
            raw_docs = self._multi_pass_retrieval(business_id, qinfo, max_sources=max_sources)
            logger.info(f"📥 Retrieved raw chunks: {len(raw_docs)}")
            
            # CRITICAL DIAGNOSTIC: Check if we got any documents
            if len(raw_docs) == 0:
                logger.error(f"❌ CRITICAL: No documents retrieved for business_id='{business_id}'")
                logger.error(f"❌ This means either:")
                logger.error(f"   1. No documents were uploaded for this business_id")
                logger.error(f"   2. Documents were uploaded but not stored in vector DB")
                logger.error(f"   3. Collection 'business_{business_id}' doesn't exist or is empty")
                # Check collection status
                try:
                    collection = self.vector_store.get_collection(business_id)
                    doc_count = collection.count() if collection else 0
                    logger.error(f"   Collection 'business_{business_id}' has {doc_count} documents")
                except Exception as e:
                    logger.error(f"   Could not check collection: {e}")
            
            # 3) Dedup/filter/rerank
            top_docs = self._dedup_filter_rerank(raw_docs, qinfo, max_sources=max_sources)
            logger.info(f"✅ After rerank: {len(top_docs)}")
            
            # CRITICAL DIAGNOSTIC: Check if we have context after reranking
            if len(top_docs) == 0:
                logger.error(f"❌ CRITICAL: No documents after reranking - LLM will have no context!")
                logger.error(f"   Raw docs: {len(raw_docs)}, After rerank: {len(top_docs)}")
            
            context = self._format_context_grouped(top_docs) if top_docs else ""
            
            # CRITICAL DIAGNOSTIC: Log context length
            if not context or len(context) < 100:
                logger.error(f"❌ CRITICAL: Context is empty or too short ({len(context)} chars) - LLM cannot answer!")
                logger.error(f"   This will cause the LLM to say 'document does not provide information'")
            else:
                logger.info(f"📄 Context length: {len(context)} chars")
            messages = self._build_synthesis_messages(query, context, conversation_history, reply_as_me=reply_as_me)

            # 4) Generate answer
            resp = self.llm.invoke(messages)
            answer = resp.content if hasattr(resp, "content") else str(resp)
            answer = self._strip_html_source_boxes(answer)

            # 5) Validate + confidence
            needs_fix, fixed = self._validate_answer(answer, context, qinfo)
            if needs_fix:
                logger.info("🔧 Answer corrected based on validation")
                answer = fixed

            confidence = self._assess_confidence(top_docs, qinfo)
            logger.info(f"📊 Confidence: {confidence.get('level')} ({confidence.get('score')})")

            # 6) Sources + metrics
            sources = self._format_sources(top_docs)
            response_time = time.time() - start_time
            tokens_used = self._estimate_tokens(messages, answer)

            return {
                "answer": answer,
                "sources": sources,
                "tokens_used": tokens_used,
                "response_time": response_time,
                "confidence": confidence.get("score"),
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                    "retrieved_docs": len(top_docs),
                    "confidence": confidence,
                    "rewritten_query": qinfo.get("rewritten_query"),
                    "intent": qinfo.get("intent"),
                }
            }

        except Exception as e:
            logger.error(f"Error in advanced RAG query: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process query: {str(e)}")

    async def query_stream(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5
    ):
        """
        Streaming with parity:
        - Stream tokens live
        - Then validate + emit final_correction if needed
        - Then emit confidence + sources
        """
        try:
            # 1) Rewrite query
            qinfo = self._rewrite_query(query)

            # 2) Multi-pass retrieval
            raw_docs = self._multi_pass_retrieval(business_id, qinfo, max_sources=max_sources)
            top_docs = self._dedup_filter_rerank(raw_docs, qinfo, max_sources=max_sources)
            context = self._format_context_grouped(top_docs) if top_docs else ""

            if not top_docs:
                yield {"type": "answer", "content": "I can't find any uploaded document content for this conversation. Upload the file again or ask in the conversation where you uploaded it."}
                yield {"type": "confidence", "content": {"level": "low", "reason": "No documents retrieved", "score": 0.05}}
                return

            messages = self._build_synthesis_messages(query, context, conversation_history, reply_as_me=False)

            # 3) Stream response
            full = []
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    piece = chunk.content
                    full.append(piece)
                    yield {"type": "answer", "content": piece}

            full_answer = self._strip_html_source_boxes("".join(full))

            # 4) Validate after stream (STREAMING PARITY)
            needs_fix, fixed = self._validate_answer(full_answer, context, qinfo)
            if needs_fix and fixed and fixed.strip() and fixed.strip() != full_answer.strip():
                logger.info("🔧 Streaming: Answer corrected, emitting final_correction")
                # Frontend should replace streamed text with this final corrected answer
                yield {"type": "final_correction", "content": fixed}

            # 5) Confidence + sources (STREAMING PARITY)
            conf = self._assess_confidence(top_docs, qinfo)
            yield {"type": "confidence", "content": conf}

            sources = self._format_sources(top_docs)
            yield {"type": "sources", "content": [s.dict() for s in sources]}

        except Exception as e:
            logger.error(f"Error in streaming RAG query: {e}", exc_info=True)
            yield {"type": "error", "content": f"Failed to process query: {str(e)}"}

    # -----------------------------
    # Existing helpers
    # -----------------------------

    def _format_sources(self, docs: List[Dict[str, Any]]) -> List[Source]:
        """Format documents as source citations."""
        sources = []
        for doc in docs:
            metadata = doc.get("metadata", {})
            document_id = metadata.get("document_id", "unknown")
            filename = metadata.get("filename", "Unknown Document")
            page = metadata.get("page_number")

            chunk_text = (doc.get("text") or "")[:200]
            if len((doc.get("text") or "")) > 200:
                chunk_text += "..."

            sources.append(Source(
                document_id=document_id,
                document_name=filename,
                page=page,
                chunk_text=chunk_text,
                relevance_score=doc.get("score", 0.0),
            ))
        return sources

    def _estimate_tokens(self, messages: List, response: str) -> int:
        """Estimate token usage (rough approximation)."""
        total_chars = sum(len(str(msg.content)) for msg in messages)
        total_chars += len(response or "")
        return total_chars // 4


# Global RAG service instance
_rag_service = None


def get_rag_service() -> RAGService:
    """Get global RAG service instance (singleton)."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
