try:
    import openai
    from .client import OpenAIClient
except ImportError as ierr:
    if 'openai' in str(ierr):
        raise ImportError(
            "The openai python package is needed to use the mira openai module is not "
            "installed. Run `pip install openai` to install it."
        ) from ierr
    else:
        raise ierr
