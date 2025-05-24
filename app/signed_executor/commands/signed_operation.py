
class SignedOperation:

    def __init__(self, namespace: str, operation: str):

        self.namespace = namespace
        self.operation = operation

    def __str__(self) -> str:

        return f"{self.namespace}.{self.operation}"

    def with_args(self, *args: str) -> str:

        base = str(self)
        if args:
            base += " " + " ".join(args)
        return base
