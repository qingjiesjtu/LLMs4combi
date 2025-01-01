import json, os
from openai import OpenAI
from tqdm import tqdm
import argparse

def get_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name', type=str, default='o1-preview')
    parser.add_argument('--expPath', type=str)
    parser.add_argument('--rag', type=str, choices=["homework","textbook"])
    parser.add_argument('--dataset', type=str, choices=["test","exam","new"], default="test")
    parser.add_argument('--newDataPath', type=str)
    opts = parser.parse_args()
    return opts

opts=get_opts()


model_name=opts.model_name
expPath=opts.expPath

if "deepseek" in model_name:
    # 课程提供
    client = OpenAI(api_key="sk-ef026ec49e9c4e469e55f7d3ea2edf7b", base_url="https://api.deepseek.com")
else:
    # 100刀限额的API key
    client = OpenAI(api_key="sk-eqOMi2allf2s7VNf78F5052aEbC2461c8fC85349Be39CaC2", base_url="https://aihubmix.com/v1")


if not os.path.exists(expPath):
    # 路径不存在，创建新路径
    os.makedirs(expPath)
    print(f"路径已创建: {expPath}")
else:
    print(f"路径已存在: {expPath}")

result_path = os.path.join(expPath,'res.jsonl')

# 中断恢复机制
done_index_list=[]
if os.path.exists(result_path):
    with open(result_path, 'r', encoding='utf-8') as file:
        for line in file:
            done_data = json.loads(line)  # 确保每行是有效的 JSON
            done_index_list.append(done_data['index'])

def read_json_from_folder(folder_path):
    # 遍历文件夹，查找 JSON 文件
    if not os.path.isdir(folder_path): return None
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path) and item_path.endswith('.json'):
            # 只处理 JSON 文件
            print(f"正在读取 JSON 文件：{item_path}")
            with open(item_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            return json_data  # 返回读取的数据
    print("未找到 JSON 文件")
    return None

def loadJson(path):
    if not path.endswith('.json'):
        raise ValueError("Path must end with .json")
    with open(path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    print(f"Json data loaded, including {len(json_data)} questions.")
    return json_data

def loadDataTest(path):
    res={}
    # 获取指定路径下的所有内容（包括文件和文件夹）
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        data=read_json_from_folder(os.path.join(item_path, "ref_answers"))
        if data==None: continue
        for key, value in data.items():
            res[key]=value
    print(f"Test data loaded, including {len(res)} questions.")
    return res

def loadDataExam(folder_path):
    json_data_dict={}
    res={}
    # 遍历文件夹，查找 JSON 文件
    if not os.path.isdir(folder_path): return None
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path) and item_path.endswith('.json'):
            # 只处理 JSON 文件
            print(f"正在读取 JSON 文件：{item_path}")
            with open(item_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            json_data_dict[item.strip('.json')]=json_data
    for key, data in json_data_dict.items():
        for qIndex, qa in data.items():
            res[key+'-'+qIndex]=qa
    print(f"Exam data loaded, including {len(res)} questions.")
    return res  # 返回读取的数据
def get_file_paths(directory):
    """
    获取指定目录下的所有一级文件路径。
    :param directory: 目标目录路径
    :return: 文件路径列表
    """
    file_paths = []
    # 遍历目录下的文件和文件夹
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        # 只保留文件
        if os.path.isfile(item_path):
            file_paths.append(item_path)
    return file_paths

if opts.rag in ("homework", "textbook"):
    # 我们的最终方案没有采用RAG，因此此处不提供OpenAI API key
    client = OpenAI(api_key='') 

    assistant = client.beta.assistants.create(
    name="组合数学专家",
    instructions="你是一位组合数学专家，请用你的知识库回答组合数学问题。",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
    )

    # Create a vector store caled "Financial Statements"
    vector_store = client.beta.vector_stores.create(name="组合数学参考材料")

    # Ready the files for upload to OpenAI
    # file_paths = ["/home/ubuntu/zqj/LLMs/zuheshuxue/ragRef/_组合数学_教材书稿.pdf"]
    ragDir="./rag/homework" if opts.rag=="homework" else "./rag/textbook"
    file_paths = get_file_paths(ragDir)
    file_streams = [open(path, "rb") for path in file_paths]

    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id, files=file_streams
    )

    # You can print the status and the file counts of the batch to see the result of this operation.
    print(file_batch.status)
    print(file_batch.file_counts)

    assistant = client.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )

