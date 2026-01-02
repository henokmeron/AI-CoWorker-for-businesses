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
from langchain_core.prompts import ChatPromptTemplate

from ..core.config import settings
from .vector_store import get_vector_store
from ..models.chat import ChatMessage, Source

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for document-based question answering with ChatGPT-grade intelligence.
    
    Features:
    - Multi-provider LLM support (OpenAI, Anthropic, Ollama)
    - Query Understanding & Rewriting (pre-retrieval optimization)
    - Multi-Pass Retrieval (broad → focused → confirmation)
    - Relevance Filtering & Reranking
    - Cross-Document Synthesis & Reasoning
    - Numerical Validation & Conflict Resolution
    - Answer Confidence Control
    - Internal Observability (comprehensive logging)
    """
    
    def __init__(self, llm_provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize RAG service.
        
        Args:
            llm_provider: LLM provider (openai, anthropic, ollama, or None for default)
            model: Model name (or None for default)
        """
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.model = model or self._get_default_model()
        self.llm = self._initialize_llm()
        self.vector_store = get_vector_store()
    
    def _get_default_model(self) -> str:
        """Get default model for provider."""
        if self.provider == "openai":
            return settings.OPENAI_MODEL
        elif self.provider == "anthropic":
            return settings.ANTHROPIC_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_MODEL
        return "gpt-4-turbo-preview"
    
    def _initialize_llm(self):
        """Initialize LLM based on provider."""
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            
            logger.info(f"Initializing OpenAI LLM with model: {self.model}")
            return ChatOpenAI(
                model=self.model,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,  # Lower temperature for more factual responses
                streaming=True
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
                    temperature=0.1
                )
            except ImportError:
                raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        
        elif self.provider == "ollama":
            logger.info(f"Initializing Ollama LLM with model: {self.model}")
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=self.model,
                temperature=0.1
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def query(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5,
        reply_as_me: bool = False
    ) -> Dict[str, Any]:
        """
        Answer a query using advanced RAG with ChatGPT-grade intelligence.
        
        Intelligence Layers:
        1. Query Understanding & Rewriting (pre-retrieval)
        2. Multi-Pass Retrieval (broad → focused → confirmation)
        3. Relevance Filtering & Reranking
        4. Cross-Document Synthesis
        5. Reasoning & Validation (numerical, conflicts, dates)
        6. Answer Confidence Control
        
        Args:
            business_id: Business identifier
            query: User question
            conversation_history: Previous conversation messages
            max_sources: Maximum number of source documents to retrieve
            reply_as_me: Whether to reply as the user
            
        Returns:
            Dictionary with answer, sources, confidence, and metadata
        """
        start_time = time.time()
        observability_log = {
            "query": query,
            "business_id": business_id,
            "stages": {}
        }
        
        try:
            # ============================================================
            # LAYER 1: Query Understanding & Rewriting
            # ============================================================
            logger.info("=" * 80)
            logger.info("🧠 LAYER 1: Query Understanding & Rewriting")
            logger.info("=" * 80)
            
            query_analysis = self._understand_and_rewrite_query(query, conversation_history)
            rewritten_query = query_analysis.get("rewritten_query", query)
            detected_entities = query_analysis.get("entities", {})
            inferred_intent = query_analysis.get("intent", "lookup")
            
            observability_log["stages"]["query_understanding"] = {
                "original": query,
                "rewritten": rewritten_query,
                "entities": detected_entities,
                "intent": inferred_intent
            }
            
            logger.info(f"📝 Original query: {query}")
            logger.info(f"✨ Rewritten query: {rewritten_query}")
            logger.info(f"🔍 Detected entities: {detected_entities}")
            logger.info(f"🎯 Inferred intent: {inferred_intent}")
            
            # ============================================================
            # LAYER 2: Multi-Pass Retrieval
            # ============================================================
            logger.info("=" * 80)
            logger.info("🔍 LAYER 2: Multi-Pass Retrieval")
            logger.info("=" * 80)
            
            retrieved_docs = self._multi_pass_retrieval(
                business_id=business_id,
                original_query=query,
                rewritten_query=rewritten_query,
                entities=detected_entities,
                intent=inferred_intent,
                max_sources=max_sources
            )
            
            observability_log["stages"]["retrieval"] = {
                "total_chunks_retrieved": len(retrieved_docs),
                "documents_found": len(set(doc.get('metadata', {}).get('document_id', '') for doc in retrieved_docs))
            }
            
            logger.info(f"📚 Retrieved {len(retrieved_docs)} chunks from multi-pass search")
            
            # ============================================================
            # LAYER 3: Relevance Filtering & Reranking
            # ============================================================
            logger.info("=" * 80)
            logger.info("🎯 LAYER 3: Relevance Filtering & Reranking")
            logger.info("=" * 80)
            
            filtered_docs = self._filter_and_rerank(
                docs=retrieved_docs,
                query=rewritten_query,
                entities=detected_entities,
                min_relevance_threshold=0.3
            )
            
            observability_log["stages"]["filtering"] = {
                "before": len(retrieved_docs),
                "after": len(filtered_docs),
                "rejected": len(retrieved_docs) - len(filtered_docs)
            }
            
            logger.info(f"✅ Filtered to {len(filtered_docs)} high-relevance chunks (rejected {len(retrieved_docs) - len(filtered_docs)} low-quality)")
            
            # ============================================================
            # LAYER 4: Cross-Document Synthesis & Reasoning
            # ============================================================
            logger.info("=" * 80)
            logger.info("🧩 LAYER 4: Cross-Document Synthesis")
            logger.info("=" * 80)
            
            context = self._format_context_for_synthesis(filtered_docs)
            messages = self._build_messages_with_reasoning(
                query=query,
                rewritten_query=rewritten_query,
                context=context,
                conversation_history=conversation_history,
                entities=detected_entities,
                intent=inferred_intent,
                has_documents=len(filtered_docs) > 0,
                reply_as_me=reply_as_me
            )
            
            # ============================================================
            # Generate Response
            # ============================================================
            logger.info("=" * 80)
            logger.info("💬 Generating response with LLM")
            logger.info("=" * 80)
            
            if self.provider == "openai" and not settings.OPENAI_API_KEY:
                raise RuntimeError("OpenAI API key is missing. Please set OPENAI_API_KEY environment variable.")
            
            try:
                response = self.llm.invoke(messages)
                answer = response.content if hasattr(response, 'content') else str(response)
                
                # Strip HTML source boxes
                answer = self._strip_html_source_boxes(answer)
                
                logger.info(f"✅ LLM response generated: {len(answer)} characters")
            except Exception as e:
                logger.error(f"❌ LLM invocation failed: {e}", exc_info=True)
                error_msg = str(e)
                if "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                    raise RuntimeError(f"OpenAI API key error: {error_msg}")
                raise RuntimeError(f"Failed to generate response: {str(e)}")
            
            # ============================================================
            # LAYER 5: Reasoning & Validation
            # ============================================================
            logger.info("=" * 80)
            logger.info("✅ LAYER 5: Reasoning & Validation")
            logger.info("=" * 80)
            
            validation_result = self._validate_and_reason(
                answer=answer,
                context_docs=filtered_docs,
                query=query,
                entities=detected_entities
            )
            
            if validation_result.get("needs_correction"):
                logger.warning(f"⚠️  Validation issues detected: {validation_result.get('issues', [])}")
                answer = validation_result.get("corrected_answer", answer)
                logger.info("🔧 Answer corrected based on validation")
            
            observability_log["stages"]["validation"] = {
                "issues_found": len(validation_result.get("issues", [])),
                "corrected": validation_result.get("needs_correction", False),
                "conflicts_detected": validation_result.get("conflicts_detected", 0)
            }
            
            # ============================================================
            # LAYER 6: Answer Confidence Control
            # ============================================================
            logger.info("=" * 80)
            logger.info("🎚️  LAYER 6: Answer Confidence Control")
            logger.info("=" * 80)
            
            confidence_assessment = self._assess_confidence(
                answer=answer,
                context_docs=filtered_docs,
                query=query
            )
            
            confidence_score = confidence_assessment.get("confidence", 0.5)
            if confidence_score < 0.6:
                logger.warning(f"⚠️  Low confidence ({confidence_score:.2f}) - adding uncertainty disclaimer")
                answer = self._add_uncertainty_disclaimer(answer, confidence_score, confidence_assessment.get("missing_info", []))
            
            observability_log["stages"]["confidence"] = {
                "score": confidence_score,
                "threshold_met": confidence_score >= 0.6,
                "disclaimer_added": confidence_score < 0.6
            }
            
            logger.info(f"📊 Confidence score: {confidence_score:.2f}")
            
            # ============================================================
            # Format Sources & Finalize
            # ============================================================
            sources = self._format_sources(filtered_docs)
            response_time = time.time() - start_time
            tokens_used = self._estimate_tokens(messages, answer)
            
            observability_log["final"] = {
                "response_time": response_time,
                "tokens_used": tokens_used,
                "sources_count": len(sources),
                "confidence": confidence_score
            }
            
            # Log full observability trace
            logger.info("=" * 80)
            logger.info("📊 OBSERVABILITY LOG")
            logger.info("=" * 80)
            logger.info(json.dumps(observability_log, indent=2, default=str))
            logger.info("=" * 80)
            
            logger.info(f"✅ Query completed in {response_time:.2f}s with {len(sources)} sources (confidence: {confidence_score:.2f})")
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence_score,
                "tokens_used": tokens_used,
                "response_time": response_time,
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                    "retrieved_docs": len(filtered_docs),
                    "query_rewritten": rewritten_query != query,
                    "entities_detected": detected_entities,
                    "intent": inferred_intent,
                    "validation_issues": len(validation_result.get("issues", [])),
                    "observability": observability_log
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in RAG query: {str(e)}", exc_info=True)
            logger.error(f"Observability log: {json.dumps(observability_log, indent=2, default=str)}")
            raise RuntimeError(f"Failed to process query: {str(e)}")
    
    # ============================================================
    # LAYER 1: Query Understanding & Rewriting
    # ============================================================
    
    def _understand_and_rewrite_query(self, query: str, conversation_history: Optional[List[ChatMessage]] = None) -> Dict[str, Any]:
        """
        Understand and rewrite query for optimal retrieval.
        
        Returns:
            Dict with rewritten_query, entities, and intent
        """
        try:
            # Build context from conversation history
            history_context = ""
            if conversation_history:
                recent = conversation_history[-3:]  # Last 3 messages
                history_lines = []
                for msg in recent:
                    if isinstance(msg, dict):
                        role = 'User' if msg.get('role') == 'user' else 'Assistant'
                        content = msg.get('content', '')
                    else:
                        role = 'Assistant'
                        content = str(msg)
                    history_lines.append(f"{role}: {content}")
                history_context = "\n".join(history_lines)
            
            # Use LLM to analyze and rewrite query
            context_part = f'Recent conversation context:\n{history_context}' if history_context else ''
            analysis_prompt = f"""Analyze this user query and rewrite it for optimal document retrieval.

Original query: {query}
{context_part}

Your task:
1. Rewrite the query to be more specific and retrieval-friendly (expand abbreviations, clarify intent)
2. Extract key entities: dates, locations, organizations, numbers, document types, age ranges, fee types, etc.
3. Infer the intent: lookup, compare, calculate, verify, summarize, etc.

Respond in JSON format:
{{
    "rewritten_query": "optimized query text",
    "entities": {{
        "dates": ["list of dates mentioned"],
        "locations": ["councils", "authorities", "places"],
        "numbers": ["ages", "amounts", "rates"],
        "document_types": ["spreadsheet", "policy", "fee schedule"],
        "fee_types": ["core", "enhanced", "complex", "solo"],
        "age_ranges": ["0-4", "5-10", "11-15", "16-17"]
    }},
    "intent": "lookup|compare|calculate|verify|summarize"
}}

Only include entities that are actually mentioned. Be precise."""
            
            try:
                analysis_messages = [
                    SystemMessage(content="You are a query analysis expert. Always respond with valid JSON only."),
                    HumanMessage(content=analysis_prompt)
                ]
                analysis_response = self.llm.invoke(analysis_messages)
                analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    return {
                        "rewritten_query": analysis.get("rewritten_query", query),
                        "entities": analysis.get("entities", {}),
                        "intent": analysis.get("intent", "lookup")
                    }
            except Exception as e:
                logger.warning(f"Query analysis failed, using original: {e}")
            
            # Fallback: simple entity extraction
            entities = self._extract_entities_simple(query)
            return {
                "rewritten_query": query,
                "entities": entities,
                "intent": "lookup"
            }
        except Exception as e:
            logger.error(f"Error in query understanding: {e}")
            return {
                "rewritten_query": query,
                "entities": {},
                "intent": "lookup"
            }
    
    def _extract_entities_simple(self, query: str) -> Dict[str, List[str]]:
        """Simple regex-based entity extraction as fallback."""
        entities = {
            "dates": [],
            "locations": [],
            "numbers": [],
            "document_types": [],
            "fee_types": [],
            "age_ranges": []
        }
        
        # Extract dates (YYYY, YYYY-MM-DD, "October 2025", etc.)
        date_patterns = [
            r'\d{4}',  # Years
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Dates
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}'
        ]
        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, query, re.IGNORECASE))
        
        # Extract numbers (ages, amounts)
        numbers = re.findall(r'\d+(?:\.\d+)?', query)
        entities["numbers"] = numbers[:10]  # Limit
        
        # Extract common fee types
        fee_keywords = ["core", "enhanced", "complex", "solo", "parent/baby", "remand"]
        entities["fee_types"] = [kw for kw in fee_keywords if kw.lower() in query.lower()]
        
        # Extract age ranges
        age_pattern = r'(\d+)[-\s]*(?:year|yr|age)'
        entities["age_ranges"] = re.findall(age_pattern, query, re.IGNORECASE)
        
        return entities
    
    # ============================================================
    # LAYER 2: Multi-Pass Retrieval
    # ============================================================
    
    def _multi_pass_retrieval(
        self,
        business_id: str,
        original_query: str,
        rewritten_query: str,
        entities: Dict[str, Any],
        intent: str,
        max_sources: int
    ) -> List[Dict[str, Any]]:
        """
        Perform multi-pass retrieval: broad → focused → confirmation.
        """
        all_chunks = []
        seen_chunk_ids = set()
        
        try:
            # Check collection exists
            collection = self.vector_store.get_collection(business_id)
            if not collection or (hasattr(collection, 'count') and collection.count() == 0):
                logger.warning(f"Collection '{business_id}' is empty or doesn't exist")
                return []
        except Exception as e:
            logger.error(f"Cannot access collection: {e}")
            return []
        
        # PASS 1: Broad semantic retrieval
        logger.info("🔍 PASS 1: Broad semantic retrieval")
        broad_k = max(max_sources * 4, 30)
        broad_results = self.vector_store.search(
            business_id=business_id,
            query=rewritten_query,
            k=broad_k
        )
        logger.info(f"   Found {len(broad_results)} chunks in broad search")
        
        for chunk in broad_results:
            chunk_id = chunk.get('id') or chunk.get('text', '')[:50]
            if chunk_id not in seen_chunk_ids:
                all_chunks.append(chunk)
                seen_chunk_ids.add(chunk_id)
        
        # PASS 2: Focused retrieval using entities
        if entities and any(entities.values()):
            logger.info("🎯 PASS 2: Focused retrieval using entities")
            entity_queries = []
            
            # Build entity-based queries
            if entities.get("locations"):
                entity_queries.append(" ".join(entities["locations"][:3]))
            if entities.get("fee_types"):
                entity_queries.append(" ".join(entities["fee_types"]))
            if entities.get("age_ranges"):
                entity_queries.append(" ".join(entities["age_ranges"]))
            
            for entity_query in entity_queries[:2]:  # Limit to 2 entity queries
                focused_results = self.vector_store.search(
                    business_id=business_id,
                    query=f"{rewritten_query} {entity_query}",
                    k=max_sources * 2
                )
                for chunk in focused_results:
                    chunk_id = chunk.get('id') or chunk.get('text', '')[:50]
                    if chunk_id not in seen_chunk_ids:
                        all_chunks.append(chunk)
                        seen_chunk_ids.add(chunk_id)
                logger.info(f"   Entity query '{entity_query}' found {len(focused_results)} additional chunks")
        
        # PASS 3: Cross-document confirmation (if we have multiple documents)
        if len(set(doc.get('metadata', {}).get('document_id', '') for doc in all_chunks)) > 1:
            logger.info("🔗 PASS 3: Cross-document confirmation retrieval")
            # Search for chunks that might confirm or contradict findings
            confirmation_results = self.vector_store.search(
                business_id=business_id,
                query=f"confirm verify {rewritten_query}",
                k=max_sources
            )
            for chunk in confirmation_results:
                chunk_id = chunk.get('id') or chunk.get('text', '')[:50]
                if chunk_id not in seen_chunk_ids:
                    all_chunks.append(chunk)
                    seen_chunk_ids.add(chunk_id)
            logger.info(f"   Found {len(confirmation_results)} confirmation chunks")
        
        # Sort by relevance score and deduplicate
        all_chunks = sorted(all_chunks, key=lambda x: x.get('score', 0), reverse=True)
        
        # Remove exact duplicates (same text)
        unique_chunks = []
        seen_texts = set()
        for chunk in all_chunks:
            text_hash = hash(chunk.get('text', '')[:100])
            if text_hash not in seen_texts:
                unique_chunks.append(chunk)
                seen_texts.add(text_hash)
        
        logger.info(f"✅ Multi-pass retrieval: {len(unique_chunks)} unique chunks from {len(all_chunks)} total")
        
        return unique_chunks
    
    # ============================================================
    # LAYER 3: Relevance Filtering & Reranking
    # ============================================================
    
    def _filter_and_rerank(
        self,
        docs: List[Dict[str, Any]],
        query: str,
        entities: Dict[str, Any],
        min_relevance_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Filter and rerank chunks by relevance.
        """
        if not docs:
            return []
        
        filtered = []
        
        for doc in docs:
            score = doc.get('score', 0.0)
            text = doc.get('text', '').lower()
            query_lower = query.lower()
            
            # Basic relevance checks
            relevance_issues = []
            
            # Check 1: Minimum similarity threshold
            if score < min_relevance_threshold:
                relevance_issues.append(f"Low similarity score: {score:.3f}")
                continue
            
            # Check 2: Query terms should appear in text
            query_words = set(query_lower.split())
            text_words = set(text.split())
            overlap = len(query_words.intersection(text_words)) / max(len(query_words), 1)
            if overlap < 0.1:  # At least 10% word overlap
                relevance_issues.append(f"Low term overlap: {overlap:.2f}")
                continue
            
            # Check 3: Entity matching (bonus)
            entity_match_bonus = 0.0
            if entities:
                for entity_type, entity_values in entities.items():
                    for entity in entity_values:
                        if isinstance(entity, str) and entity.lower() in text:
                            entity_match_bonus += 0.1
            
            # Adjust score with entity bonus
            adjusted_score = min(score + entity_match_bonus, 1.0)
            doc['adjusted_score'] = adjusted_score
            
            filtered.append(doc)
        
        # Rerank by adjusted score
        filtered = sorted(filtered, key=lambda x: x.get('adjusted_score', x.get('score', 0)), reverse=True)
        
        # Limit to top results
        max_chunks = 15  # Reasonable limit for context
        filtered = filtered[:max_chunks]
        
        logger.info(f"   Filtered: {len(filtered)}/{len(docs)} chunks passed relevance checks")
        
        return filtered
    
    # ============================================================
    # LAYER 4: Cross-Document Synthesis Formatting
    # ============================================================
    
    def _format_context_for_synthesis(self, docs: List[Dict[str, Any]]) -> str:
        """
        Format context to encourage cross-document reasoning.
        """
        if not docs:
            return ""
        
        # Group by document
        docs_by_document = {}
        for doc in docs:
            doc_id = doc.get('metadata', {}).get('document_id', 'unknown')
            if doc_id not in docs_by_document:
                docs_by_document[doc_id] = {
                    "filename": doc.get('metadata', {}).get('filename', 'Unknown'),
                    "chunks": []
                }
            docs_by_document[doc_id]["chunks"].append(doc)
        
        context_parts = []
        context_parts.append("=" * 80)
        context_parts.append("DOCUMENT CONTEXT (Multiple documents - reason across them)")
        context_parts.append("=" * 80)
        
        for doc_id, doc_info in docs_by_document.items():
            filename = doc_info["filename"]
            chunks = doc_info["chunks"]
            
            context_parts.append(f"\n--- Document: {filename} (ID: {doc_id}) ---")
            for i, chunk in enumerate(chunks, 1):
                metadata = chunk.get("metadata", {})
                page = metadata.get("page_number", "")
                score = chunk.get('adjusted_score', chunk.get('score', 0))
                
                page_info = f" (Page {page})" if page else ""
                context_parts.append(f"\n[Chunk {i}{page_info} - Relevance: {score:.3f}]")
                context_parts.append(chunk['text'])
        
        context_parts.append("\n" + "=" * 80)
        context_parts.append("INSTRUCTIONS: Compare, reconcile, and synthesize information across ALL documents above.")
        context_parts.append("If documents disagree, identify the conflict and explain which source is used and why.")
        context_parts.append("=" * 80)
        
        return "\n".join(context_parts)
    
    def _format_context(self, docs: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string.
        
        Args:
            docs: Retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page_number", "")
            
            page_info = f" (Page {page})" if page else ""
            context_parts.append(
                f"[Source {i}: {filename}{page_info}]\n{doc['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_messages_with_reasoning(
        self,
        query: str,
        rewritten_query: str,
        context: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        entities: Dict[str, Any] = None,
        intent: str = "lookup",
        has_documents: bool = False,
        reply_as_me: bool = False
    ) -> List:
        """
        Build messages with enhanced reasoning instructions.
        """
        if reply_as_me:
            if has_documents and context:
                system_prompt = """You are helping the user craft personalized responses based on provided documents.

When answering:
- Write responses as if the user is writing them
- Use information from the provided documents when available
- Compare and reconcile information across multiple documents
- Maintain a natural, personal tone
- Cite sources when referencing documents
- Be concise and accurate"""
            else:
                system_prompt = """You are helping the user craft personalized responses. Write as if the user is writing, maintaining a natural and personal tone."""
        else:
            if has_documents and context:
                system_prompt = """You are an expert AI assistant that answers questions by reasoning across multiple documents.

CRITICAL INSTRUCTIONS:
1. You have access to MULTIPLE documents. You MUST reason across ALL of them, not just one.
2. When documents contain related information:
   - COMPARE values, rates, dates, and policies across documents
   - RECONCILE differences (e.g., if one doc says £1000 and another says £1200, identify which is correct and why)
   - AGGREGATE information when appropriate (e.g., total fees across age ranges)
   - RESOLVE conflicts by preferring:
     * Newer documents over older ones
     * More specific documents over general ones
     * Documents with explicit "effective from" dates
3. When answering:
   - ALWAYS check ALL documents before answering
   - If information appears in multiple documents, cite all relevant sources
   - If documents disagree, explicitly state the conflict and which source you're using
   - Extract dates and ensure you're using rates/policies from the correct time period
   - Perform calculations accurately (double-check math)
4. Be precise with numbers, dates, and rates. Never mix data from different time periods.
5. If you're uncertain, say so clearly rather than guessing."""
            else:
                from datetime import datetime
                current_date = datetime.now().strftime("%B %d, %Y")
                system_prompt = f"""You are a helpful AI assistant powered by GPT-4o. Answer questions clearly and accurately based on your knowledge as of {current_date}.

IMPORTANT: No documents were found in the vector database. If the user asks about uploaded files, inform them that documents were not found."""
        
        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                elif hasattr(msg, 'role'):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add current query with context
        if has_documents and context:
            user_message = f"""{context}

Question: {query}
{f'Detected entities: {entities}' if entities else ''}
Intent: {intent}

Please provide a comprehensive answer by reasoning across all documents. Compare, reconcile, and synthesize information. Be precise with numbers and dates."""
        else:
            user_message = query
        
        messages.append(HumanMessage(content=user_message))
        return messages
    
    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        has_documents: bool = False,
        reply_as_me: bool = False
    ) -> List:
        """
        Build message list for LLM.
        
        Args:
            query: User question
            context: Retrieved context (empty if no documents)
            conversation_history: Previous messages
            has_documents: Whether documents were found
            
        Returns:
            List of messages for LLM
        """
        # System prompt adapts based on whether we have documents and reply mode
        if reply_as_me:
            # Reply as the user (personalized responses)
            if has_documents and context:
                system_prompt = """You are helping the user craft personalized responses based on provided documents.

When answering:
- Write responses as if the user is writing them
- Use information from the provided documents when available
- Maintain a natural, personal tone
- Cite sources when referencing documents
- Be concise and accurate"""
            else:
                system_prompt = """You are helping the user craft personalized responses. Write as if the user is writing, maintaining a natural and personal tone."""
        else:
            # Categorize only mode (default)
            if has_documents and context:
                system_prompt = """You are a helpful AI assistant that answers questions based on uploaded documents.

CRITICAL: The user has uploaded documents. You MUST use the document content provided below to answer their questions.

When answering:
- ALWAYS check the provided documents first before answering
- Use information from the provided documents to answer the user's questions
- Cite sources when referencing documents (e.g., "According to Source 1...")
- If the user asks about "attached file", "uploaded document", or mentions a file name, the information is in the documents below
- Be accurate and specific, using the document content to answer
- If information isn't in the documents, say so clearly
- DO NOT say you can't access documents - the documents are provided below"""
            else:
                from datetime import datetime
                current_date = datetime.now().strftime("%B %d, %Y")
                system_prompt = f"""You are a helpful AI assistant powered by GPT-4o. Answer questions clearly and accurately based on your knowledge as of {current_date}.

IMPORTANT: The user may have uploaded documents, but no documents were found in the vector database for this conversation. This could mean:
1. The document upload failed or is still processing
2. The document was uploaded to a different conversation/business_id
3. The vector database search failed

If the user asks about a specific file or document they mentioned uploading, please inform them that you cannot find that document in the system. Suggest they:
- Check if the upload completed successfully
- Try uploading the document again
- Verify they are asking questions in the same conversation where they uploaded the file

Be helpful, concise, and informative. When providing information, use current knowledge and avoid referencing outdated dates like "as of 2023" unless specifically asked about historical events. Always use the current date ({current_date}) as your knowledge cutoff."""

        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                # Handle both dict and object formats
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                elif hasattr(msg, 'role'):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add current query with or without context
        if has_documents and context:
            user_message = f"""Context from business documents:

{context}

Question: {query}

Please provide a helpful answer, citing sources when relevant."""
        else:
            # No documents - just answer the question directly
            user_message = query

        messages.append(HumanMessage(content=user_message))
        
        return messages
    
    def _format_sources(self, docs: List[Dict[str, Any]]) -> List[Source]:
        """
        Format documents as source citations.
        
        Args:
            docs: Retrieved documents
            
        Returns:
            List of Source objects
        """
        sources = []
        
        for doc in docs:
            metadata = doc.get("metadata", {})
            
            # Extract document info
            document_id = metadata.get("document_id", "unknown")
            filename = metadata.get("filename", "Unknown Document")
            page = metadata.get("page_number")
            
            # Create preview of chunk text (first 200 chars)
            chunk_text = doc['text'][:200]
            if len(doc['text']) > 200:
                chunk_text += "..."
            
            sources.append(Source(
                document_id=document_id,
                document_name=filename,
                page=page,
                chunk_text=chunk_text,
                relevance_score=doc.get("score", 0.0)
            ))
        
        return sources
    
    # ============================================================
    # LAYER 5: Reasoning & Validation
    # ============================================================
    
    def _validate_and_reason(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
        query: str,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate answer for numerical accuracy, conflicts, and date awareness.
        """
        issues = []
        conflicts_detected = 0
        needs_correction = False
        corrected_answer = answer
        
        # Extract numbers from answer
        numbers_in_answer = re.findall(r'\d+(?:\.\d+)?', answer)
        
        # Extract numbers from context
        numbers_in_context = []
        dates_in_context = []
        for doc in context_docs:
            text = doc.get('text', '')
            numbers_in_context.extend(re.findall(r'\d+(?:\.\d+)?', text))
            # Extract dates
            dates_in_context.extend(re.findall(r'\d{4}', text))
            dates_in_context.extend(re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', text, re.IGNORECASE))
        
        # Check 1: Numerical validation
        if numbers_in_answer:
            # Check if numbers in answer appear in context
            answer_numbers_set = set(numbers_in_answer)
            context_numbers_set = set(numbers_in_context)
            missing_numbers = answer_numbers_set - context_numbers_set
            
            if missing_numbers:
                # Some numbers not found in context - might be hallucinated
                issues.append(f"Numbers in answer not found in context: {missing_numbers}")
                logger.warning(f"⚠️  Numerical validation: {len(missing_numbers)} numbers not found in context")
        
        # Check 2: Date awareness
        dates_in_answer = re.findall(r'\d{4}', answer)
        if dates_in_answer and dates_in_context:
            answer_dates_set = set(dates_in_answer)
            context_dates_set = set(dates_in_context)
            if not answer_dates_set.intersection(context_dates_set):
                issues.append("Dates in answer don't match dates in documents")
                logger.warning("⚠️  Date mismatch detected")
        
        # Check 3: Conflict detection (if multiple documents with different values)
        if len(context_docs) > 1:
            # Look for conflicting numbers (same entity, different values)
            doc_values = {}
            for doc in context_docs:
                doc_id = doc.get('metadata', {}).get('document_id', 'unknown')
                text = doc.get('text', '')
                # Extract fee-related numbers
                fee_numbers = re.findall(r'£?\s*(\d+(?:\.\d+)?)', text)
                if fee_numbers:
                    doc_values[doc_id] = fee_numbers
            
            # Check for conflicts
            if len(set(str(v) for v in doc_values.values())) > 1:
                conflicts_detected = len(doc_values)
                issues.append(f"Conflicting values detected across {conflicts_detected} documents")
                logger.warning(f"⚠️  Conflict detected: {conflicts_detected} documents have different values")
        
        # If issues found, attempt correction via LLM
        if issues:
            try:
                correction_prompt = f"""The following answer was generated, but validation found issues:

Answer: {answer}

Validation Issues:
{chr(10).join(f'- {issue}' for issue in issues)}

Context Documents:
{self._format_context(context_docs[:5])}

Please correct the answer to:
1. Only use numbers that appear in the context documents
2. Use dates that match the documents
3. If documents conflict, explicitly state which document you're using and why
4. Remove any information not supported by the context

Provide the corrected answer:"""
                
                correction_messages = [
                    SystemMessage(content="You are a validation expert. Correct answers based on context documents."),
                    HumanMessage(content=correction_prompt)
                ]
                
                correction_response = self.llm.invoke(correction_messages)
                corrected_answer = correction_response.content if hasattr(correction_response, 'content') else str(correction_response)
                needs_correction = True
                logger.info("🔧 Answer corrected based on validation")
            except Exception as e:
                logger.warning(f"Correction attempt failed: {e}")
        
        return {
            "issues": issues,
            "conflicts_detected": conflicts_detected,
            "needs_correction": needs_correction,
            "corrected_answer": corrected_answer
        }
    
    # ============================================================
    # LAYER 6: Answer Confidence Control
    # ============================================================
    
    def _assess_confidence(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Assess confidence in the answer.
        """
        if not context_docs:
            return {
                "confidence": 0.3,
                "missing_info": ["No documents found"],
                "reason": "No context available"
            }
        
        confidence_factors = []
        missing_info = []
        
        # Factor 1: Number of relevant documents
        doc_count = len(context_docs)
        if doc_count >= 5:
            confidence_factors.append(0.9)
        elif doc_count >= 3:
            confidence_factors.append(0.7)
        elif doc_count >= 1:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.2)
        
        # Factor 2: Average relevance score
        avg_score = sum(doc.get('adjusted_score', doc.get('score', 0)) for doc in context_docs) / len(context_docs)
        confidence_factors.append(avg_score)
        
        # Factor 3: Answer completeness (check for uncertainty markers)
        uncertainty_markers = ["unclear", "uncertain", "not found", "unavailable", "cannot determine"]
        has_uncertainty = any(marker in answer.lower() for marker in uncertainty_markers)
        if has_uncertainty:
            confidence_factors.append(0.4)
        else:
            confidence_factors.append(0.8)
        
        # Factor 4: Query coverage (does answer address the query?)
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        coverage = len(query_words.intersection(answer_words)) / max(len(query_words), 1)
        confidence_factors.append(coverage)
        
        # Calculate overall confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        # Identify missing information
        if doc_count < 3:
            missing_info.append("Limited document coverage")
        if avg_score < 0.5:
            missing_info.append("Low relevance scores")
        if coverage < 0.3:
            missing_info.append("Answer may not fully address query")
        
        return {
            "confidence": confidence,
            "missing_info": missing_info,
            "factors": {
                "doc_count": doc_count,
                "avg_score": avg_score,
                "coverage": coverage
            }
        }
    
    def _add_uncertainty_disclaimer(self, answer: str, confidence: float, missing_info: List[str]) -> str:
        """
        Add uncertainty disclaimer to low-confidence answers.
        """
        if confidence >= 0.6:
            return answer
        
        disclaimer = "\n\n⚠️ Note: The available documents may not contain complete information to fully answer this question."
        if missing_info:
            disclaimer += f" Limitations: {', '.join(missing_info)}."
        disclaimer += " Please verify critical information from original sources."
        
        return answer + disclaimer
    
    def _strip_html_source_boxes(self, text: str) -> str:
        """Strip HTML source boxes from text."""
        # Remove source-box divs
        text = re.sub(r'<div\s+class\s*=\s*["\']source-box["\']>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<div\s+class\s*=\s*source-box>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove source markers
        text = re.sub(r'<strong>Source\s+\d+.*?</strong>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<em>Relevance:.*?</em>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove Sources emoji and text
        text = re.sub(r'📚\s*Sources?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<details.*?Sources?.*?</details>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Clean up whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'\s{3,}', ' ', text)
        return text.strip()
    
    def _estimate_tokens(self, messages: List, response: str) -> int:
        """
        Estimate token usage (rough approximation).
        
        Args:
            messages: Input messages
            response: Generated response
            
        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token
        total_chars = sum(len(str(msg.content)) for msg in messages)
        total_chars += len(response)
        return total_chars // 4
    
    async def query_stream(
        self,
        business_id: str,
        query: str,
        conversation_history: List[ChatMessage] = None,
        max_sources: int = 5
    ):
        """
        Answer a query with streaming response (uses intelligence layers).
        
        Args:
            business_id: Business identifier
            query: User question
            conversation_history: Previous conversation messages
            max_sources: Maximum number of source documents to retrieve
            
        Yields:
            Response chunks
        """
        # Use intelligence layers for retrieval
        query_analysis = self._understand_and_rewrite_query(query, conversation_history)
        rewritten_query = query_analysis.get("rewritten_query", query)
        entities = query_analysis.get("entities", {})
        intent = query_analysis.get("intent", "lookup")
        
        # Multi-pass retrieval
        retrieved_docs = self._multi_pass_retrieval(
            business_id=business_id,
            original_query=query,
            rewritten_query=rewritten_query,
            entities=entities,
            intent=intent,
            max_sources=max_sources
        )
        
        # Filter and rerank
        filtered_docs = self._filter_and_rerank(
            docs=retrieved_docs,
            query=rewritten_query,
            entities=entities,
            min_relevance_threshold=0.3
        )
        
        if not filtered_docs:
            yield {"type": "answer", "content": "No relevant documents found to answer this question."}
            return
        
        # Build messages with reasoning
        context = self._format_context_for_synthesis(filtered_docs)
        messages = self._build_messages_with_reasoning(
            query=query,
            rewritten_query=rewritten_query,
            context=context,
            conversation_history=conversation_history,
            entities=entities,
            intent=intent,
            has_documents=True,
            reply_as_me=False
        )
        
        # Stream response
        full_answer = ""
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                full_answer += chunk.content
                yield {"type": "answer", "content": chunk.content}
        
        # Strip HTML and validate (post-processing)
        full_answer = self._strip_html_source_boxes(full_answer)
        
        # Send sources at the end
        sources = self._format_sources(filtered_docs)
        yield {"type": "sources", "content": [s.dict() for s in sources]}


# Global RAG service instance
_rag_service = None


def get_rag_service() -> RAGService:
    """
    Get global RAG service instance (singleton).
    
    Returns:
        RAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


