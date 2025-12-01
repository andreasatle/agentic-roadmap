from dotenv import load_dotenv
from openai import OpenAI
load_dotenv(override=True)
openai = OpenAI()

planner_prompt = """
You are the Planner.
Your job is to design a tiny arithmetic task for the Worker.
Pick two integers X and Y between 1 and 20.
Output the task in the format: "ADD X Y", "SUB X Y" or "MUL X Y".
Do NOT provide any explanation or additional text.
"""

worker_prompt = """
You are the Worker.
Your job is to perform the arithmetic task exactly as the Planner stated it.
Return ONLY the final integer result.
Do NOT explain your reasoning.
Do NOT modify the task.
Do NOT output anything except the number.
"""

critic_prompt = """
You are the Critic.
Your job is to check whether the Worker’s answer matches the Planner’s task.
If correct, output ONLY: ACCEPT
If incorrect, output ONLY: REJECT
Do NOT solve the task yourself.
Do NOT propose a new task.
Do NOT add any explanation.
"""

class Agent:
    def __init__(self, role, prompt):
        self.role = role
        self.prompt = prompt

    def __call__(self, user_input):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content.strip()
    
planner_agent = Agent("Planner", planner_prompt)
worker_agent = Agent("Worker", worker_prompt)
critic_agent = Agent("Critic", critic_prompt)
for _ in range(5):
    plan = planner_agent("")
    result = worker_agent(plan)
    evaluation = critic_agent(f"Task: {plan}\nAnswer: {result}")
    print(f"Plan: {plan}\nResult: {result}\nEvaluation: {evaluation}\n{'-'*40}\n")
