from tradinghub.auth.security.passwords import hash_password, verify_password

PASSWORD = "correct horse battery"


def test_hash_is_salted() -> None:
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_accepts_correct_password() -> None:
    assert verify_password(raw_password=PASSWORD, password_hash=hash_password(PASSWORD))


def test_verify_rejects_wrong_password() -> None:
    assert not verify_password(raw_password="wrong", password_hash=hash_password(PASSWORD))


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password(raw_password="anything", password_hash="not-a-hash")


def test_hash_never_contains_the_password() -> None:
    assert PASSWORD not in hash_password(PASSWORD)
