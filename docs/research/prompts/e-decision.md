TASK E: compare decision / classifier models for cheap agent decisions, against TypeSafe AI (Jev).

Read our note first: ~/agent-kit/docs/research/typesafe-ai.md. Then, for each source below, first confirm it exists
and what it is (owner, license, date); if you cannot open it, say so and do not describe it:
- https://github.com/iapp-technology/openthai-systemone
- https://github.com/ipenywis/laya-ultrafast
- https://blog.cloudflare.com/clef-decision-models/
- TypeSafe AI Jev (from our note; recheck pricing / license only if needed)

Deliver:
1. Table: name | what it is | open weights / OSS / paid / API | runs locally? (size, hardware) | task types (choice,
   score, yes/no, extraction) | latency / cost numbers WITH their source | Thai language support | license.
2. For our use (decisions inside the harness that must stay cheap and local where possible: keep/drop tool results,
   route to a cheaper agent, pick a skill, classify a request's network level; company data must not leave the
   machine unless the user approves): which fits, which does not, why. Note that openthai-systemone is Thai-made:
   check whether it relates to Jev's "System One" interface.
3. A small pilot we could run to compare 2 of them on our own decisions (inputs, metric, how the user reviews it;
   no LLM judge).
4. "What this means for us": 3-5 lines, verified vs hypothesis.
