import sys, os, json, argparse, re, textwrap, ast, subprocess, sys
from typing import List, Dict, Any, get_type_hints
from langchain_core.runnables import RunnablePassthrough, chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.schema import StrOutputParser

# define LLM model, chains and query function
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1) # temperature=0.3)
memory = ConversationBufferMemory(
	memory_key="chat_history",
	return_messages=True
)

def query_llm(chains, prompt: str, save_memory=False) -> str:
	memory_contents = memory.load_memory_variables({})['chat_history']
	response = chains.invoke({"input": prompt, "chat_history": memory_contents})  # "agent_scratchpad": []})
	if save_memory:
		memory.save_context({"input": prompt}, {"output": response.response})
	print(f'* LLM Answer *\n{response.content}\n* End of Answer *\n')
	return response

# define functions for executing script code like Python
def check_safe_eval(express):
	tokens = express.split()

	try:
		if tokens.index("import") < 0:
			return 
		unsafe_libs = ["os", "shutil", "subprocess", "ctypes", "pickle", "http", "socket", "eval", "exec"]
		unsafe = False
		for lib in unsafe_libs:
			try:
				if tokens.index(lib) >= 0:
					unsafe = True
					break
			except ValueError:
				pass

		if unsafe:
			raise Exception(f"{express} is not safe.")
	except ValueError:
		pass
	return 

def preprocess_code(text: str) -> str:
	try:
		match = re.search(r'```python\n(.*?)```', text, re.DOTALL) # extract code from text between ```python\n and ```
		code = match.group(1).strip()
		code = code.replace('\t', '    ')
		code = textwrap.dedent(code)
		check_safe_eval(code)
		ast.parse(code)
		print('\n* Generated Python code *')
		print(code)
		print('* End of Python code *\n')
	except IndentationError as e:
		print(f"IndentationError detected: {e}")
		code = ''
	except SyntaxError as e:
		print(f"SyntaxError detected: {e}")
		code = ''
	except Exception as e:
		print(f"Error: {e}")
		code = ''
	return code

# Define function call tools (example: GeoAI, BIM, Robot)
def g1():
	'''
	load file in GeoAI
	'''
	print("g1")

def g2(a: int, b: int) -> Dict[str, Any]:
	'''
	sampling file in GeoAI
	'''
	c = a + b
	print(f"g2={c}")
	return {"data": c}

def g3(input: Dict) -> Dict[str, Any]:
	'''
	save file in GeoAI. input=('data': Any)
	'''
	out_value = -1
	if type(input) is int:
		out_value = input + 1
	elif type(input) is list:
		out_value = sum([x['data'] for x in input])
	elif type(input) is dict:
		if len(input) > 1:
			out_value = sum([input[x]['data'] for x in input])
		else:
			out_value = input['data']	
	print(f"g3={out_value}")
	return {"result": out_value}

def b1():
	'''
	load file in BIM
	'''
	print("b1")

def b2(a: int, b: int) -> Dict[str, Any]:
	'''
	sampling file in BIM
	'''
	c = a + b
	print(f"b2={c}")
	return {"data": c}

def b3(input: Dict) -> Dict[str, Any]:
	'''
	save file in BIM. input=('data': Any)
	'''
	out_value = -1
	if type(input) is int:
		out_value = input + 1
	elif type(input) is list:
		out_value = sum([x['data'] for x in input])
	elif type(input) is dict:
		if len(input) > 1:
			out_value = sum([input[x]['data'] for x in input])
		else:
			out_value = input['data']	
	print(f"b3={out_value}")
	return {"result": out_value}

def r1():
	'''
	set base point in Robot
	'''
	print("r1")

def r2(a: int, b: int) -> Dict[str, Any]:
	'''
	move position(a, b) in Robot
	'''
	c = a + b
	print(f"r2={c}")
	return {"data": c}

