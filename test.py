"""
Script de test simple - À exécuter sur votre PC
"""

import requests
import json

# URL de votre API locale
API_URL = "http://localhost:8000"

def test_health():
    """Test 1: Vérifier que tout fonctionne"""
    print("\n" + "="*80)
    print("TEST 1: VÉRIFICATION DE SANTÉ")
    print("="*80)
    
    response = requests.get(f"{API_URL}/health")
    result = response.json()
    
    print(f"\n✅ Statut API locale: {result['status']}")
    print(f"✅ Statut Colab RAG: {result['colab_rag']}")
    print(f"⏰ Timestamp: {result['timestamp']}")
    
    if result['colab_rag'] != 'healthy':
        print("\n⚠️  ATTENTION: Le RAG Colab n'est pas accessible!")
        print("   Vérifiez que Colab est actif et que l'URL est correcte")
        return False
    
    return True

def test_simple_query():
    """Test 2: Question simple"""
    print("\n" + "="*80)
    print("TEST 2: QUESTION SIMPLE")
    print("="*80)
    
    question = "What are the genetic markers for Hyalomma marginatum?"
    
    print(f"\n❓ Question: {question}")
    print("🔄 Envoi de la requête...")
    
    response = requests.post(
        f"{API_URL}/query",
        json={
            "query": question,
            "evaluate": True
        }
    )
    
    if response.status_code != 200:
        print(f"\n❌ Erreur: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    
    # Afficher la réponse
    print("\n" + "-"*80)
    print("RÉPONSE:")
    print("-"*80)
    print(result['answer'])
    
    # Afficher les métriques
    if result.get('metrics'):
        print("\n" + "-"*80)
        print("📊 MÉTRIQUES D'ÉVALUATION:")
        print("-"*80)
        metrics = result['metrics']
        print(f"   Pertinence des sources: {metrics['relevance_score']:.2%}")
        print(f"   Qualité de la réponse: {metrics['answer_quality']:.2%}")
        print(f"   Cohérence factuelle: {metrics['factual_consistency']:.2%}")
        print(f"   Fluidité: {metrics['fluency_score']:.2%}")
        print(f"   Temps de réponse: {metrics['latency_ms']:.0f}ms")
        print(f"   Confiance globale: {metrics['confidence']:.2%}")
    
    # Afficher les sources
    print("\n" + "-"*80)
    print(f"📚 SOURCES UTILISÉES: {len(result['sources'])}")
    print("-"*80)
    for i, source in enumerate(result['sources'], 1):
        print(f"\n{i}. Type: {source['type']}")
        print(f"   Extrait: {source['content'][:200]}...")

def test_multiple_queries():
    """Test 3: Plusieurs questions"""
    print("\n" + "="*80)
    print("TEST 3: PLUSIEURS QUESTIONS")
    print("="*80)
    
    questions = [
        "Where is Hyalomma marginatum found?",
        "What diseases does it transmit?",
        "What are its hosts?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"❓ {question}")
        
        response = requests.post(
            f"{API_URL}/query",
            json={"query": question, "evaluate": True}
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['answer'][:150]  # Tronquer
            confidence = result.get('metrics', {}).get('confidence', 0)
            
            print(f"💬 Réponse: {answer}...")
            print(f"📊 Confiance: {confidence:.2%}")
        else:
            print(f"❌ Erreur: {response.status_code}")

def test_without_evaluation():
    """Test 4: Sans évaluation (plus rapide)"""
    print("\n" + "="*80)
    print("TEST 4: SANS ÉVALUATION (MODE RAPIDE)")
    print("="*80)
    
    question = "What is Hyalomma marginatum?"
    
    print(f"\n❓ Question: {question}")
    
    import time
    start = time.time()
    
    response = requests.post(
        f"{API_URL}/query",
        json={"query": question, "evaluate": False}  # Pas d'évaluation
    )
    
    duration = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n💬 Réponse: {result['answer'][:200]}...")
        print(f"⏱️  Temps total: {duration:.2f}s")
        print(f"📊 Métriques: {'Désactivées' if not result.get('metrics') else 'Activées'}")

def main():
    """Exécute tous les tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "TESTS API RAG" + " "*40 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        # Test 1: Santé
        if not test_health():
            print("\n❌ Tests arrêtés - API non accessible")
            return
        
        # Test 2: Question simple
        test_simple_query()
        
        # Test 3: Plusieurs questions
        test_multiple_queries()
        
        # Test 4: Sans évaluation
        test_without_evaluation()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS TERMINÉS")
        print("="*80 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR: Impossible de se connecter à l'API locale")
        print("   Vérifiez que api_locale.py est lancé (python api_locale.py)")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")

if __name__ == "__main__":
    main()