import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class User:
    username: str
    email: str
    hashed_password: str


class UserStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[User]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [User(**u) for u in data]

    def _save(self, users: list[User]) -> None:
        self.path.write_text(
            json.dumps([asdict(u) for u in users], indent=2),
            encoding="utf-8",
        )

    def get_by_username(self, username: str) -> User | None:
        return next((u for u in self._load() if u.username == username), None)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._load() if u.email == email), None)

    def create(self, username: str, email: str, hashed_password: str) -> User:
        users = self._load()
        user = User(username=username, email=email, hashed_password=hashed_password)
        users.append(user)
        self._save(users)
        return user
