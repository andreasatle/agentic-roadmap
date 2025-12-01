from dotenv import load_dotenv
from openai import OpenAI
load_dotenv(override=True)
openai = OpenAI()

planner_prompt = """
ROLE:
You are the Planner.
Your task is to generate a simple arithmetic task.

INPUT FORMAT:
""

OUTPUT FORMAT TEMPLATE:
{"op": $OP, "a": $A, "b": $B}

INVARIANTS:
- $OP ∈ {"ADD", "SUB", "MUL"} chosen uniformly at random
- $A and $B are integers between 1 and 20 chosen uniformly at random
- Replace the placeholders with real JSON values.
- Output ONLY valid JSON
- No explanation
- No extra text
- No comments
- No trailing commas
"""

worker_prompt = """
ROLE:
You are the Worker.
Compute the result.

INPUT FORMAT TEMPLATE:
{"op": $OP, "a": $A, "b": $B}

OUTPUT FORMAT TEMPLATE:
{"result": $Z}

INVARIANTS:
- $Z must be an integer
- Replace the placeholders with real JSON values.
- Output ONLY valid JSON.
- Do not output anything else
- No explanation
- No surrounding text
"""

critic_prompt = """
ROLE:
You are the Critic.
Verify correctness.

INPUT FORMAT:
{"op": "...", "a": $X, "b": $Y, "result": $Z}

OUTPUT FORMAT:
{"decision": "ACCEPT"}
or
{"decision": "REJECT"}

INVARIANTS:
- Output ONLY valid JSON
- No explanation
- No additional fields
- No comments
"""

class Agent:
    def __init__(self, role, temperature, prompt):
        self.role = role
        self.temperature = temperature
        self.prompt = prompt

    def __call__(self, user_input):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()
    
planner_agent = Agent("Planner", 0.6, planner_prompt)
worker_agent = Agent("Worker", 0.0, worker_prompt)
critic_agent = Agent("Critic", 0.0, critic_prompt)
for _ in range(5):
    plan = planner_agent("")
    result = worker_agent(plan)
    evaluation = critic_agent(f"Task: {plan}\nAnswer: {result}")
    print(f"Plan: {plan}\nResult: {result}\nEvaluation: {evaluation}\n{'-'*40}\n")
