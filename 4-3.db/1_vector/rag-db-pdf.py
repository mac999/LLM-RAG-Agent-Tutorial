import os, re, glob
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경변수 로드

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

VECTOR_DB_PATH = './faiss_index'
FILES_DIRECTORY = './files'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

llm_model = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)

def load_and_split_pdfs(path):
	files = glob.glob(os.path.join(path, '*.pdf'))
	docs = []
	for f in files:
		loader = PyPDFLoader(f)
		docs.extend(loader.load())
	splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
	return splitter.split_documents(docs)

def save_to_faiss(docs):
	vectordb = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
	vectordb.save_local(VECTOR_DB_PATH)
	print(f"[INFO] FAISS saved to {VECTOR_DB_PATH}")
	return vectordb

def create_qa_chain(vectordb):
	retriever = vectordb.as_retriever(search_type="mmr", search_kwargs={'k': 3, 'lambda_mult': 0.25}) # top-k=3, tradeoff lambda=0.25

	output = RetrievalQA.from_chain_type(llm=llm_model, retriever=retriever, chain_type="stuff") # map_reduce, stuff, refine, map_rerank
	return output

'''
def general_llm_qa_with_memory(memory, query):
	# Retrieve chat history from memory
	chat_history = memory.load_memory_variables({}).get("chat_history", [])
	# Format the chat history for the LLM
	formatted_history = "\n".join([f"User: {msg.content}" for msg in chat_history])
	# Create a prompt with chat history and the new query
	prompt = f"""
지금까지의 대화: 메모리 내용을 기반으로 답변해줘.
{formatted_history}

사용자의 질문:
{query}

답변:"""
'''

def create_agent(qa_chain):
	memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, max_token_limit=2000)

	tools = [
		Tool(name="Expert PDF File QA", func=qa_chain.run, description="PDF에서 질문에 답변"),
		TavilySearchResults(max_results=5, tavily_api_key=TAVILY_API_KEY),
		Tool(name="General LLM QA", func=lambda query: llm_model(query), description="일반적인 질문에 답변"),
	]

	prompt = PromptTemplate(
		input_variables=["input", "chat_history"],
		template="""너는 친절하고 전문적인 코딩 Q&A 어시스턴트이다.

지금까지의 대화:
{chat_history}

사용자의 질문:
{input}

답변:"""
	)

	return initialize_agent(
		tools=tools,
		llm=llm_model,
		agent="chat-conversational-react-description",
		memory=memory,
		verbose=True,
		agent_kwargs={"prompt": prompt}
	), memory

def extract_action_input(text):
	# "action_input": "..." 패턴을 정규식으로 추출
	pattern = r'"content"\s*:\s*"([^"]+)"'
	match = re.search(pattern, text, re.DOTALL)
	if match:
		return match.group(1)  # 캡처한 "..." 안의 내용 리턴
	return None  

def clean_action_input_with_llm(text):
	prompt = f"""
다음 텍스트에서 content에 해당하는 부분만 내용을 추출해줘.
그 외의 모든 내용은 제거해. 

텍스트:
{text}
	"""

	response = llm_model.invoke(prompt)
	return response

def main():
	if not os.path.exists(VECTOR_DB_PATH):
		print("[INFO] 청킹 및 벡터 저장을 시작합니다.")
		docs = load_and_split_pdfs(FILES_DIRECTORY)
		save_to_faiss(docs)

	vectordb = FAISS.load_local(
		VECTOR_DB_PATH,
		OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
		allow_dangerous_deserialization=True
	)
	
	# test serach "mama mia" using vectordb
	docs = vectordb.similarity_search("mama mia", search_type="mmr", search_kwargs={'k': 3, 'lambda_mult': 0.25})
	for doc in docs:
		print(f"문서: {doc.metadata['source']}")
		print(f"내용: {doc.page_content}")

	qa_chain = create_qa_chain(vectordb)
	agent, memory = create_agent(qa_chain)

	print("Coding QA Expert Agent 시작됨 (터미널 입력)")
	print("종료하려면 Ctrl+C 또는 'exit' 입력")

	while True:
		try:
			query = input("\n사용자 질문: ") # 1) who is Donna in pdf? 2) in web, what is mama mia? 3) what is mama mia? 
											# 1) PDF에서 PEFT를 한글로 설명해줘. 2) PEFT를 한글로 설명해줘.
			if query.lower() in ("exit", "quit"):
				break
			answer = "잘 모르겠어요"
			answer = agent.run(query)
			print(f"답변: {answer}")
			memory.chat_memory.add_user_message(query)
			memory.chat_memory.add_ai_message(answer)
			
		except Exception as e:
			response = extract_action_input(str(e))
			if response == None:
				response = clean_action_input_with_llm(str(e))
			if response == None:
				print("답변: 잘 모르겠어요")
			else:
				print(f'답변: {response}')
				memory.chat_memory.add_user_message(query)
				memory.chat_memory.add_ai_message(answer)

if __name__ == "__main__":
	main()
