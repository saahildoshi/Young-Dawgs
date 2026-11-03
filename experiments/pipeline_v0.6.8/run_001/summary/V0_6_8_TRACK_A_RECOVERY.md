# v0.6.8 Track A — recovery decision

**Decision: no new full-original solve or full-original restart.** The predeclared local entry gate in [TRACK_A.json](../protocol/TRACK_A.json) requires a complete geometry-valid local path, matching measured full-parent fields and near-contact context, actual opposing interface forces, and the unchanged 1% reaction, 10⁻⁵ mm penetration and positive quadratic-mapping checks. The expanded comparison does not meet that gate.

The authenticated original full restart remains load step 3/substep 6 at 0.009270608836206897 engineering strain. The local nodal variant still stops during curved contact onset. Unified detection finishes its **hypothetical local** 1% loading, but early measured parent stress states fail the fixed comparison; its terminal near-gap/contact state also differs. Native pressure/penetration and geometry readbacks are retained, and closed local interfaces are marked as lacking a two-sided force proof. Thus neither local candidate authorizes a costly full fine-model retry.

No identical stalled full solve was repeated. No local extrapolated load step is represented as a full-specimen result. The previous rejected 1% full states stay rejected, and the original full mechanical maximum remains **0.9270608836206897%**. The separately selected Track B specimen and its contact-pair branch are reported in their own files.

The next Track A milestone is a parent-matched local model from the earliest measured state through contact onset, including a native two-sided interface-force check and a quantified near-gap comparison. Only after that gate passes should a registered full fine-model formulation or restart retry be considered.
