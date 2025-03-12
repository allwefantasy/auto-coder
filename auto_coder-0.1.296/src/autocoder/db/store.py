import os
from sqlmodel import SQLModel, Field, create_engine, Session, select

class TokenCounter(SQLModel, table=True):
    project: str = Field(primary_key=True)
    input_tokens_count: int = 0
    generated_tokens_count: int = 0

class SingletonStore(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]    

class Store(metaclass=SingletonStore):
    def __init__(self, db_path: str=None):
        self.db_path = db_path
        self.engine = self._create_engine()
        SQLModel.metadata.create_all(self.engine)

    def _create_engine(self):
        if not os.path.exists(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return create_engine(f"sqlite:///{self.db_path}")

    def update_token_counter(self, project: str=None, input_tokens_count: int=0, generated_tokens_count: int=0):
        with Session(self.engine) as session:
            if project is None:
                statement = select(TokenCounter)
            else:
                statement = select(TokenCounter).where(TokenCounter.project == project)
            results = session.exec(statement)
            token_counter = results.first()

            if token_counter is None:
                token_counter = TokenCounter(project=project)

            token_counter.input_tokens_count += input_tokens_count
            token_counter.generated_tokens_count += generated_tokens_count
            session.add(token_counter)
            session.commit()

    def get_token_counter(self):
        with Session(self.engine) as session:
            statement = select(TokenCounter)
            results = session.exec(statement)
            token_counter = results.first()
            return token_counter