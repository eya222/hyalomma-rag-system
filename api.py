"""
API LOCALE - À exécuter sur votre PC
Ce fichier appelle votre RAG sur Colab et ajoute les métriques d'évaluation
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import httpx
import time
from datetime import datetime
from sentence_transformers import SentenceTransformer, util

# ============================================================================
# CONFIGURATION - MODIFIEZ ICI
# ============================================================================

# ⚠️ REMPLACEZ PAR L'URL DONNÉE PAR COLAB (après avoir lancé ngrok)
COLAB_RAG_URL =  "https://minimus-sickeningly-baylee.ngrok-free.dev" # À REMPLACER !

# ============================================================================
# MODÈLES DE DONNÉES
# ============================================================================

class QueryRequest(BaseModel):
    query: str
    evaluate: bool = True  # Activer/désactiver l'évaluation

class Source(BaseModel):
    type: str
    content: str
    score: float = 0.0

class Metrics(BaseModel):
    relevance_score: float  # Pertinence des sources
    answer_quality: float   # Qualité globale
    factual_consistency: float  # Cohérence factuelle
    fluency_score: float    # Fluidité
    latency_ms: float       # Temps de réponse
    confidence: float       # Score de confiance global

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    metrics: Optional[Metrics] = None
    timestamp: str

# ============================================================================
# ÉVALUATEUR - CALCULE LES MÉTRIQUES
# ============================================================================

class RAGEvaluator:
    """Évalue la qualité des réponses RAG"""
    
    def __init__(self):
        print("📊 Chargement du modèle d'évaluation...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Modèle d'évaluation chargé\n")
    
    def evaluate(self, query: str, answer: str, sources: List[Source]) -> Metrics:
        """Calcule toutes les métriques d'évaluation"""
        
        # 1. Pertinence des sources (similarité query <-> sources)
        relevance = self._calculate_relevance(query, sources)
        
        # 2. Cohérence factuelle (similarité answer <-> sources)
        consistency = self._calculate_consistency(answer, sources)
        
        # 3. Fluidité de la réponse
        fluency = self._calculate_fluency(answer)
        
        # 4. Qualité globale
        quality = (consistency + fluency) / 2
        
        # 5. Confiance (minimum entre pertinence et qualité)
        confidence = min(relevance, quality)
        
        return Metrics(
            relevance_score=relevance,
            answer_quality=quality,
            factual_consistency=consistency,
            fluency_score=fluency,
            latency_ms=0,  # Sera rempli par l'API
            confidence=confidence
        )
    
    def _calculate_relevance(self, query: str, sources: List[Source]) -> float:
        """Calcule la pertinence des sources par rapport à la question"""
        if not sources:
            return 0.0
        
        # Encoder la question
        query_emb = self.model.encode(query, convert_to_tensor=True)
        
        # Encoder les sources
        source_texts = [s.content[:500] for s in sources]  # Limiter la taille
        source_embs = self.model.encode(source_texts, convert_to_tensor=True)
        
        # Calculer similarité cosinus
        similarities = util.cos_sim(query_emb, source_embs)[0]
        
        return float(similarities.mean())
    
    def _calculate_consistency(self, answer: str, sources: List[Source]) -> float:
        """Vérifie si la réponse est cohérente avec les sources"""
        if not answer or not sources:
            return 0.0
        
        answer_emb = self.model.encode(answer, convert_to_tensor=True)
        source_texts = [s.content[:500] for s in sources]
        source_embs = self.model.encode(source_texts, convert_to_tensor=True)
        
        similarities = util.cos_sim(answer_emb, source_embs)
        
        return float(similarities.max())
    
    def _calculate_fluency(self, text: str) -> float:
        """Évalue la fluidité du texte (heuristique simple)"""
        if not text:
            return 0.0
        
        score = 1.0
        
        # Vérifications
        if len(text.split()) < 10:
            score -= 0.3  # Trop court
        
        if text.count('.') == 0:
            score -= 0.2  # Pas de ponctuation
        
        # Vérifier les répétitions
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.5:
                score -= 0.3
        
        return max(0.0, min(1.0, score))

# ============================================================================
# API FASTAPI
# ============================================================================

app = FastAPI(
    title="API RAG Locale avec Métriques",
    description="Appelle le RAG sur Colab et ajoute des métriques d'évaluation",
    version="1.0.0"
)

# Initialiser l'évaluateur
evaluator = RAGEvaluator()

# Client HTTP pour appeler Colab
http_client = httpx.AsyncClient(timeout=60.0)

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Endpoint principal - Appelle le RAG et ajoute les métriques
    """
    start_time = time.time()
    
    try:
        print(f"\n📝 Question: {request.query}")
        
        # 1. Appeler le RAG sur Colab
        print("🔄 Appel du RAG sur Colab...")
        response = await http_client.post(
            f"{COLAB_RAG_URL}/query",
            json={
                "query": request.query,
                "context_window": 3,
                "temperature": 0.7,
                "max_tokens": 512
            }
        )
        response.raise_for_status()
        colab_result = response.json()
        
        # 2. Extraire les données
        answer = colab_result.get("answer", "")
        sources_raw = colab_result.get("sources", [])
        
        # 3. Formater les sources
        sources = [
            Source(
                type=s.get("type", "unknown"),
                content=s.get("content", "")[:500],  # Limiter
                score=0.0
            )
            for s in sources_raw
        ]
        
        # 4. Calculer les métriques (si demandé)
        metrics = None
        if request.evaluate:
            print("📊 Calcul des métriques...")
            metrics = evaluator.evaluate(request.query, answer, sources)
            
            # Ajouter la latence
            latency = (time.time() - start_time) * 1000
            metrics.latency_ms = latency
            
            print(f"✅ Métriques calculées:")
            print(f"   - Pertinence: {metrics.relevance_score:.2%}")
            print(f"   - Qualité: {metrics.answer_quality:.2%}")
            print(f"   - Confiance: {metrics.confidence:.2%}")
        
        # 5. Retourner la réponse
        return QueryResponse(
            answer=answer,
            sources=sources,
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur de connexion au RAG Colab: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Vérification de santé"""
    try:
        # Tester la connexion au Colab
        response = await http_client.get(f"{COLAB_RAG_URL}/health", timeout=5.0)
        colab_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        colab_status = "unreachable"
    
    return {
        "status": "healthy",
        "colab_rag": colab_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Page d'accueil"""
    return {
        "message": "API RAG Locale - Prête à l'emploi",
        "endpoints": {
            "query": "POST /query - Poser une question",
            "health": "GET /health - Vérifier la santé",
            "docs": "GET /docs - Documentation interactive"
        }
    }

# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*80)
    print("🚀 DÉMARRAGE DE L'API LOCALE")
    print("="*80)
    print(f"\n⚠️  Assurez-vous que:")
    print(f"   1. Colab est actif avec ngrok")
    print(f"   2. COLAB_RAG_URL est correctement configuré: {COLAB_RAG_URL}")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)