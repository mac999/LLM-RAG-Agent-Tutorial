# Title: Fine-tuning Gemma-3 for Function Calling Tasks
# Environment: Python 3.8+, Ubuntu 20.04, CUDA 11.3+
# Libraries: transformers, datasets, trl, peft, huggingface_hub, dotenv
# Description:
# This script fine-tunes Google's Gemma-3 language model for function calling tasks using LoRA and HuggingFace.
# It loads a function-calling dataset, preprocesses it into a chat format, and trains the model with special tokens.
# The script also demonstrates how to push the trained model and tokenizer to the HuggingFace Hub,
# and how to load and use the fine-tuned model for inference.
#
import torch, json, gc, os
from transformers import AutoTokenizer, Gemma3ForConditionalGeneration, BitsAndBytesConfig, set_seed
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig, PeftModel, PeftConfig
from enum import Enum
from huggingface_hub import login
from dotenv import load_dotenv

load_dotenv()
hf_token = os.getenv("HF_API_KEY")
login(token=hf_token)

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

seed = 42
set_seed(seed)

torch_dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model_name = "google/gemma-3-4b-it"
dataset_name = "Salesforce/xlam-function-calling-60k"

model_kwargs = dict(
    attn_implementation="flash_attention_2", # "eager", "sdpa", "flash_attention", "flash_attention_2"
    torch_dtype=torch_dtype,
    device_map="auto",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type='nf4',
        bnb_4bit_compute_dtype=torch_dtype,
        bnb_4bit_quant_storage=torch_dtype,
        llm_int8_enable_fp32_cpu_offload=True
    ),
    local_files_only=True
)

model = Gemma3ForConditionalGeneration.from_pretrained(model_name, **model_kwargs)

class ToolCallSpacialTokens(str, Enum):
    tools = "<tools>"
    eotools = "</tools>"
    think = "<think>"
    eothink = "</think>"
    tool_call="<tool_call>"
    eotool_call="</tool_call>"
    tool_response="<tool_response>"
    eotool_response="</tool_response>"
    pad_token = "<pad>"
    eos_token = "<eos>"

    @classmethod
    def list(cls):
        return [c.value for c in cls]

tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    pad_token=ToolCallSpacialTokens.pad_token.value,
    additional_special_tokens=ToolCallSpacialTokens.list(), local_files_only=True
)

tokenizer.chat_template = """{{ bos_token }}{% if messages[0]['role'] == 'system' %}{{ raise_exception('System role not supported') }}{% endif %}{% for message in messages %}{{ '<start_of_turn>' + message['role'] + '\n' + message['content'] | trim + '<end_of_turn><eos>\n' }}{% endfor %}{% if add_generation_prompt %}{{'<start_of_turn>model\n'}}{% endif %}"""

model.resize_token_embeddings(len(tokenizer))
model.to(device)

def preprocess(sample):
    try:
        tools = json.loads(sample["tools"])
        answers = json.loads(sample["answers"])
        user_query = sample["query"]
    except Exception as e:
        print("Error decoding JSON:", sample)
        raise e

    messages = [
        {
            "role": "user",
            "content": (
                "You have access to the following tools:\n\n"
                + "\n\n".join(f"- {tool['name']}: {tool['description']}" for tool in tools)
                + "\n\nUser query:\n" + user_query
            )
        },
        {
            "role": "assistant",
            "content": "\n".join(
                f"<function_call>\n{json.dumps(answer)}\n</function_call>"
                for answer in answers
            )
        }
    ]

    return {
        "text": tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    }

dataset = load_dataset(dataset_name)
dataset = dataset["train"].map(preprocess, remove_columns=["id", "query", "answers", "tools"])
dataset = dataset.train_test_split(0.1)
print(dataset)

print(dataset["train"][19]["text"])

peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.05,
    r=16,
    bias="none",
    target_modules="all-linear",
    task_type="CAUSAL_LM",
    modules_to_save=["lm_head", "embed_tokens"] # make sure to save the lm_head and embed_tokens as you train the special tokens
)

training_arguments = SFTConfig(
    output_dir="gemma-3-4b-it-thinking-function_calling-V0",
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=32,
    save_strategy="epoch",
    eval_strategy="epoch",
    logging_steps=50,
    learning_rate=3e-4,
    max_grad_norm=0.3,
    weight_decay=0.1,
    warmup_ratio=0.03,
    lr_scheduler_type="constant",
    report_to=None,
    bf16=True,
    optim="paged_adamw_8bit",
    torch_compile=False,
    push_to_hub=False,
    num_train_epochs=3,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    packing=False,
    max_seq_length=512,
    dataset_kwargs={
        "add_special_tokens": False,
        "append_concat_token": True,
    }
)

torch.cuda.empty_cache()
torch.cuda.ipc_collect()
gc.collect()

trainer = SFTTrainer(
    model=model,
    args=training_arguments,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    # tokenizer=tokenizer,
    peft_config=peft_config,
) # https://huggingface.co/docs/trl/en/sft_trainer

trainer.train()
trainer.save_model()

trainer.push_to_hub(f'mac999/gemma-3-4b-it-thinking-function_calling-V0-{seed}', commit_message="Pushing fine-tuned model with function calling capabilities")

tokenizer.eos_token = "<eos>"
tokenizer.push_to_hub(f"mac999/", token=True)

peft_model_id = f"mac999/gemma-3-4b-it-thinking-function_calling-V0-{seed}" 
device = "auto"
config = PeftConfig.from_pretrained(peft_model_id)
model = Gemma3ForConditionalGeneration.from_pretrained("google/gemma-3-4b-it",
                                             device_map="auto",
                                             )
tokenizer = AutoTokenizer.from_pretrained(peft_model_id)
model.resize_token_embeddings(len(tokenizer))
model = PeftModel.from_pretrained(model, peft_model_id)
model.to(torch.bfloat16)
model.eval()

prompt = """<bos><start_of_turn>user
You have access to the following tools:

- numerical_derivative: Estimate the derivative of a mathematical function

User query:
I need to estimate the derivative of the function y = sin(x) at x = π/4 and x = π. Can you help with that?<end_of_turn><eos>
<start_of_turn>assistant
"""

inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=256,
    do_sample=True,
    temperature=0.01,
    top_p=0.95,
    repetition_penalty=1.1,
    eos_token_id=tokenizer.eos_token_id
)

response = tokenizer.decode(outputs[0], skip_special_tokens=False)
print(response)