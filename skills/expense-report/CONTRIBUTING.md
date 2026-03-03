# Contributing

## Development Flow

1. Update `SKILL.md` and related resources under `scripts/` or `references/`.
2. Test core script behavior locally.
3. Re-package the skill.
4. Open PR with clear scope and test evidence.

## Local Test

```bash
python3 skills/expense-report/scripts/ledger.py init --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py add --root shared/expense-report --text "午饭 32元"
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period daily
```

## Commit Style

Use Conventional Commits:

- `feat:` new feature
- `fix:` bug fix
- `docs:` docs only
- `refactor:` internal improvement
- `test:` tests
- `chore:` tooling/maintenance