def r3(input: Dict) -> Dict[str, Any]:
	'''
	pick the input position. input=('data': Any)
	'''
	out_value = -1
	if type(input) is int:
		out_value = input + 1
	elif type(input) is list:
		out_value = sum([x['data'] for x in input])
	elif type(input) is dict:
		if len(input) > 1:
			out_value = sum([input[x]['data'] for x in input])
		else:
			out_value = input['data']	
	print(f"r3={out_value}")
	return {"result": out_value}

# create function(tool) prototype using python runtime
def extract_type(type_str):
	match = re.search(r"<class '(\w+)'>", type_str)
	if match:
		return match.group(1)
	return type_str

def get_function_prototype(func):
	comments = func.__doc__.replace('\t', '').replace('\n', '')
	hints = get_type_hints(func)
	parameters = {k: str(v) for k, v in hints.items() if k != 'return'}
	parameters_str = ", ".join([p + ":" + extract_type(parameters[p]) for p in parameters])

	return_types = hints.get('return', 'none') 
	if return_types == 'none':
		return_types = 'no return'
	else:
		return_types = f'returns {return_types}'
	sig_str = f'{func.__name__}({parameters_str}) with {return_types} for {comments}'
	return sig_str

# define function protoype list
func_list = [g1, g2, g3, b1, b2, b3, r1, r2, r3]
func_prototype_list = []
for func in func_list:
	proto = get_function_prototype(func)
	print(proto)
	func_prototype_list.append(proto)

# insert function prototype list to prompt
coder_prompt_tpl = ChatPromptTemplate.from_messages([
	("system", f'You are a Python coder. You can call function with {func_prototype_list} using variables, if condition, loop statement under user input commands.The last function return result or the final calculated value of the code is stored in the variable "last_result". Do not respond with anything that is not Python code. Do not provide explanation including "#" line comments'), MessagesPlaceholder(variable_name="chat_history"),
	("human", "{input}"),
])

coder_chains = (
	coder_prompt_tpl
	| llm
)

# python function call test.
response = query_llm(coder_chains, "g1()") # just generate code to call it
code = preprocess_code(response.content)
exec(code)

response = query_llm(coder_chains, "In geoai, load file and sampling it with 3.14, for loop index in loop with 10 times. save it.")
code = preprocess_code(response.content)
exec(code)

response = query_llm(coder_chains, "In geoai. Load the file. Sample with 3.14 and the loop index value in the loop. Repeat the loop 10 times. Save the sampled results.")
code = preprocess_code(response.content)
exec(code)

response = query_llm(coder_chains, "In BIM. Load the file. Sample with 3.14 and loop index value in the loop. Repeat the loop 10 times. Save the sampled result.")
code = preprocess_code(response.content)
exec(code)

input_query = "In robot domain. Position the robot at the origin. There are two balls on the table. The red ball is at position (2,2) and the green ball is at position (10,3). Move 5 positions up from the green ball. Pick up the object at the origin."
response = query_llm(coder_chains, input_query)
code = preprocess_code(response.content)
exec(code)

# define assistant function and chains
assistant_prompt_tpl = ChatPromptTemplate.from_messages([
	("system", """You are a helpful AI assistant. If you don't know, answer I don't know."""), MessagesPlaceholder(variable_name="chat_history"),
	("human", "{input}"),
])

assistant_chains = (
	assistant_prompt_tpl
	| llm
)

def reasoning_llm(input_query: str) -> str:
	response = query_llm(coder_chains, input_query)
	code = preprocess_code(response.content)
	exec(code)
	if 'last_result' not in locals():
		return "I don't know."
	print(f'\n* Last result *\n{locals()["last_result"]}\n* End of Last result *\n')

	revise_query = f'Already user queried "{input_query}". and I executed the python code you generated, so we took the result which is {locals()["last_result"]}. Answer the question considering the last result values under the user query for human to understand it naturally.'
	response = query_llm(assistant_chains, revise_query)
	return response

# Test reasoning with function call
response = reasoning_llm("In geoai. Load the file. Sample with 3.14 and the loop index value in the loop. Repeat the loop 10 times. How much is the result of the sampling?")
print(f'Final result: {response.content}')