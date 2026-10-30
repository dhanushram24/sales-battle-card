"""Track provider-reported usage, without presenting byte estimates as tokens."""
from dataclasses import dataclass


@dataclass
class TokenUsage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    complete: bool = True

    def record(self, completion):
        self.calls += 1
        usage = getattr(completion, "usage", None)
        prompt = getattr(usage, "prompt_tokens", None)
        output = getattr(usage, "completion_tokens", None)
        if type(prompt) is int and type(output) is int and prompt >= 0 and output >= 0:
            self.input_tokens += prompt
            self.output_tokens += output
        else:
            self.complete = False

    def as_dict(self):
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens if self.complete else None,
            "output_tokens": self.output_tokens if self.complete else None,
        }
