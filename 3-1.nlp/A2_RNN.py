import torch
import torch.nn as nn
import torch.optim as optim

# 1. 간단한 학습 데이터
texts = [
    "오늘 날씨가 좋아서 친구와 공원으로 산책을 갔다",
    "나는 학교에 간다",
    "우리는 공원에 간다",
    "나는 밥을 먹는다",
    "너는 물을 마신다",
    "우리는 공부를 한다",
    "나는 책을 읽는다",
    "너는 음악을 듣는다"
]

# 2. 어휘 구축
words = set()
for text in texts:
    words.update(text.split()) # 단어 단위로 분리하여 집합에 추가
vocab = sorted(list(words))
word2idx = {w: i for i, w in enumerate(vocab)} # 단어를 인덱스로 매핑
idx2word = {i: w for w, i in word2idx.items()} # 인덱스를 단어로 매핑

print(f"어휘 크기: {len(vocab)}")
print(f"단어 목록: {vocab}")

# 3. 학습 데이터 생성 (2개 단어 -> 다음 단어)
X, y = [], []
for text in texts:
    words = text.split()
    for i in range(len(words) - 2):
        X.append([word2idx[words[i]], word2idx[words[i+1]]]) # 두 단어의 인덱스
        y.append(word2idx[words[i+2]]) # 다음 단어의 인덱스

X = torch.LongTensor(X)
y = torch.LongTensor(y)
print(f"\n학습 샘플 수: {len(X)}")

# 4. RNN 모델 정의
class SimpleRNN(nn.Module):
    def __init__(self, vocab_size, embed_dim=16, hidden_dim=32):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim) # 임베딩 레이어. 단어 수, 임베딩 차원
        self.rnn = nn.RNN(embed_dim, hidden_dim, batch_first=True) # RNN 레이어. 입력 차원, 은닉 상태 차원
        self.fc = nn.Linear(hidden_dim, vocab_size) # 출력 레이어. 은닉 상태 차원, 단어 수
    
    def forward(self, x):
        x = self.embedding(x)
        _, hidden = self.rnn(x)
        return self.fc(hidden.squeeze(0))

model = SimpleRNN(len(vocab))

# 5. 학습
criterion = nn.CrossEntropyLoss() # 다중 클래스 분류를 위한 손실함수 (다음 단어 예측)
optimizer = optim.Adam(model.parameters(), lr=0.01) # Adam 옵티마이저

print("\n학습 시작...")
for epoch in range(100):
    optimizer.zero_grad() # 기울기 초기화
    output = model(X) # 모델 순전파
    loss = criterion(output, y) # 손실 계산
    loss.backward() # 역전파
    optimizer.step() # 가중치 갱신
    
    if (epoch + 1) % 20 == 0:
        print(f"Epoch {epoch+1}, Loss: {loss.item():.4f}")

# 6. 재귀적 단어 토큰 예측 함수
def predict_sequence(text, max_length=10, min_prob=0.9): # 최소 확률 0.9로 설정
    words = text.split()
    
    if len(words) < 2 or any(w not in word2idx for w in words): # 입력 검증
        return "입력 오류: 최소 2개의 유효한 단어 필요"
    
    generated = words[-2:] # 초기 시퀀스
    for _ in range(max_length): # 재귀 예측 루프
        input_tensor = torch.LongTensor([[word2idx[w] for w in generated[-2:]]])
        
        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.softmax(output, dim=1) # 확률 계산
            max_prob, pred_idx = probs.max(1) # 가장 높은 확률과 인덱스 값
        
        if max_prob.item() < min_prob: # 예측 단어 중 낮은 확률이면 생성 중지
            break
        generated.append(idx2word[pred_idx.item()])
    
    return " ".join(generated)
    
# 7. 테스트
model.eval()

print("\n재귀적 시퀀스 예측 테스트:")
test_cases = ["오늘 날씨가", "나는 학교에", "나는 책을"]
for test in test_cases:
    result = predict_sequence(test, max_length=8)
    print(f"{test} -> {result}")
