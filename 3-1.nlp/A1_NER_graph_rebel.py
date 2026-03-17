# install: pip install transformers torch
import networkx as nx
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import warnings
warnings.filterwarnings('ignore')

# REBEL: End-to-End Relation Extraction 모델 (Babelscape 개발)
print("REBEL 모델 및 토크나이저 로딩 중...")

model_name = "Babelscape/rebel-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# GPU 사용 가능 여부 확인
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# pipeline 대신 사용할 래퍼 함수 정의
def triplet_extractor(text, max_length=256):
    inputs = tokenizer(text, return_tensors="pt").to(device)
    gen_kwargs = {
        "max_length": max_length,
        "length_penalty": 0,
        "num_beams": 3,
        "num_return_sequences": 1,
    }
    generated_tokens = model.generate(
        inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        **gen_kwargs,
    )
    decoded_preds = tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)
    # 기존 코드와의 호환성을 위해 리스트 안에 딕셔너리 형태로 반환
    return [{'generated_text': decoded_preds[0]}]

print("완료\n")

story_text = """
Alice is employed by Google.
Google is located in New York.
Coco is owned by Alice.
Coco is a cat.
Alice is a friend of Bob.
Bob is employed by Microsoft.
Microsoft is located in Seattle.
Charlie is employed by Amazon.
"""

print(story_text)

# REBEL로 Triple 추출
def extract_triples_rebel(text, extractor):
    """REBEL 모델의 특수 토큰 포맷을 해석하여 triple 추출"""
    triples = []

    for sentence in text.strip().split('.'):
        sentence = sentence.strip()
        if not sentence: continue

        result = extractor(sentence, max_length=256)
        extracted_text = result[0]['generated_text']

        print(f"\n[문장] {sentence}")
        print(f"[REBEL raw] {extracted_text}")

        # REBEL 포맷 파싱: <triplet> subject <subj> object <obj> relation
        current_subject, current_object, current_relation = "", "", ""
        
        # 특수 토큰 기준으로 분할
        parts = extracted_text.replace('<s>', '').replace('</s>', '').split('<triplet>')
        for part in parts:
            if not part.strip(): continue
            
            # subject <subj> object <obj> relation 구조 파싱
            if '<subj>' in part and '<obj>' in part:
                subj_split = part.split('<subj>')
                subject = subj_split[0].strip()
                
                obj_rel_parts = subj_split[1].split('<obj>')
                for i in range(len(obj_rel_parts) - 1):
                    obj = obj_rel_parts[i].strip()
                    rel = obj_rel_parts[i+1].split('<triplet>')[0].strip()
                    if subject and obj and rel:
                        print(f"  → ({subject}) --[{rel}]--> ({obj})")
                        triples.append((subject, rel, obj))

    return triples

triples = extract_triples_rebel(story_text, triplet_extractor)

print("\n최종 추출된 Triples count:", len(triples))

# 그래프 생성 및 시각화
G = nx.DiGraph()
for s, p, o in triples:
    G.add_edge(s, o, relation=p)

print("\n그래프 구조:")
for node in G.nodes():
    neighbors = list(G.neighbors(node))
    if neighbors:
        print(f"  [{node}]")
        for neighbor in neighbors:
            rel = G[node][neighbor]['relation']
            print(f"    └─ {rel} → [{neighbor}]")

import matplotlib.pyplot as plt
plt.figure(figsize=(14, 10))
# k 값을 조절하여 노드 간의 거리를 확보합니다.
pos = nx.spring_layout(G, k=1.5, iterations=50)

nx.draw(G, pos, with_labels=True, 
        node_color='skyblue', 
        node_size=3000, 
        font_size=12, 
        font_weight='bold', 
        arrows=True, 
        arrowsize=20, 
        edge_color='gray', 
        width=2)

edge_labels = nx.get_edge_attributes(G, 'relation')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, 
                              font_color='red', 
                              font_size=10, 
                              font_weight='bold')

plt.title("Knowledge Graph from REBEL Model", fontsize=15)
plt.axis('off')
plt.show()
