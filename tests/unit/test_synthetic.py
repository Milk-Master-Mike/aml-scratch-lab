from engine.synthetic.generator import generate_bank


def test_same_seed_produces_same_bank():
    assert generate_bank(194028, days=30) == generate_bank(194028, days=30)


def test_different_seed_produces_different_bank():
    assert generate_bank(1, days=30) != generate_bank(2, days=30)


def test_supported_baseline_durations():
    for days in (30, 60, 90):
        customers, accounts, transactions = generate_bank(5, days=days)
        assert len(customers) == 8
        assert len(accounts) == 8
        assert transactions
