import pytest
from authenticator import Authenticator

@pytest.fixture
def authenticator():
    auth = Authenticator()
    yield auth
    auth.reset()

@pytest.fixture
def user():
   return "name"

@pytest.fixture
def passwd():
   return "pass"

def test_register(authenticator, user, passwd):
    authenticator.register(user, passwd)
    assert authenticator.users[user] == passwd

def test_register_by_registered(authenticator, user, passwd):
    authenticator.register(user, passwd)
    with pytest.raises(ValueError, match="ユーザーは既に存在します"):
      authenticator.register(user, passwd)

def test_login(authenticator, user, passwd):
    authenticator.register(user, passwd)
    assert authenticator.login(user, passwd) == "ログイン成功"

def test_login_by_wrong_pass(authenticator, user, passwd):
    authenticator.register(user, passwd)
    with pytest.raises(ValueError, match="ユーザー名またはパスワードが正しくありません"):
      authenticator.login(user, passwd+passwd)