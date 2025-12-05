from openai import OpenAI
from ...agents import Agent
from .types import ArithmeticCriticInput, ArithmeticCriticOutput

def make_critic(client: OpenAI, model: str) -> Agent[ArithmeticCriticInput, ArithmeticCriticOutput]:
    prompt = """
    ROLE: Arithmetic Critic
    Your job is to verify whether the worker produced the correct arithmetic result.
    Output MUST be JSON only.
    Output ONLY:
      {"decision": "ACCEPT"}
    or
      {"decision": "REJECT", "feedback": "explanation"}
    """

    return Agent(
        name="Critic",
        client=client,
        model=model,
        system_prompt=prompt,
        input_schema=ArithmeticCriticInput,
        output_schema=ArithmeticCriticOutput,
        temperature=0.0,
    )
