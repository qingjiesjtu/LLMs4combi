import json, os
from openai import OpenAI
import re
import argparse
from tqdm import tqdm

# 100刀限额的API key
client = OpenAI(api_key="sk-eqOMi2allf2s7VNf78F5052aEbC2461c8fC85349Be39CaC2", base_url="https://aihubmix.com/v1")


def get_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resPath', type=str)
    opts = parser.parse_args()
    return opts

def computeAverageScore(pigaiPath):
    res=[]
    total_score=0
    with open(pigaiPath, 'r', encoding='utf-8') as file:
        for line in file:
            res.append(json.loads(line))  # 确保每行是有效的 JSON
    score=0
    for res_dict in res:
        score+=float(res_dict['score'])
        for _, subanswer in res_dict['ref_answer'].items():
            rules=subanswer[0]['rules']
            for rulescore in rules:
                total_score+=rulescore['score']
    print(pigaiPath)
    print(f"得分率：{score}/{total_score}={score/total_score:.2f}")

opts=get_opts()

result_path=opts.resPath
output_file_path=result_path[:-6]+"_pigai.jsonl"

res=[]
with open(result_path, 'r', encoding='utf-8') as file:
    for line in file:
        res.append(json.loads(line))  # 确保每行是有效的 JSON

# 中断恢复机制
done_index_list=[]
if os.path.exists(output_file_path):
    with open(output_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            done_data = json.loads(line)  # 确保每行是有效的 JSON
            done_index_list.append(done_data['index'])

for res_dict in tqdm(res, desc="Pigai", unit="Answer"):
    if res_dict['index'] in done_index_list: continue
    problem=res_dict['problem']
    ref_answer=res_dict['ref_answer']
    answer=res_dict['answer']

    # 这种方法存在的问题：比如一下例子中情况1，2，3具体对应到哪里是未知的
    pigaiPrompt=f'''
    你是一位组合数学课的老师，请根据参考答案和打分规则来给学生的回答打分。我将给你问题，参考答案和打分规则，学生回答，请输出一个分数。例如：
    问题：
    \\begin{{exercise}} 设$\\left\\{{ a_i \\right\\}}$是一长度为$60$的正整数列（$1 \\leq i \\leq 60$），其中$a_1 = 1, a_{{60}}=20^{{20}}$，并且数列中每一项都是其后面一项的约数。 % \\begin{{enumerate}}[label={{\\rm (\\arabic*)}}] \\item 求满足要求的数列$\\left\\{{ a_i \\right\\}}$的数目； \\item 若进一步要求$\\left\\{{ a_i \\right\\}}$严格递增，求满足条件的序列数目。 \\end{{enumerate}} \\end{{exercise}}

    参考答案：
        "(1)": [
            {{
            "answer": "$20^{{20}} = 2^{{40}} \\dotp 5^{{20}}$。 \\begin{{enumerate}}[label={{\\rm (\\arabic*)}}] \\item 每一项中含有$2$的幂次和$5$的幂次分别单调递增。 以$2$的幂次为例，可想象成是走$58 \\times 40$的格路，路径在$x = i - 2$处的最大$y$坐标即为$a_i$中$2$的幂次；对于$5$也类似。 总的方案数为$\\binom{{98}}{{40}} \\binom{{78}}{{20}}$；",
            "rules": [
                {{
                "rule": "分解$20^{{20}}$",
                "score": 1
                }},
                {{
                "rule": "答案正确",
                "score": 3
                }}
            ]
            }}
        ],
        "(2)": [
            {{
            "answer": "\\item 讨论数列$\\left\\{{ \\frac{{a_{{i+1}}}}{{a_i}} \\right\\}}$（$1 \\leq i \\leq 59$），该数列的组成有三种情况： % \\begin{{itemize}} \\item $38$个$2$、$20$个$5$、$1$个$4$，有$59 \\binom{{58}}{{20}}$种情况； \\item $39$个$2$、$19$个$5$、$1$个$10$，有$59 \\binom{{58}}{{19}}$种情况； \\item $40$个$2$、$18$个$5$、$1$个$25$，有$59 \\binom{{58}}{{18}}$种情况。 \\end{{itemize}} % 因此，总共有$59 \\left[ \\binom{{58}}{{18}} + \\binom{{58}}{{19}} + \\binom{{58}}{{20}} \\right]$种情况。",
            "rules": [
                {{
                "rule": "讨论数列形式",
                "score": 1
                }},
                {{
                "rule": "情况1正确",
                "score": 1
                }},
                {{
                "rule": "情况2正确",
                "score": 1
                }},
                {{
                "rule": "情况3正确",
                "score": 1
                }},
                {{
                "rule": "答案正确",
                "score": 1
                }}
            ]
            }}
        ]

    学生回答：
    ### 问题分析

    我们有一个长度为60的正整数列 $\{{a_i\}}$，其中 $1 \leq i \leq 60$，满足以下条件：
    1. $a_1 = 1$
    2. $a_{{60}} = 20^{{20}}$
    3. 对于每一个 $i$（$1 \leq i \leq 59$），$a_i$ 是 $a_{{i+1}}$ 的约数。

    我们需要解决两个问题：
    1. 求满足上述条件的数列 $\{{a_i\}}$ 的数目。
    2. 如果进一步要求数列 $\{{a_i\}}$ 严格递增，求满足条件的序列数目。

    ### 问题1：求满足要求的数列 $\{{a_i\}}$ 的数目

    #### 思路

    首先，我们注意到 $a_1 = 1$，而 $a_i$ 是 $a_{{i+1}}$ 的约数。这意味着对于每一个 $i$，$a_{{i+1}}$ 必须是 $a_i$ 的倍数。因此，数列 $\{{a_i\}}$ 是一个非递减的序列，且每一项都是前一项的倍数。

    为了简化问题，我们可以考虑将数列 $\{{a_i\}}$ 看作是从 $1$ 到 $20^{{20}}$ 的一条路径，其中每一步都是从前一项乘以一个正整数得到的。

    #### 具体步骤

    1. **确定每一步的倍数**：对于每一个 $i$（$1 \leq i \leq 59$），$a_{{i+1}} = a_i \times k_i$，其中 $k_i$ 是一个正整数。
    2. **总倍数的确定**：由于 $a_{{60}} = 1 \times k_1 \times k_2 \times \cdots \times k_{{59}} = 20^{{20}}$，所以 $k_1 \times k_2 \times \cdots \times k_{{59}} = 20^{{20}}$。
    3. **分解质因数**：将 $20^{{20}}$ 分解质因数，得到 $20^{{20}} = (2^2 \times 5)^20 = 2^{{40}} \times 5^{{20}}$。
    4. **分配质因数**：我们需要将 $2^{{40}}$ 和 $5^{{20}}$ 分配到 $k_1, k_2, \ldots, k_{{59}}$ 中。

    #### 计算方法

    对于每一个质因数，我们可以独立地分配其指数。具体来说：
    - 对于质因数 $2$，我们需要将 $40$ 个 $2$ 分配到 $59$ 个 $k_i$ 中。这相当于将 $40$ 个无区别的球放入 $59$ 个有区别的盒子中，允许空盒。这是一个经典的组合问题，可以用“星与条”方法计算，其方案数为 $\binom{{40 + 59 - 1}}{{59 - 1}} = \binom{{98}}{{58}}$。
    - 对于质因数 $5$，我们需要将 $20$ 个 $5$ 分配到 $59$ 个 $k_i$ 中。同样地，方案数为 $\binom{{20 + 59 - 1}}{{59 - 1}} = \binom{{78}}{{58}}$。

    由于这两个分配是独立的，总的方案数为 $\binom{{98}}{{58}} \times \binom{{78}}{{58}}$。

    ### 问题2：若进一步要求 $\{{a_i\}}$ 严格递增，求满足条件的序列数目

    #### 思路

    如果数列 $\{{a_i\}}$ 严格递增，那么每一项 $a_{{i+1}}$ 必须是 $a_i$ 的严格倍数，即 $a_{{i+1}} = a_i \times k_i$，其中 $k_i \geq 2$。

    #### 具体步骤

    1. **确定每一步的倍数**：对于每一个 $i$（$1 \leq i \leq 59$），$a_{{i+1}} = a_i \times k_i$，其中 $k_i \geq 2$。
    2. **总倍数的确定**：由于 $a_{{60}} = 1 \times k_1 \times k_2 \times \cdots \times k_{{59}} = 20^{{20}}$，所以 $k_1 \times k_2 \times \cdots \times k_{{59}} = 20^{{20}}$。
    3. **分解质因数**：将 $20^{{20}}$ 分解质因数，得到 $20^{{20}} = 2^{{40}} \times 5^{{20}}$。
    4. **分配质因数**：我们需要将 $2^{{40}}$ 和 $5^{{20}}$ 分配到 $k_1, k_2, \ldots, k_{{59}}$ 中，且每个 $k_i$ 至少为 $2$。

    #### 计算方法

    对于每一个质因数，我们可以独立地分配其指数。具体来说：
    - 对于质因数 $2$，我们需要将 $40$ 个 $2$ 分配到 $59$ 个 $k_i$ 中，且每个 $k_i$ 至少包含 $1$ 个 $2$。这相当于将 $40 - 59 = -19$ 个 $2$ 分配到 $59$ 个盒子中，这是不可能的。因此，我们需要重新考虑分配方式。

    实际上，由于每个 $k_i$ 至少为 $2$，我们可以将 $2^{{40}}$ 看作是 $2^{{40}} = 2^{{59}} \times 2^{{40 - 59}} = 2^{{59}} \times 2^{{-19}}$。由于指数不能为负，这意味着我们需要至少 $59$ 个 $2$，但 $40 < 59$，所以这是不可能的。

    因此，不存在满足条件的严格递增数列。

    ### 最终答案

    1. 满足要求的数列 $\{{a_i\}}$ 的数目为 $\binom{{98}}{{58}} \times \binom{{78}}{{58}}$。
    2. 若进一步要求 $\{{a_i\}}$ 严格递增，则不存在满足条件的序列。

    那么，由于这个例子中的问题和参考答案包含2个小题，因此你需要逐个给每个小题打分。初始给分为0。
    先分析第1小题，对于第1个批改规则"rule": "分解$20^{{20}}$, "score": 1"，由于学生回答中包含"3. **分解质因数**：将 $20^{{20}}$ 分解质因数，得到 $20^{{20}} = (2^2 \times 5)^20 = 2^{{40}} \times 5^{{20}}$。", 因此根据""score": 1", 我们给0（之前总分）+ 1（该规则给分）= 1 （当前总分）。对于第2个批改规则""rule": "答案正确", "score": 3", 我们找到参考答案中第1小题的最终答案是"$\\binom{{98}}{{40}} \\binom{{78}}{{20}}$"，学生回答的最终答案是"$\binom{{98}}{{58}} \times \binom{{78}}{{58}}$", 虽然他们形式上不一样，但是经过一些组合数学的运算是一样的，即"$\binom{{98}}{{58}} \times \binom{{78}}{{58}}$=$\binom{{98}}{{40}} \times \binom{{78}}{{20}}$"，因此答案正确，我们给1（之前总分）+ 3（该规则给分）= 4（当前总分）。
    再分析第2小题，对于第1个批改规则""rule": "讨论数列形式", "score": 1"，根据参考答案中的"该数列的组成有三种情况"可知需要将数列分为三种情况讨论，但是学生回答中没有分成三种情况讨论，因此我们给4（之前总分）+ 0（不符合该规则，不给分）= 4（当前总分）。对于第2个批改规则""rule": "情况1正确", "score": 1"，由于学生回答中不包含情况1，因此我们给4（之前总分）+ 0（不符合该规则，不给分）= 4（当前总分）。对于第3个批改规则""rule": "情况2正确", "score": 1"，由于学生回答中不包含情况2，因此我们给4（之前总分）+ 0（不符合该规则，不给分）= 4（当前总分）。对于第4个批改规则""rule": "情况3正确", "score": 1"，由于学生回答中不包含情况3，因此我们给4（之前总分）+ 0（不符合该规则，不给分）= 4（当前总分）。对于第5个批改规则""rule": "答案正确", "score": 1"，由于学生回答的答案是"不存在满足条件的严格递增数列"，而参考答案的最终答案是"总共有$59 \\left[ \\binom{{58}}{{18}} + \\binom{{58}}{{19}} + \\binom{{58}}{{20}} \\right]$种情况"，因此我们给4（之前总分）+ 0（不符合该规则，不给分）= 4（当前总分）。
    因此总分是4。
    总分：
    4

    请根据以上例子，依据我下面给出的问题和参考答案给学生回答打分。请根据我提供的例子，首先输出你的打分分析过程，最终输出学生的分数。
    问题：
    {problem}

    参考答案：
    {ref_answer}

    学生回答：
    {answer}

    请首先输出你的打分分析过程，最终输出学生的分数。你必须保证你输出的最后一部分遵循此格式：
    总分：
    分数
    '''
    response = client.chat.completions.create(
        model="gpt-4o",
        # model="DeepSeek-V2.5-1210"
        messages=[
            # {"role": "system", "content": "请用中文解答组合数学问题。"},
            {"role": "user", "content": pigaiPrompt},
        ],
        stream=False
    )
    scoreAnswer=response.choices[0].message.content

    res_dict['scoreReason']=scoreAnswer
    
    # 使用正则表达式查找所有的数字，包括整数和小数
    numbers = re.findall(r'\d+\.\d+|\d+', scoreAnswer)

    # 获取最后一个数字
    last_number = numbers[-1] if numbers else None
    res_dict['score']=last_number

    with open(output_file_path, 'a', encoding='utf-8') as file:
        json_line = json.dumps(res_dict, ensure_ascii=False)
        file.write(json_line + '\n')


computeAverageScore(output_file_path)