import re
from typing import List, Dict, Any
from supabase import create_client, Client
import config
from .embeddings import GeminiEmbeddingFunction

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 
    'by', 'can', 'cannot', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 
    'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 
    'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 
    'its', 'itself', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 
    'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 
    'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 
    'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 
    'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 
    'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'would', 'you', 
    'your', 'yours', 'yourself', 'yourselves',
    'find', 'documents', 'document', 'setup', 'set', 'using', 'use', 'file', 'guide', 
    'manual', 'help', 'system', 'screen', 'error', 'issue', 'problem', 'working', 
    'work', 'steps', 'step', 'configure', 'configuration', 'install', 'installation',
    'printer', 'printers', 'device', 'devices', 'option', 'options', 'menu', 'click', 
    'press', 'select', 'page', 'button', 'window', 'display', 'check', 'verify', 'pdf', 'chm',
    'add', 'create', 'delete', 'edit', 'update', 'make', 'run', 'print', 'open', 'close', 
    'start', 'stop', 'test', 'show', 'view', 'get', 'look', 'see', 'need', 'want', 'please'
}

KNOWN_POS_ENTITIES = {
    'kyocera', 'taskalfa', 'verifone', 'toshiba', 'buypass', 'fiserv', 
    'ingenico', 'epson', 'zebra', 'rbslynk', 'mx915', 'payserver', 
    'storeman', 'reportbuilder', 'pinpad', 'invoicing', 'pricebook',
    'vendor_tab', 'vendor', 'fct_tab', 'alt_tab', 'rec_bat', 'loc', 'ssf', 'lane3000'
}

