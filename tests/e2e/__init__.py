"""
End-to-end tests - full system tests requiring complete setup.

These tests:
- Require full environment setup
- Test complete trading workflows
- May execute real transactions (with safeguards)
- Are marked with @pytest.mark.e2e and @pytest.mark.skip by default
- Can be enabled with environment gates (CONFIRM_SEND=YES)
"""
