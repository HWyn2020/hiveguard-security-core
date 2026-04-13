"""Tests for framework.security.invariants — the 20 HiveGuard security invariants."""
import pytest

from framework.security.invariants import (
    SECURITY_INVARIANTS,
    check_invariant,
    list_invariants,
)


class TestInvariantInventory:
    def test_exactly_twenty_invariants_defined(self):
        """HiveGuard's contract is exactly 20 invariants — no more, no less."""
        assert len(SECURITY_INVARIANTS) == 20

    def test_every_invariant_has_id_prefix(self):
        """Every invariant must start with a parseable INV-NN: prefix."""
        valid_ids = {f"INV-{i:02d}" for i in range(1, 21)}
        seen_ids = set()
        for inv in SECURITY_INVARIANTS:
            prefix = inv[:6]
            assert prefix in valid_ids, f"Bad/missing INV prefix on: {inv[:30]}"
            assert inv[6] == ":", f"Missing colon after ID in: {inv[:30]}"
            seen_ids.add(prefix)
        assert seen_ids == valid_ids, "Some invariant IDs are missing or duplicated"

    def test_all_invariants_are_non_empty_strings(self):
        for inv in SECURITY_INVARIANTS:
            assert isinstance(inv, str)
            assert len(inv) > 10  # IDs alone are 7 chars; require real content


class TestCheckInvariant:
    def test_check_invariant_returns_full_text_for_valid_id(self):
        result = check_invariant("INV-01")
        assert result.startswith("INV-01:")
        # INV-01 is the LLM routing rule per the framework spec
        assert "LLM" in result

    def test_check_invariant_resolves_all_twenty_ids(self):
        for i in range(1, 21):
            inv_id = f"INV-{i:02d}"
            result = check_invariant(inv_id)
            assert result.startswith(f"{inv_id}:")

    def test_check_invariant_invalid_id_raises_value_error(self):
        with pytest.raises(ValueError):
            check_invariant("INV-99")

    def test_check_invariant_unknown_format_raises_value_error(self):
        with pytest.raises(ValueError):
            check_invariant("not-an-invariant-id")


class TestListInvariants:
    def test_list_invariants_returns_all_twenty(self):
        result = list_invariants()
        assert len(result) == 20

    def test_list_invariants_returns_a_copy_not_reference(self):
        """Mutating the returned list MUST NOT affect the master list."""
        a = list_invariants()
        b = list_invariants()
        assert a == b
        assert a is not b
        a.append("INJECTED")
        a.clear()
        # Master list still intact
        assert len(list_invariants()) == 20
        assert len(SECURITY_INVARIANTS) == 20
