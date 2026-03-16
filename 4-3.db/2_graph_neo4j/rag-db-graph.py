text = """  
Marie Curie, born in 1867, was a Polish and naturalised-French physicist and chemist who conducted pioneering research on radioactivity.  
She was the first woman to win a Nobel Prize, the first person to win a Nobel Prize twice, and the only person to win a Nobel Prize in two scientific fields.  
Her husband, Pierre Curie, was a co-winner of her first Nobel Prize, making them the first-ever married couple to win the Nobel Prize and launching the Curie family legacy of five Nobel Prizes.  
She was, in 1906, the first woman to become a professor at the University of Paris.  
"""

# 라이브러리를 임포트한다.
from dotenv import load_dotenv  
from langchain.chains import GraphCypherQAChain  
from langchain_community.graphs import Neo4jGraph  
from langchain_core.documents import Document  
from langchain_experimental.graph_transformers import LLMGraphTransformer  
from langchain_openai import ChatOpenAI  
  
load_dotenv()  
  
# llm을 생성한다.
llm = ChatOpenAI(temperature=0, model_name="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY")) # LLM 모델 설정. gpt-4o는 실험적 모델로, 성능이 다를 수 있음
llm_transformer = LLMGraphTransformer(llm=llm) # 실험적 모듈. 언어 모델(LLM)을 사용하여 텍스트 데이터를 그래프 데이터로 변환하는 데 사용

# neo4j에 접속하고, 텍스트를 통해 문서를 만든 후, 문서를 그래프 형식으로 변환한다.
def build_graph():
    graph = Neo4jGraph(url='bolt://localhost:7687', username='neo4j', password='neo4jneo4j') # Neo4j 그래프 데이터베이스에 연결
    documents = [Document(page_content=text)]
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    graph.add_graph_documents(graph_documents)
    return graph

# 그래프 DB에 질의한다.
def query_graph(graph, query):  
    chain = GraphCypherQAChain.from_llm(graph=graph, llm=llm, verbose=True, validate_cypher=True)  
    response = chain.invoke({"query": query})  
    return response

graph = build_graph()  

response = query_graph(graph, "In what university Marie Curie was professor and when she did it?")  
print(response)
