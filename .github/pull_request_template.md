## Summary

- _Explain why this change exists and what it delivers for users or contributors._
- _Call out any notable trade-offs or follow-up work._

## Testing

- [ ] `uv run pre-commit run --all-files`
- [ ] `docker compose run --rm backend-tests` *(or)* `uv run pytest -m "not slow and not integration"`
- [ ] Frontend confidence step (`npm run build`, `npm run test`, or manual QA as appropriate)

## Checklist

- [ ] Linked all relevant issues or created a tracking issue
- [ ] Added or updated documentation when behaviour or workflows changed
- [ ] Added or updated tests covering new/changed functionality
- [ ] Verified the Docker stack (`docker compose up`) still boots cleanly

> Need a refresher? See [CONTRIBUTIONS.md](../CONTRIBUTIONS.md#️-contribution-workflow-at-a-glance) for the full workflow. Thanks for shipping! 🎉
