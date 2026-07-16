# CV Generation Guidelines

Rules the agents follow when tailoring a CV. Replace every bracketed value with
your own before running the pipeline.

- **Geographic Constraints:** Target roles located in [your region] (e.g.
  [City A], [City B], [City C]). State here whether remote roles are acceptable.
- **Tone:** [e.g. concise, factual, results-first. No marketing language.]
- **Length:** [e.g. one page for DEV, one page for MGMT.]
- **Formatting:** Use the section order defined in `CV_Vault/*_Base.md`. Do not
  invent sections.
- **Bullet Style:** Start each bullet with a strong verb. Include a measurable
  result where one exists. Never pad with adjectives.
- **Keyword Rule:** Mirror the terminology used in the job description, but only
  where it is genuinely true of the candidate.
- **Education Rule:** [State whether education must always appear, and whether
  the graduation date should be included or omitted.]
- **Track Selection:** Entries are tagged `DEV` or `MGMT`. Only pull entries
  matching the track being generated.