def getAnswer(prompt):
    if opts.rag in ("homework", "textbook"):
        if '4o' not in model_name:
            print("RAG only supported in gpt-4o models")
            # break
        # Create a thread and attach the file to the message
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        # Use the create and poll SDK helper to create a run and poll the status of
        # the run until it's in a terminal state.

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=assistant.id
        )

        messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

        message_content = messages[0].content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")
        answer = message_content.value + "\n" + "\n".join(citations)
    elif 'o1' in model_name:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            stream=False
        )        
        answer = response.choices[0].message.content
    else:
        response = client.chat.completions.create(
            model=model_name,
            # model="DeepSeek-V2.5-1210"
            messages=[
                # {"role": "system", "content": "请用中文解答组合数学问题。"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        answer = response.choices[0].message.content
    return answer

CoTkeywords = ["polya", "Polya", "burnside", "Burnside", "转动群"]
cotPrompt="""

请根据以下解题思路回答上述问题。
这类问题需要用到burnside引理或者polya定理，具体的解题思路如下
1.根据欧拉公式，和棱、面、点之间的数值关系，求出多面体的信息
2.根据多面体的形态，分析其转动群，并列表出  |置换类型|转动群数量|不同面形的转动循环情况| ,其中循环情况应以转动循环的形式展示
3.然后根据涂色或者图案进行上色，涂色没有方向限制，视为相同方案。但是图案具有方向性，不同方向的方案不同（当出现一阶循环的时候不存在不动点，高阶循环阶乘基数改变）。同样列出表格|置换类型|转动群数量|不同面形的转动循环情况|不动点个数| ,其中循环情况应以转动循环的形式展示，不动点个数应以指数相乘的形式展示
4.最后列出计算公式并求方案数
"""
step1prompt="请执行：1.根据欧拉公式，和棱、面、点之间的数值关系，求出多面体的信息"
step2prompt="请执行：2.根据多面体的形态，分析其转动群，并列表出  |置换类型|转动群数量|不同面形的转动循环情况| ,其中循环情况应以转动循环的形式展示"
step3prompt="请执行：3.然后根据涂色或者图案进行上色，涂色没有方向限制，视为相同方案。但是图案具有方向性，不同方向的方案不同（当出现一阶循环的时候不存在不动点，高阶循环阶乘基数改变）。同样列出表格|置换类型|转动群数量|不同面形的转动循环情况|不动点个数| ,其中循环情况应以转动循环的形式展示，不动点个数应以指数相乘的形式展示"
step4prompt="请执行：4.最后列出计算公式并求方案数"

stepPrompts=[step1prompt,step2prompt,step3prompt,step4prompt]

def getMultiRoundAnswer(problem):
    """
    多轮对话
    不兼容rag、selfCorrection
    “”“"""
    prompt1=problem+cotPrompt+'\n'+step1prompt
    messages=[
            {"role": "user", "content": prompt1},
       ]
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=False
    )
    answer=response.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})
    for stepPrompt in stepPrompts[1:]:
        messages.append({"role": "user", "content": stepPrompt})
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False
        )
        answer=response.choices[0].message.content
        messages.append({"role": "assistant", "content": answer})
    return messages


if opts.dataset=="test":
    data=loadDataTest("./dataset/ai_judge_dist")
elif opts.dataset=="exam":
    data=loadDataExam("./dataset/final_test/paper_ans")
elif opts.dataset=="new":
    data=loadJson(opts.newDataPath)

for qIndex, qa in tqdm(data.items(), desc="Processing ", unit="problem"):
    if qIndex in done_index_list: continue
    problem=qa['problem']
    if any(keyword in problem for keyword in CoTkeywords):
        # CoT
        answer=getMultiRoundAnswer(problem)
    else:
        # Self-correction
        answer=getAnswer(problem)
        self_correction_prompt=f"""
        请检查关于组合数学的问题的第一次回答的正确性，并给出第二次回答。如果第一次回答正确，请直接输出第一次回答；如果第一次回答错误，请输出正确的第二次回答。
        问题：{problem}
        第一次回答：{answer}
        第二次回答：
        """
        answer=getAnswer(self_correction_prompt)

    res={}
    res['index']=qIndex
    res['problem']=problem
    res['answer']=answer
    if opts.dataset=="test":
        res['ref_answer']=qa['answers']
    with open(result_path, 'a', encoding='utf-8') as file:
        json_line = json.dumps(res, ensure_ascii=False)
        file.write(json_line + '\n')
