"""Radio propagation prediction module."""

def __getattr__(name):
    """Lazy import to avoid loading heavy dependencies unless needed."""
    if name == "batch_process":
        from .batch_processor import main as batch_process
        return batch_process
    elif name == "load_profiles":
        from .profile_parser import load_profiles
        return load_profiles
    elif name == "process_loss_parameters":
        from .profile_parser import process_loss_parameters
        return process_loss_parameters
    elif name == "generate_phyllotaxis":
        from .point_generator import generate_phyllotaxis
        return generate_phyllotaxis
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["batch_process", "load_profiles", "process_loss_parameters", "generate_phyllotaxis"]
