from .appconfig import AppConfig
import dspy


def configure_llm(config: AppConfig, api_key: str, callbacks: list):
    """
    Configure the LLM for use across the application.
    """
    lm = dspy.LM(config.model.name, api_key=api_key, cache=True, callbacks=[])
    dspy.configure(lm=lm)