class SupabaseVectorStore:
    """Manages cloud vector database operations in Supabase pgvector with hybrid search."""

    def __init__(self, url: str = None, key: str = None, table_name: str = "documents"):
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_KEY
        self.table_name = table_name
        self.embedding_fn = GeminiEmbeddingFunction()

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured for Supabase cloud vector store.")

        self.client: Client = create_client(self.url, self.key)

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Generates embeddings and upserts document chunks into Supabase pgvector.
        Returns count of added chunks.
        """
        if not chunks:
            return 0

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_fn(texts)

        records = []
        for idx, chunk in enumerate(chunks):
            raw_emb = embeddings[idx]
            if hasattr(raw_emb, "tolist"):
                vec = raw_emb.tolist()
            else:
                vec = [float(x) for x in raw_emb]

            records.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": vec
            })

        batch_size = 50
        total_upserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            res = self.client.table(self.table_name).upsert(batch).execute()
            if res.data:
                total_upserted += len(res.data)

        return total_upserted

    def search(self, query: str, top_k: int = 6, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Executes consolidated hybrid search (vector similarity + keyword matching)
        in a single database round-trip via match_documents_hybrid RPC, with
        intelligent keyword extraction and metadata re-ranking.
        """
        # 1. Fast Google native query embedding (~50-100ms)
        raw_query_emb = self.embedding_fn.embed_query(query)
        if isinstance(raw_query_emb, list) and len(raw_query_emb) > 0:
            query_vec = raw_query_emb[0]
        else:
            query_vec = raw_query_emb

        if hasattr(query_vec, "tolist"):
            query_vec = query_vec.tolist()
        else:
            query_vec = [float(x) for x in query_vec]

        filter_json = {}
        if category_filter and category_filter not in ["General", "All Documentation", ""]:
            filter_json = {"category": category_filter}

        # 2. Extract high-specificity technical keywords (distinguishing hardware/models from stop words)
        raw_words = re.findall(r'[A-Za-z0-9_\-\.]{2,}', query)
        high_spec_terms = [w for w in raw_words if w.lower() not in STOP_WORDS and len(w) >= 3]

        primary_kw = ""
        if high_spec_terms:
            # Priority 1: Hardware model codes with digits/hyphens (e.g. 308ci, m400, a776, lane3000)
            alphanumeric_models = [w for w in high_spec_terms if any(c.isdigit() for c in w)]
            if alphanumeric_models:
                primary_kw = alphanumeric_models[0]
            else:
                # Priority 2: Known hardware/software vendor brands
                brand_terms = [w for w in high_spec_terms if w.lower() in KNOWN_POS_ENTITIES]
                if brand_terms:
                    primary_kw = brand_terms[0]
                else:
                    primary_kw = high_spec_terms[0]

        matches: List[Dict[str, Any]] = []

        # 3. Consolidated Hybrid Search in 1 DB Round-Trip
        try:
            res = self.client.rpc("match_documents_hybrid", {
                "query_embedding": query_vec,
                "query_text": primary_kw,
                "match_count": max(top_k * 3, 15),
                "filter": filter_json
            }).execute()

            if res.data:
                for row in res.data:
                    sim = float(row.get("similarity", 0.0))
                    meta = row.get("metadata", {})
                    fn = (meta.get("file_name") or "").lower()
                    tt = (meta.get("topic_title") or "").lower()

                    # Re-ranking: Boost documents whose file_name or topic_title matches query terms
                    term_matches = sum(1 for t in high_spec_terms if t.lower() in fn or t.lower() in tt)
                    final_score = sim
                    if term_matches > 0:
                        final_score = min(0.99, 0.95 + (0.02 * term_matches))
                    elif meta.get("category") == "Confirmed Fixes" and any(t.lower() in tt for t in high_spec_terms):
                        final_score = 0.99

                    matches.append({
                        "id": row.get("id"),
                        "text": row.get("text"),
                        "metadata": meta,
                        "score": final_score,
                        "distance": max(0.0, 1.0 - final_score)
                    })
        except Exception as e:
            print(f"[Supabase Warning] match_documents_hybrid RPC failed ({e}). Falling back to match_documents.")
            try:
                fallback_res = self.client.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_count": top_k,
                    "filter": filter_json
                }).execute()
                if fallback_res.data:
                    for row in fallback_res.data:
                        sim = float(row.get("similarity", 0.0))
                        matches.append({
                            "id": row.get("id"),
                            "text": row.get("text"),
                            "metadata": row.get("metadata", {}),
                            "score": sim,
                            "distance": max(0.0, 1.0 - sim)
                        })
            except Exception as fb_err:
                print(f"[Supabase Error] Fallback vector search also failed: {fb_err}")

        # 4. Check Confirmed Fixes to ensure verified field fixes are always elevated
        existing_ids = {m["id"] for m in matches}
        try:
            fixes_res = self.client.table(self.table_name).select("id, text, metadata").eq("metadata->>category", "Confirmed Fixes").execute()
            if fixes_res.data:
                for fix_row in fixes_res.data:
                    fix_id = fix_row["id"]
                    fix_meta = fix_row.get("metadata", {})
                    fix_tt = (fix_meta.get("topic_title") or "").lower()
                    fix_txt = (fix_row.get("text") or "").lower()

                    title_hits = sum(1 for t in high_spec_terms if t.lower() in fix_tt)
                    txt_hits = sum(1 for t in high_spec_terms if t.lower() in fix_txt)

                    if title_hits > 0 or txt_hits >= 2:
                        fix_score = 0.99 if title_hits > 0 else 0.96
                        if fix_id in existing_ids:
                            for m in matches:
                                if m["id"] == fix_id:
                                    m["score"] = max(m["score"], fix_score)
                        else:
                            matches.append({
                                "id": fix_id,
                                "text": fix_row.get("text"),
                                "metadata": fix_meta,
                                "score": fix_score,
                                "distance": max(0.0, 1.0 - fix_score)
                            })
                            existing_ids.add(fix_id)
        except Exception as fix_err:
            print(f"[Supabase Warning] Error checking Confirmed Fixes: {fix_err}")

        # 5. If query asks about database tables, also ensure SMSMembers Database tables topics are included
        is_table_query = any(w in query.lower() for w in ["table", "tables", "_tab", "vendor_tab", "fct_tab"])
        if is_table_query:
            try:
                table_chunks_res = self.client.table(self.table_name).select("id, text, metadata") \
                    .eq("metadata->>topic_title", "Database tables").execute()
                if table_chunks_res.data:
                    for tc in table_chunks_res.data:
                        tc_id = tc["id"]
                        tc_txt = (tc.get("text") or "").lower()
                        # If chunk contains the specific table mentioned in the query
                        if any(t.lower() in tc_txt for t in high_spec_terms if t.lower() not in ["table", "tables"]):
                            if tc_id not in existing_ids:
                                matches.append({
                                    "id": tc_id,
                                    "text": tc.get("text"),
                                    "metadata": tc.get("metadata", {}),
                                    "score": 0.98,
                                    "distance": 0.02
                                })
                                existing_ids.add(tc_id)
            except Exception as tc_err:
                print(f"[Supabase Warning] Error fetching Database tables chunks: {tc_err}")

        # 6. If we found strong exact keyword / metadata matches (>= 0.95), filter out low-relevance generic chunks (< 0.72)
        has_strong_matches = any(m["score"] >= 0.95 for m in matches)
        if has_strong_matches:
            matches = [m for m in matches if m["score"] >= 0.72]

        # 5. Sort Candidates and return top_k
        sorted_chunks = sorted(matches, key=lambda x: x["score"], reverse=True)
        return sorted_chunks[:top_k]


    def count(self) -> int:
        """Returns total document count in Supabase table."""
        try:
            # Adding limit(1) prevents downloading all IDs while still getting the exact count
            res = self.client.table(self.table_name).select("id", count="exact").limit(1).execute()
            # In the Supabase python client, count is an attribute on the response object
            return res.count if res.count is not None else 0
        except Exception as e:
            print(f"[Warning] Error getting document count: {e}")
            return 0
