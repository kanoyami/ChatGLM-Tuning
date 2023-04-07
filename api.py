from fastapi import FastAPI, Request
from transformers import AutoTokenizer, AutoModel
import uvicorn
import json
import datetime
import torch
from peft import get_peft_model, LoraConfig, TaskType

DEVICE = "cuda"
DEVICE_ID = "0"
CUDA_DEVICE = f"{DEVICE}:{DEVICE_ID}" if DEVICE_ID else DEVICE

torch.set_default_tensor_type(torch.cuda.HalfTensor)
def torch_gc():
    if torch.cuda.is_available():
        with torch.cuda.device(CUDA_DEVICE):
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

app = FastAPI()


@app.post("/")
async def create_item(request: Request):
    global model, tokenizer
    json_post_raw = await request.json()
    json_post = json.dumps(json_post_raw)
    json_post_list = json.loads(json_post)
    prompt = json_post_list.get('prompt')
    history = json_post_list.get('history')
    max_length = json_post_list.get('max_length')
    top_p = json_post_list.get('top_p')
    temperature = json_post_list.get('temperature')
    response, history = model.chat(tokenizer,
                                   prompt,
                                   history=history,
                                   max_length=max_length if max_length else 2048,
                                   top_p=top_p if top_p else 0.7,
                                   temperature=temperature if temperature else 0.95)
    now = datetime.datetime.now()
    time = now.strftime("%Y-%m-%d %H:%M:%S")
    answer = {
        "response": response,
        "history": history,
        "status": 200,
        "time": time
    }
    log = "[" + time + "] " + '", prompt:"' + \
        prompt + '", response:"' + repr(response) + '"'
    torch_gc()
    return answer


if __name__ == '__main__':
    torch_gc()
    tokenizer = AutoTokenizer.from_pretrained(
        "THUDM/chatglm-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained(
        "THUDM/chatglm-6b", trust_remote_code=True).half().cuda()
    peft_path = "output/adapter_model.bin"
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, inference_mode=True,
        r=8,
        lora_alpha=32, lora_dropout=0.1
    )
    model = get_peft_model(model, peft_config)
    model.load_state_dict(torch.load(peft_path), strict=False)

    uvicorn.run(app, host='0.0.0.0', port=8000, workers=1)
